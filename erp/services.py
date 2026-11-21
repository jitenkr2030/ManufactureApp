from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import *

@transaction.atomic
def post_stock_movement(*, stock, movement_type, quantity_delta, user=None, reference="", remarks=""):
    stock=Stock.objects.select_for_update().get(pk=stock.pk); qty=Decimal(str(quantity_delta))
    if stock.quantity+qty<0: raise ValidationError(f"Insufficient stock for {stock.product}. Available: {stock.quantity}")
    stock.quantity+=qty; stock.save(update_fields=["quantity","updated_at"])
    movement=StockMovement.objects.create(stock=stock,movement_type=movement_type,quantity_delta=qty,reference=reference,remarks=remarks,created_by=user)
    AuditLog.objects.create(user=user,action="STOCK_POSTED",object_type="StockMovement",object_id=str(movement.pk),details={"reference":reference,"delta":str(qty)})
    return movement

def explode_bom(product, quantity, warehouse, level=0, path=None):
    path=path or set()
    if product.pk in path: raise ValidationError(f"Circular BOM detected at {product}.")
    bom=BOM.objects.filter(product=product,is_active=True).order_by("-version").first()
    if not bom: return []
    result=[]; next_path=path|{product.pk}
    for line in bom.lines.select_related("component","bom"):
        required=line.required_for(quantity)
        nested=explode_bom(line.component,required,warehouse,level+1,next_path)
        if nested: result.extend(nested)
        else:
            on_hand=sum((s.available for s in Stock.objects.filter(product=line.component,warehouse=warehouse)),Decimal("0"))
            result.append({"product":line.component,"level":level+1,"gross":required,"on_hand":on_hand,"net":max(required-on_hand,Decimal("0"))})
    return result

def calculate_mrp(bom, output_quantity, warehouse):
    return explode_bom(bom.product,Decimal(str(output_quantity)),warehouse)

@transaction.atomic
def post_material_issue(issue,user=None):
    issue=MaterialIssue.objects.select_for_update().get(pk=issue.pk)
    if issue.status=="POSTED": raise ValidationError("Already posted.")
    if not issue.lines.exists(): raise ValidationError("Add material issue lines.")
    for line in issue.lines.select_related("stock"):
        post_stock_movement(stock=line.stock,movement_type=StockMovement.Type.ISSUE,quantity_delta=-line.quantity,user=user,reference=issue.number)
    issue.status="POSTED"; issue.issued_at=timezone.now(); issue.save(update_fields=["status","issued_at","updated_at"])
    return issue

@transaction.atomic
def receive_finished_goods(order,warehouse,quantity,user=None,batch_no=""):
    qty=Decimal(str(quantity))
    if qty<=0 or qty>order.pending_quantity: raise ValidationError("Receipt must be positive and not exceed pending production.")
    stock,_=Stock.objects.get_or_create(product=order.product,warehouse=warehouse,location=None,batch_no=batch_no)
    post_stock_movement(stock=stock,movement_type=StockMovement.Type.FG_RECEIPT,quantity_delta=qty,user=user,reference=order.number)
    order.completed_quantity+=qty; order.status="COMPLETED" if order.completed_quantity>=order.planned_quantity else "IN_PROGRESS"
    order.save(update_fields=["completed_quantity","status","updated_at"])
    return FinishedGoodsReceipt.objects.create(number=f"FGR-{timezone.now():%Y%m%d%H%M%S%f}",production_order=order,stock=stock,quantity=qty)

@transaction.atomic
def post_goods_receipt(receipt,user=None):
    receipt=GoodsReceipt.objects.select_for_update().get(pk=receipt.pk)
    if receipt.status=="POSTED": raise ValidationError("GRN already posted.")
    if not receipt.lines.exists(): raise ValidationError("Add receipt lines.")
    po=receipt.purchase_order
    for line in receipt.lines.select_related("order_line__product"):
        ol=line.order_line
        if ol.received_quantity+line.quantity>ol.quantity: raise ValidationError(f"Receipt exceeds ordered quantity for {ol.product}.")
        stock,_=Stock.objects.get_or_create(product=ol.product,warehouse=po.warehouse,location=None,batch_no=line.batch_no)
        post_stock_movement(stock=stock,movement_type=StockMovement.Type.RECEIPT,quantity_delta=line.quantity,user=user,reference=receipt.number)
        ol.received_quantity+=line.quantity; ol.save(update_fields=["received_quantity","updated_at"])
    receipt.status="POSTED"; receipt.save(update_fields=["status","updated_at"])
    if all(x.received_quantity>=x.quantity for x in po.lines.all()): po.status="RECEIVED"; po.save(update_fields=["status","updated_at"])
    return receipt

@transaction.atomic
def post_stock_transfer(transfer,user=None):
    transfer=StockTransfer.objects.select_for_update().get(pk=transfer.pk)
    if transfer.status=="POSTED": raise ValidationError("Transfer already posted.")
    for line in transfer.lines.select_related("stock__product"):
        src=line.stock
        post_stock_movement(stock=src,movement_type=StockMovement.Type.TRANSFER_OUT,quantity_delta=-line.quantity,user=user,reference=transfer.number)
        dest,_=Stock.objects.get_or_create(product=src.product,warehouse=transfer.to_warehouse,location=None,batch_no=line.batch_no or src.batch_no)
        post_stock_movement(stock=dest,movement_type=StockMovement.Type.TRANSFER_IN,quantity_delta=line.quantity,user=user,reference=transfer.number)
    transfer.status="POSTED"; transfer.save(update_fields=["status","updated_at"])
    return transfer

@transaction.atomic
def decide_approval(request_obj,approved,user,comments=""):
    if request_obj.status!="PENDING": raise ValidationError("Approval is already decided.")
    if request_obj.approver_id and request_obj.approver_id!=user.id and not user.is_superuser: raise ValidationError("You are not the assigned approver.")
    request_obj.status="APPROVED" if approved else "REJECTED"; request_obj.comments=comments; request_obj.decided_at=timezone.now()
    request_obj.save(update_fields=["status","comments","decided_at","updated_at"])
    return request_obj

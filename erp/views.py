from decimal import Decimal
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Sum,Count,F
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from . import models
from .forms import form_for,MRPForm,FGReceiptForm
from .services import calculate_mrp,post_goods_receipt,post_material_issue,post_stock_transfer,receive_finished_goods,decide_approval

MODULES={
 "companies":("Company","Companies"),"branches":("Branch","Branches"),"factories":("Factory","Factories"),
 "departments":("Department","Departments"),"units":("Unit","Units"),"categories":("Category","Categories"),
 "products":("Product","Products"),"warehouses":("Warehouse","Warehouses"),"locations":("Location","Locations"),
 "suppliers":("Supplier","Suppliers"),"customers":("Customer","Customers"),"stock":("Stock","Inventory"),
 "boms":("BOM","Bills of Materials"),"bom-lines":("BOMLine","BOM Components"),
 "purchase-requisitions":("PurchaseRequisition","Purchase Requisitions"),"purchase-orders":("PurchaseOrder","Purchase Orders"),
 "purchase-order-lines":("PurchaseOrderLine","Purchase Order Lines"),"grn":("GoodsReceipt","Goods Receipts"),
 "grn-lines":("GoodsReceiptLine","GRN Lines"),"work-centers":("WorkCenter","Work Centers"),"machines":("Machine","Machines"),
 "routings":("Routing","Routings"),"operations":("Operation","Operations"),"production-orders":("ProductionOrder","Production Orders"),
 "schedules":("ProductionSchedule","Production Calendar"),"material-issues":("MaterialIssue","Material Issues"),
 "material-issue-lines":("MaterialIssueLine","Material Issue Lines"),"job-work":("JobWorkOrder","Job Work Orders"),
 "qc":("QCInspection","Quality Inspections"),"defects":("Defect","Defects"),"inspection-parameters":("InspectionParameter","Inspection Parameters"),
 "batches":("Batch","Batch Tracking"),"serials":("SerialNumber","Serial Numbers"),"genealogy":("ProductGenealogy","Product Genealogy"),
 "operation-execution":("OperationExecution","Shop Floor Execution"),"wip":("WIPRecord","Work in Progress"),
 "finished-goods":("FinishedGoodsReceipt","Finished Goods Receipts"),"scrap":("ScrapRecord","Scrap & Waste"),
 "rework":("ReworkOrder","Rework Orders"),"cost-sheets":("CostSheet","Production Costing"),
 "sales-orders":("SalesOrder","Sales Orders"),"sales-lines":("SalesOrderLine","Sales Order Lines"),"deliveries":("Delivery","Dispatch & Deliveries"),
 "stock-transfers":("StockTransfer","Stock Transfers"),"stock-transfer-lines":("StockTransferLine","Transfer Lines"),
 "maintenance-plans":("MaintenancePlan","Maintenance Plans"),"maintenance-orders":("MaintenanceOrder","Maintenance Orders"),
 "employees":("Employee","Employees"),"shifts":("Shift","Shifts"),"attendance":("Attendance","Attendance"),
 "approvals":("ApprovalRequest","Approvals"),"documents":("Document","Documents"),"expenses":("Expense","Expenses"),
 "accounts":("Account","Accounts"),"journals":("JournalEntry","Journal Entries"),"journal-lines":("JournalLine","Journal Lines"),
 "returns":("ReturnAuthorization","Customer Returns"),"warranty":("WarrantyClaim","Warranty Claims"),"safety":("SafetyIncident","Safety Incidents"),
 "notifications":("Notification","Notifications"),"audit":("AuditLog","Audit Trail"),
}
def _model(slug):
    name,label=MODULES[slug]; return apps.get_model("erp",name),label
@login_required
def dashboard(request):
    low_stock=models.Stock.objects.select_related("product","warehouse").filter(quantity__lte=F("product__reorder_level")).order_by("quantity")[:8]
    context={"product_count":models.Product.objects.filter(is_active=True).count(),"stock_bins":models.Stock.objects.count(),
      "production_open":models.ProductionOrder.objects.exclude(status__in=["COMPLETED","CLOSED","CANCELLED"]).count(),
      "purchase_open":models.PurchaseOrder.objects.exclude(status__in=["RECEIVED","CLOSED"]).count(),
      "qc_pending":models.QCInspection.objects.filter(result="PENDING").count(),"pending_approvals":models.ApprovalRequest.objects.filter(status="PENDING").count(),
      "low_stock":low_stock,"recent_orders":models.ProductionOrder.objects.select_related("product").order_by("-created_at")[:8],
      "upcoming":models.ProductionSchedule.objects.select_related("production_order","work_center").filter(start_at__gte=timezone.now()).order_by("start_at")[:6]}
    return render(request,"erp/dashboard.html",context)
@login_required
def module_list(request,slug):
    if slug not in MODULES: return redirect("dashboard")
    model,label=_model(slug)
    if not any(_allowed(request.user, action, model) for action in ("view","change","add")):
        return HttpResponseForbidden("You do not have permission to view this module.")
    qs=model.objects.all().order_by("-pk")
    q=request.GET.get("q","").strip()
    if q:
        from django.db.models import Q
        fields=[f.name for f in model._meta.fields if f.get_internal_type() in ("CharField","TextField","EmailField")]
        condition=Q()
        for field in fields: condition|=Q(**{f"{field}__icontains":q})
        if fields: qs=qs.filter(condition)
    fields=[f for f in model._meta.fields if f.name not in ("created_at","updated_at")]
    rows=[{"obj":obj,"cells":[getattr(obj,f.name) for f in fields]} for obj in qs[:300]]
    return render(request,"erp/module_list.html",{"label":label,"slug":slug,"objects":qs[:300],"rows":rows,
        "q":q,"model":model,"fields":fields,"can_add":_allowed(request.user,"add",model),
        "can_change":_allowed(request.user,"change",model),"can_delete":_allowed(request.user,"delete",model)})
@login_required
def module_create(request,slug,pk=None):
    if slug not in MODULES: return redirect("dashboard")
    model,label=_model(slug)
    action="change" if pk else "add"
    if not _allowed(request.user,action,model): return HttpResponseForbidden("You do not have permission to save this record.")
    obj=get_object_or_404(model,pk=pk) if pk else None; Form=form_for(model)
    if request.method=="POST":
        form=Form(request.POST,request.FILES,instance=obj)
        if form.is_valid():
            saved=form.save(); messages.success(request,f"{label}: record saved."); return redirect("module-list",slug=slug)
    else: form=Form(instance=obj)
    return render(request,"erp/module_form.html",{"form":form,"label":label,"slug":slug,"obj":obj})
@login_required
@require_POST
def module_delete(request,slug,pk):
    model,label=_model(slug)
    if not _allowed(request.user,"delete",model): return HttpResponseForbidden("You do not have permission to delete this record.")
    obj=get_object_or_404(model,pk=pk)
    try: obj.delete(); messages.success(request,"Record deleted.")
    except Exception as exc: messages.error(request,f"Cannot delete this record because it is referenced by another transaction. {exc}")
    return redirect("module-list",slug=slug)
@login_required
def mrp_view(request):
    form=MRPForm(request.GET or None); rows=[]; run=None
    if form.is_valid():
        bom=form.cleaned_data["bom"]; wh=form.cleaned_data["warehouse"]; qty=form.cleaned_data["quantity"]
        try:
            rows=calculate_mrp(bom,qty,wh)
            if request.GET.get("save")=="1":
                run=models.MRPRun.objects.create(number=f"MRP-{timezone.now():%Y%m%d%H%M%S}",warehouse=wh,demand_date=form.cleaned_data.get("demand_date") or timezone.localdate())
                for row in rows: models.MRPLine.objects.create(run=run,product=row["product"],gross_requirement=row["gross"],on_hand=row["on_hand"],net_requirement=row["net"],suggested_order_qty=row["net"],level=row["level"])
        except ValidationError as exc: messages.error(request,str(exc))
    return render(request,"erp/mrp.html",{"form":form,"rows":rows,"run":run})
@login_required
def calendar_view(request):
    start=request.GET.get("start"); qs=models.ProductionSchedule.objects.select_related("production_order","work_center","machine").order_by("start_at")
    if start: qs=qs.filter(start_at__date=start)
    return render(request,"erp/calendar.html",{"schedules":qs[:500],"selected_date":start})
@login_required
def workflow_action(request,kind,pk):
    if request.method!="POST": return redirect("dashboard")
    try:
        if kind=="post-grn": post_goods_receipt(get_object_or_404(models.GoodsReceipt,pk=pk),request.user)
        elif kind=="post-issue": post_material_issue(get_object_or_404(models.MaterialIssue,pk=pk),request.user)
        elif kind=="post-transfer": post_stock_transfer(get_object_or_404(models.StockTransfer,pk=pk),request.user)
        elif kind=="approve":
            ar=get_object_or_404(models.ApprovalRequest,pk=pk); decide_approval(ar,True,request.user,request.POST.get("comments",""))
        elif kind=="reject":
            ar=get_object_or_404(models.ApprovalRequest,pk=pk); decide_approval(ar,False,request.user,request.POST.get("comments",""))
        messages.success(request,"Workflow action completed.")
    except Exception as exc: messages.error(request,str(exc))
    return redirect(request.META.get("HTTP_REFERER","dashboard"))
@login_required
def fg_receipt(request):
    if request.method=="POST":
        form=FGReceiptForm(request.POST)
        if form.is_valid():
            try: receive_finished_goods(form.cleaned_data["order"],form.cleaned_data["warehouse"],form.cleaned_data["quantity"],request.user,form.cleaned_data["batch_no"]); messages.success(request,"Finished goods received into inventory."); return redirect("module-list",slug="finished-goods")
            except Exception as exc: messages.error(request,str(exc))
    else: form=FGReceiptForm()
    return render(request,"erp/simple_form.html",{"form":form,"title":"Receive Finished Goods"})
@login_required
def reports(request):
    data={"stock_value":sum((s.quantity*s.product.standard_cost for s in models.Stock.objects.select_related("product")),Decimal("0")),
      "stock_items":models.Stock.objects.count(),"production_orders":models.ProductionOrder.objects.count(),
      "completed_orders":models.ProductionOrder.objects.filter(status="COMPLETED").count(),
      "scrap_qty":models.ScrapRecord.objects.aggregate(v=Sum("quantity"))["v"] or 0,
      "qc_rejected":models.QCInspection.objects.aggregate(v=Sum("rejected_quantity"))["v"] or 0}
    return render(request,"erp/reports.html",{"data":data})
@login_required
def export_stock(request):
    wb=Workbook(); ws=wb.active; ws.title="Inventory"; ws.append(["SKU","Product","Warehouse","Batch","Qty","Reserved","Available","Unit Cost","Stock Value"])
    for s in models.Stock.objects.select_related("product","warehouse"):
        ws.append([s.product.sku,s.product.name,s.warehouse.name,s.batch_no,float(s.quantity),float(s.reserved_quantity),float(s.available),float(s.product.standard_cost),float(s.quantity*s.product.standard_cost)])
    from io import BytesIO
    buf=BytesIO(); wb.save(buf); buf.seek(0)
    response=HttpResponse(buf.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"]='attachment; filename="manufacturing-inventory.xlsx"'; return response
@login_required
def export_production(request):
    wb=Workbook(); ws=wb.active; ws.title="Production"; ws.append(["Order","Product","Planned","Completed","Pending","Due Date","Status"])
    for o in models.ProductionOrder.objects.select_related("product"):
        ws.append([o.number,o.product.name,float(o.planned_quantity),float(o.completed_quantity),float(o.pending_quantity),str(o.due_date or ""),o.status])
    from io import BytesIO
    buf=BytesIO(); wb.save(buf); buf.seek(0)
    response=HttpResponse(buf.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"]='attachment; filename="production-report.xlsx"'; return response
@login_required
def export_stock_pdf(request):
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf=BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4); width,height=A4
    y=height-42; pdf.setFont("Helvetica-Bold",15); pdf.drawString(36,y,"Manufacturing ERP — Inventory Report")
    y-=28; pdf.setFont("Helvetica",8)
    for stock in models.Stock.objects.select_related("product","warehouse").order_by("product__sku"):
        line=f"{stock.product.sku} | {stock.product.name[:30]} | {stock.warehouse.name[:20]} | {stock.batch_no[:12]} | Qty {stock.quantity}"
        pdf.drawString(36,y,line); y-=14
        if y<40: pdf.showPage(); y=height-40; pdf.setFont("Helvetica",8)
    pdf.save(); buf.seek(0)
    response=HttpResponse(buf.getvalue(),content_type="application/pdf")
    response["Content-Disposition"]='attachment; filename="manufacturing-inventory.pdf"'
    return response

@login_required
def product_qr(request, pk):
    from io import BytesIO
    import qrcode
    product=get_object_or_404(models.Product,pk=pk)
    img=qrcode.make(f"SKU:{product.sku}|NAME:{product.name}")
    buf=BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    return HttpResponse(buf.getvalue(),content_type="image/png")

@login_required
def audit_view(request):
    return render(request,"erp/audit.html",{"entries":models.AuditLog.objects.select_related("user")[:300]})

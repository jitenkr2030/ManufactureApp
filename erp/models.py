# Original Version 1 models are retained and extended below.
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

class TimeStamped(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: abstract=True

class Company(TimeStamped):
    name=models.CharField(max_length=180); code=models.CharField(max_length=30,unique=True)
    tax_id=models.CharField(max_length=40,blank=True); address=models.TextField(blank=True)
    def __str__(self): return self.name
class Branch(TimeStamped):
    company=models.ForeignKey(Company,on_delete=models.PROTECT); name=models.CharField(max_length=150); code=models.CharField(max_length=30)
    class Meta: unique_together=("company","code")
    def __str__(self): return self.name
class Factory(TimeStamped):
    branch=models.ForeignKey(Branch,on_delete=models.PROTECT); name=models.CharField(max_length=150); code=models.CharField(max_length=30)
    def __str__(self): return self.name
class Department(TimeStamped):
    factory=models.ForeignKey(Factory,on_delete=models.PROTECT,null=True,blank=True); name=models.CharField(max_length=120)
    def __str__(self): return self.name
class Unit(TimeStamped):
    name=models.CharField(max_length=80); symbol=models.CharField(max_length=12,unique=True); decimal_places=models.PositiveSmallIntegerField(default=3)
    def __str__(self): return self.symbol
class Category(TimeStamped):
    name=models.CharField(max_length=120,unique=True); parent=models.ForeignKey("self",null=True,blank=True,on_delete=models.PROTECT)
    def __str__(self): return self.name
class Product(TimeStamped):
    class Kind(models.TextChoices): RAW="RAW","Raw material"; WIP="WIP","Work in progress"; FINISHED="FG","Finished good"; CONSUMABLE="CON","Consumable"; SERVICE="SRV","Service"
    sku=models.CharField(max_length=60,unique=True); name=models.CharField(max_length=180); kind=models.CharField(max_length=3,choices=Kind.choices)
    category=models.ForeignKey(Category,null=True,blank=True,on_delete=models.PROTECT); unit=models.ForeignKey(Unit,on_delete=models.PROTECT)
    description=models.TextField(blank=True); reorder_level=models.DecimalField(max_digits=16,decimal_places=3,default=0)
    standard_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0); barcode=models.CharField(max_length=100,blank=True)
    is_active=models.BooleanField(default=True)
    def __str__(self): return f"{self.sku} - {self.name}"
class Warehouse(TimeStamped):
    company=models.ForeignKey(Company,on_delete=models.PROTECT); name=models.CharField(max_length=120); code=models.CharField(max_length=30)
    def __str__(self): return self.name
class Location(TimeStamped):
    warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT,related_name="locations"); code=models.CharField(max_length=40); description=models.CharField(max_length=160,blank=True)
    class Meta: unique_together=("warehouse","code")
    def __str__(self): return f"{self.warehouse}/{self.code}"
class Supplier(TimeStamped):
    name=models.CharField(max_length=180); code=models.CharField(max_length=40,unique=True); contact_person=models.CharField(max_length=120,blank=True)
    email=models.EmailField(blank=True); phone=models.CharField(max_length=30,blank=True); address=models.TextField(blank=True); tax_id=models.CharField(max_length=40,blank=True)
    def __str__(self): return self.name
class Customer(TimeStamped):
    name=models.CharField(max_length=180); code=models.CharField(max_length=40,unique=True); email=models.EmailField(blank=True); phone=models.CharField(max_length=30,blank=True); address=models.TextField(blank=True)
    def __str__(self): return self.name
class Stock(TimeStamped):
    product=models.ForeignKey(Product,on_delete=models.PROTECT); warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT)
    location=models.ForeignKey(Location,null=True,blank=True,on_delete=models.PROTECT); batch_no=models.CharField(max_length=80,blank=True)
    quantity=models.DecimalField(max_digits=18,decimal_places=3,default=0); reserved_quantity=models.DecimalField(max_digits=18,decimal_places=3,default=0)
    class Meta: constraints=[models.UniqueConstraint(fields=["product","warehouse","location","batch_no"],name="uniq_stock_bin_batch_v2")]
    @property
    def available(self): return self.quantity-self.reserved_quantity
    def __str__(self): return f"{self.product} @ {self.warehouse}: {self.quantity}"
class StockMovement(TimeStamped):
    class Type(models.TextChoices):
        OPENING="OPEN","Opening"; RECEIPT="REC","Receipt"; ISSUE="ISS","Issue"; RETURN="RET","Return"
        TRANSFER_IN="TIN","Transfer in"; TRANSFER_OUT="TOU","Transfer out"; FG_RECEIPT="FGR","Finished goods"; SCRAP="SCR","Scrap"; ADJUSTMENT="ADJ","Adjustment"
    stock=models.ForeignKey(Stock,on_delete=models.PROTECT,related_name="movements"); movement_type=models.CharField(max_length=3,choices=Type.choices)
    quantity_delta=models.DecimalField(max_digits=18,decimal_places=3); reference=models.CharField(max_length=80,blank=True); remarks=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
    def __str__(self): return f"{self.get_movement_type_display()} {self.quantity_delta}"
class BOM(TimeStamped):
    product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name="boms"); version=models.PositiveIntegerField(default=1)
    output_quantity=models.DecimalField(max_digits=16,decimal_places=3,default=1); is_active=models.BooleanField(default=True); notes=models.TextField(blank=True)
    class Meta: unique_together=("product","version")
    def __str__(self): return f"{self.product} BOM v{self.version}"
class BOMLine(TimeStamped):
    bom=models.ForeignKey(BOM,on_delete=models.CASCADE,related_name="lines"); component=models.ForeignKey(Product,on_delete=models.PROTECT)
    quantity=models.DecimalField(max_digits=16,decimal_places=4); wastage_percent=models.DecimalField(max_digits=7,decimal_places=3,default=0)
    def required_for(self,output_qty): return Decimal(output_qty)*self.quantity/self.bom.output_quantity*(1+self.wastage_percent/100)
class PurchaseRequisition(TimeStamped):
    number=models.CharField(max_length=40,unique=True); requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
    required_date=models.DateField(null=True,blank=True); status=models.CharField(max_length=20,default="DRAFT"); remarks=models.TextField(blank=True)
    def __str__(self): return self.number
class PurchaseOrder(TimeStamped):
    number=models.CharField(max_length=40,unique=True); supplier=models.ForeignKey(Supplier,on_delete=models.PROTECT); warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT)
    order_date=models.DateField(default=timezone.localdate); expected_date=models.DateField(null=True,blank=True); status=models.CharField(max_length=20,default="DRAFT")
    def __str__(self): return self.number
class PurchaseOrderLine(TimeStamped):
    order=models.ForeignKey(PurchaseOrder,on_delete=models.CASCADE,related_name="lines"); product=models.ForeignKey(Product,on_delete=models.PROTECT)
    quantity=models.DecimalField(max_digits=16,decimal_places=3); received_quantity=models.DecimalField(max_digits=16,decimal_places=3,default=0); unit_price=models.DecimalField(max_digits=16,decimal_places=2,default=0)
class GoodsReceipt(TimeStamped):
    number=models.CharField(max_length=40,unique=True); purchase_order=models.ForeignKey(PurchaseOrder,on_delete=models.PROTECT,related_name="receipts")
    received_date=models.DateField(default=timezone.localdate); status=models.CharField(max_length=20,default="DRAFT")
    def __str__(self): return self.number
class GoodsReceiptLine(TimeStamped):
    receipt=models.ForeignKey(GoodsReceipt,on_delete=models.CASCADE,related_name="lines"); order_line=models.ForeignKey(PurchaseOrderLine,on_delete=models.PROTECT)
    quantity=models.DecimalField(max_digits=16,decimal_places=3); batch_no=models.CharField(max_length=80,blank=True)
class WorkCenter(TimeStamped):
    code=models.CharField(max_length=40,unique=True); name=models.CharField(max_length=120); capacity_hours_per_day=models.DecimalField(max_digits=8,decimal_places=2,default=8); is_active=models.BooleanField(default=True)
    def __str__(self): return self.name
class Routing(TimeStamped):
    product=models.ForeignKey(Product,on_delete=models.PROTECT); version=models.PositiveIntegerField(default=1)
    def __str__(self): return f"{self.product} routing v{self.version}"
class Operation(TimeStamped):
    routing=models.ForeignKey(Routing,on_delete=models.CASCADE,related_name="operations"); sequence=models.PositiveIntegerField()
    name=models.CharField(max_length=120); work_center=models.ForeignKey(WorkCenter,on_delete=models.PROTECT); standard_minutes=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    setup_minutes=models.DecimalField(max_digits=10,decimal_places=2,default=0); instructions=models.TextField(blank=True)
    class Meta: ordering=["sequence"]
class ProductionOrder(TimeStamped):
    number=models.CharField(max_length=40,unique=True); product=models.ForeignKey(Product,on_delete=models.PROTECT); bom=models.ForeignKey(BOM,on_delete=models.PROTECT)
    warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT); planned_quantity=models.DecimalField(max_digits=16,decimal_places=3)
    completed_quantity=models.DecimalField(max_digits=16,decimal_places=3,default=0); due_date=models.DateField(null=True,blank=True); status=models.CharField(max_length=24,default="PLANNED")
    @property
    def pending_quantity(self): return self.planned_quantity-self.completed_quantity
    def __str__(self): return self.number
class MaterialIssue(TimeStamped):
    number=models.CharField(max_length=40,unique=True); production_order=models.ForeignKey(ProductionOrder,on_delete=models.PROTECT); status=models.CharField(max_length=20,default="DRAFT"); issued_at=models.DateTimeField(null=True,blank=True)
class MaterialIssueLine(TimeStamped):
    issue=models.ForeignKey(MaterialIssue,on_delete=models.CASCADE,related_name="lines"); product=models.ForeignKey(Product,on_delete=models.PROTECT); stock=models.ForeignKey(Stock,on_delete=models.PROTECT); quantity=models.DecimalField(max_digits=16,decimal_places=3)
class JobWorkOrder(TimeStamped):
    number=models.CharField(max_length=40,unique=True); subcontractor=models.ForeignKey(Supplier,on_delete=models.PROTECT); production_order=models.ForeignKey(ProductionOrder,null=True,blank=True,on_delete=models.PROTECT)
    description=models.TextField(blank=True); sent_date=models.DateField(null=True,blank=True); due_date=models.DateField(null=True,blank=True); status=models.CharField(max_length=20,default="OPEN")
    charges=models.DecimalField(max_digits=16,decimal_places=2,default=0); transport_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0)
class QCInspection(TimeStamped):
    class Result(models.TextChoices): PENDING="PENDING","Pending"; PASS="PASS","Pass"; FAIL="FAIL","Fail"; CONDITIONAL="COND","Conditional"
    number=models.CharField(max_length=40,unique=True); product=models.ForeignKey(Product,on_delete=models.PROTECT); production_order=models.ForeignKey(ProductionOrder,null=True,blank=True,on_delete=models.PROTECT)
    inspected_quantity=models.DecimalField(max_digits=16,decimal_places=3); accepted_quantity=models.DecimalField(max_digits=16,decimal_places=3,default=0); rejected_quantity=models.DecimalField(max_digits=16,decimal_places=3,default=0)
    result=models.CharField(max_length=10,choices=Result.choices,default=Result.PENDING); remarks=models.TextField(blank=True)
class FinishedGoodsReceipt(TimeStamped):
    number=models.CharField(max_length=40,unique=True); production_order=models.ForeignKey(ProductionOrder,on_delete=models.PROTECT); stock=models.ForeignKey(Stock,on_delete=models.PROTECT); quantity=models.DecimalField(max_digits=16,decimal_places=3)
class SalesOrder(TimeStamped):
    number=models.CharField(max_length=40,unique=True); customer=models.ForeignKey(Customer,on_delete=models.PROTECT); order_date=models.DateField(default=timezone.localdate); status=models.CharField(max_length=20,default="OPEN")
    def __str__(self): return self.number
class SalesOrderLine(TimeStamped):
    order=models.ForeignKey(SalesOrder,on_delete=models.CASCADE,related_name="lines"); product=models.ForeignKey(Product,on_delete=models.PROTECT); quantity=models.DecimalField(max_digits=16,decimal_places=3); unit_price=models.DecimalField(max_digits=16,decimal_places=2,default=0)
class Delivery(TimeStamped):
    number=models.CharField(max_length=40,unique=True); sales_order=models.ForeignKey(SalesOrder,on_delete=models.PROTECT); warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT)
    dispatch_date=models.DateField(default=timezone.localdate); tracking_reference=models.CharField(max_length=100,blank=True); status=models.CharField(max_length=20,default="DRAFT")
class ScrapRecord(TimeStamped):
    number=models.CharField(max_length=40,unique=True); production_order=models.ForeignKey(ProductionOrder,on_delete=models.PROTECT); product=models.ForeignKey(Product,on_delete=models.PROTECT); quantity=models.DecimalField(max_digits=16,decimal_places=3); reason=models.TextField(blank=True)
class AuditLog(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL); action=models.CharField(max_length=100); object_type=models.CharField(max_length=100); object_id=models.CharField(max_length=50)
    details=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]
class Notification(TimeStamped):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.CASCADE); title=models.CharField(max_length=180); message=models.TextField(); read_at=models.DateTimeField(null=True,blank=True)

# Version 2 expansion: planning, traceability, costing, maintenance, workforce and workflow.
class Machine(TimeStamped):
    code=models.CharField(max_length=40,unique=True); name=models.CharField(max_length=120); work_center=models.ForeignKey(WorkCenter,on_delete=models.PROTECT)
    hourly_rate=models.DecimalField(max_digits=12,decimal_places=2,default=0); status=models.CharField(max_length=20,default="AVAILABLE"); serial_number=models.CharField(max_length=100,blank=True)
    def __str__(self): return f"{self.code} - {self.name}"
class ProductionSchedule(TimeStamped):
    production_order=models.ForeignKey(ProductionOrder,on_delete=models.CASCADE); work_center=models.ForeignKey(WorkCenter,on_delete=models.PROTECT)
    machine=models.ForeignKey(Machine,null=True,blank=True,on_delete=models.PROTECT); start_at=models.DateTimeField(); end_at=models.DateTimeField()
    status=models.CharField(max_length=20,default="SCHEDULED"); assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL)
    class Meta: ordering=["start_at"]
class MRPRun(TimeStamped):
    number=models.CharField(max_length=40,unique=True); warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT); demand_date=models.DateField(default=timezone.localdate)
    status=models.CharField(max_length=20,default="CALCULATED"); notes=models.TextField(blank=True)
    def __str__(self): return self.number
class MRPLine(TimeStamped):
    run=models.ForeignKey(MRPRun,on_delete=models.CASCADE,related_name="lines"); product=models.ForeignKey(Product,on_delete=models.PROTECT)
    gross_requirement=models.DecimalField(max_digits=18,decimal_places=3); on_hand=models.DecimalField(max_digits=18,decimal_places=3); net_requirement=models.DecimalField(max_digits=18,decimal_places=3)
    suggested_order_qty=models.DecimalField(max_digits=18,decimal_places=3,default=0); level=models.PositiveIntegerField(default=0)
class Batch(TimeStamped):
    product=models.ForeignKey(Product,on_delete=models.PROTECT); batch_number=models.CharField(max_length=80,unique=True); manufacture_date=models.DateField(null=True,blank=True)
    expiry_date=models.DateField(null=True,blank=True); supplier_batch=models.CharField(max_length=80,blank=True); status=models.CharField(max_length=20,default="ACTIVE")
    def __str__(self): return self.batch_number
class SerialNumber(TimeStamped):
    product=models.ForeignKey(Product,on_delete=models.PROTECT); serial_number=models.CharField(max_length=100,unique=True); batch=models.ForeignKey(Batch,null=True,blank=True,on_delete=models.PROTECT)
    status=models.CharField(max_length=20,default="AVAILABLE"); current_warehouse=models.ForeignKey(Warehouse,null=True,blank=True,on_delete=models.PROTECT)
class ProductGenealogy(TimeStamped):
    parent_serial=models.ForeignKey(SerialNumber,on_delete=models.PROTECT,related_name="components"); component_serial=models.ForeignKey(SerialNumber,on_delete=models.PROTECT,related_name="used_in")
    production_order=models.ForeignKey(ProductionOrder,null=True,blank=True,on_delete=models.PROTECT)
class OperationExecution(TimeStamped):
    production_order=models.ForeignKey(ProductionOrder,on_delete=models.PROTECT); operation=models.ForeignKey(Operation,on_delete=models.PROTECT)
    operator=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL); machine=models.ForeignKey(Machine,null=True,blank=True,on_delete=models.PROTECT)
    started_at=models.DateTimeField(null=True,blank=True); ended_at=models.DateTimeField(null=True,blank=True); good_quantity=models.DecimalField(max_digits=16,decimal_places=3,default=0)
    rejected_quantity=models.DecimalField(max_digits=16,decimal_places=3,default=0); status=models.CharField(max_length=20,default="PENDING"); delay_reason=models.TextField(blank=True)
class WIPRecord(TimeStamped):
    production_order=models.ForeignKey(ProductionOrder,on_delete=models.PROTECT); product=models.ForeignKey(Product,on_delete=models.PROTECT)
    operation=models.ForeignKey(Operation,null=True,blank=True,on_delete=models.PROTECT); quantity=models.DecimalField(max_digits=16,decimal_places=3)
    status=models.CharField(max_length=20,default="IN_PROCESS"); location=models.CharField(max_length=100,blank=True)
class CostSheet(TimeStamped):
    production_order=models.OneToOneField(ProductionOrder,on_delete=models.PROTECT); material_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    labour_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0); machine_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    overhead_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0); jobwork_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    standard_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0); actual_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    @property
    def variance(self): return self.actual_cost-self.standard_cost
class MaintenancePlan(TimeStamped):
    machine=models.ForeignKey(Machine,on_delete=models.PROTECT); title=models.CharField(max_length=160); due_date=models.DateField()
    interval_days=models.PositiveIntegerField(default=30); active=models.BooleanField(default=True)
class MaintenanceOrder(TimeStamped):
    number=models.CharField(max_length=40,unique=True); machine=models.ForeignKey(Machine,on_delete=models.PROTECT); planned_date=models.DateField()
    completed_date=models.DateField(null=True,blank=True); description=models.TextField(); status=models.CharField(max_length=20,default="OPEN"); cost=models.DecimalField(max_digits=14,decimal_places=2,default=0)
class Shift(TimeStamped):
    name=models.CharField(max_length=80); start_time=models.TimeField(); end_time=models.TimeField(); active=models.BooleanField(default=True)
    def __str__(self): return self.name
class Employee(TimeStamped):
    employee_code=models.CharField(max_length=40,unique=True); name=models.CharField(max_length=150); department=models.ForeignKey(Department,null=True,blank=True,on_delete=models.PROTECT)
    user=models.OneToOneField(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL); phone=models.CharField(max_length=30,blank=True); active=models.BooleanField(default=True)
    def __str__(self): return self.name
class Attendance(TimeStamped):
    employee=models.ForeignKey(Employee,on_delete=models.PROTECT); shift=models.ForeignKey(Shift,on_delete=models.PROTECT); work_date=models.DateField()
    check_in=models.DateTimeField(null=True,blank=True); check_out=models.DateTimeField(null=True,blank=True); hours=models.DecimalField(max_digits=6,decimal_places=2,default=0)
class ApprovalRequest(TimeStamped):
    module=models.CharField(max_length=80); object_type=models.CharField(max_length=100); object_id=models.CharField(max_length=50)
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="approval_submitted")
    approver=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.PROTECT,related_name="approval_assigned")
    status=models.CharField(max_length=20,default="PENDING"); comments=models.TextField(blank=True); decided_at=models.DateTimeField(null=True,blank=True)
class Document(TimeStamped):
    title=models.CharField(max_length=180); document_type=models.CharField(max_length=60); reference=models.CharField(max_length=100,blank=True)
    file=models.FileField(upload_to="documents/%Y/%m/",blank=True); revision=models.PositiveIntegerField(default=1); notes=models.TextField(blank=True)
class Defect(TimeStamped):
    code=models.CharField(max_length=40,unique=True); name=models.CharField(max_length=120); severity=models.CharField(max_length=20,default="MINOR"); description=models.TextField(blank=True)
class InspectionParameter(TimeStamped):
    name=models.CharField(max_length=120); product=models.ForeignKey(Product,null=True,blank=True,on_delete=models.PROTECT); unit=models.ForeignKey(Unit,null=True,blank=True,on_delete=models.PROTECT)
    min_value=models.DecimalField(max_digits=14,decimal_places=4,null=True,blank=True); max_value=models.DecimalField(max_digits=14,decimal_places=4,null=True,blank=True)
class InspectionFinding(TimeStamped):
    inspection=models.ForeignKey(QCInspection,on_delete=models.CASCADE,related_name="findings"); parameter=models.ForeignKey(InspectionParameter,null=True,blank=True,on_delete=models.PROTECT)
    defect=models.ForeignKey(Defect,null=True,blank=True,on_delete=models.PROTECT); measured_value=models.DecimalField(max_digits=14,decimal_places=4,null=True,blank=True)
    result=models.CharField(max_length=20,default="PASS"); notes=models.TextField(blank=True)
class ReworkOrder(TimeStamped):
    number=models.CharField(max_length=40,unique=True); production_order=models.ForeignKey(ProductionOrder,on_delete=models.PROTECT); quantity=models.DecimalField(max_digits=16,decimal_places=3)
    reason=models.TextField(); status=models.CharField(max_length=20,default="OPEN")
class StockTransfer(TimeStamped):
    number=models.CharField(max_length=40,unique=True); from_warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT,related_name="transfer_out")
    to_warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT,related_name="transfer_in"); status=models.CharField(max_length=20,default="DRAFT")
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
class StockTransferLine(TimeStamped):
    transfer=models.ForeignKey(StockTransfer,on_delete=models.CASCADE,related_name="lines"); stock=models.ForeignKey(Stock,on_delete=models.PROTECT)
    quantity=models.DecimalField(max_digits=16,decimal_places=3); batch_no=models.CharField(max_length=80,blank=True)
class ReturnAuthorization(TimeStamped):
    number=models.CharField(max_length=40,unique=True); customer=models.ForeignKey(Customer,on_delete=models.PROTECT); sales_order=models.ForeignKey(SalesOrder,null=True,blank=True,on_delete=models.PROTECT)
    reason=models.TextField(); status=models.CharField(max_length=20,default="OPEN"); received_date=models.DateField(null=True,blank=True)
class WarrantyClaim(TimeStamped):
    number=models.CharField(max_length=40,unique=True); customer=models.ForeignKey(Customer,on_delete=models.PROTECT); product=models.ForeignKey(Product,on_delete=models.PROTECT)
    serial_number=models.ForeignKey(SerialNumber,null=True,blank=True,on_delete=models.PROTECT); claim_date=models.DateField(default=timezone.localdate); status=models.CharField(max_length=20,default="OPEN"); resolution=models.TextField(blank=True)
class Expense(TimeStamped):
    reference=models.CharField(max_length=60); expense_date=models.DateField(default=timezone.localdate); category=models.CharField(max_length=80)
    amount=models.DecimalField(max_digits=16,decimal_places=2); notes=models.TextField(blank=True)
class Account(TimeStamped):
    code=models.CharField(max_length=30,unique=True); name=models.CharField(max_length=120); account_type=models.CharField(max_length=30)
    def __str__(self): return f"{self.code} - {self.name}"
class JournalEntry(TimeStamped):
    number=models.CharField(max_length=40,unique=True); entry_date=models.DateField(default=timezone.localdate); narration=models.TextField(blank=True); status=models.CharField(max_length=20,default="DRAFT")
class JournalLine(TimeStamped):
    journal=models.ForeignKey(JournalEntry,on_delete=models.CASCADE,related_name="lines"); account=models.ForeignKey(Account,on_delete=models.PROTECT)
    debit=models.DecimalField(max_digits=16,decimal_places=2,default=0); credit=models.DecimalField(max_digits=16,decimal_places=2,default=0)
class SafetyIncident(TimeStamped):
    number=models.CharField(max_length=40,unique=True); incident_date=models.DateTimeField(); location=models.CharField(max_length=120); description=models.TextField()
    severity=models.CharField(max_length=20,default="LOW"); corrective_action=models.TextField(blank=True); status=models.CharField(max_length=20,default="OPEN")

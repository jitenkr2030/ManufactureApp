from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Company,Unit,Product,Warehouse,Stock,StockMovement,BOM,BOMLine
from .services import post_stock_movement,calculate_mrp
class InventoryTests(TestCase):
 def setUp(self):
  c=Company.objects.create(name="Test",code="T"); u=Unit.objects.create(name="Piece",symbol="PCS")
  self.p=Product.objects.create(sku="RM1",name="Steel",kind="RAW",unit=u)
  self.w=Warehouse.objects.create(company=c,name="Main",code="M")
  self.s=Stock.objects.create(product=self.p,warehouse=self.w,quantity=Decimal("10"))
 def test_receipt_posts_ledger_and_stock(self):
  post_stock_movement(stock=self.s,movement_type=StockMovement.Type.RECEIPT,quantity_delta=5)
  self.s.refresh_from_db(); self.assertEqual(self.s.quantity,Decimal("15"))
 def test_prevents_negative_stock(self):
  with self.assertRaises(ValidationError):
   post_stock_movement(stock=self.s,movement_type=StockMovement.Type.ISSUE,quantity_delta=-11)
 def test_multilevel_mrp(self):
  u=self.p.unit; sub=Product.objects.create(sku="SUB",name="Sub",kind="WIP",unit=u)
  fg=Product.objects.create(sku="FG",name="Finished",kind="FG",unit=u)
  b1=BOM.objects.create(product=sub); BOMLine.objects.create(bom=b1,component=self.p,quantity=2)
  b2=BOM.objects.create(product=fg); BOMLine.objects.create(bom=b2,component=sub,quantity=3)
  rows=calculate_mrp(b2,2,self.w)
  self.assertEqual(rows[0]["gross"],Decimal("12"))

from rest_framework.routers import DefaultRouter
from rest_framework import serializers,viewsets
from rest_framework.permissions import IsAuthenticated
from django.apps import apps
from .models import Product,Stock,BOM,ProductionOrder,Supplier,Warehouse,PurchaseOrder,QCInspection,MRPRun,ProductionSchedule,ApprovalRequest
class AutoSerializer(serializers.ModelSerializer):
 class Meta: model=Product; fields="__all__"
def make_viewset(model):
 serializer=type(model.__name__+"Serializer",(AutoSerializer,),{"Meta":type("Meta",(),{"model":model,"fields":"__all__"})})
 return type(model.__name__+"ViewSet",(viewsets.ModelViewSet,),{"queryset":model.objects.all(),"serializer_class":serializer,"permission_classes":[IsAuthenticated]})
router=DefaultRouter()
for endpoint,model in [("products",Product),("stock",Stock),("boms",BOM),("production-orders",ProductionOrder),("suppliers",Supplier),("warehouses",Warehouse),("purchase-orders",PurchaseOrder),("qc-inspections",QCInspection),("mrp-runs",MRPRun),("schedules",ProductionSchedule),("approvals",ApprovalRequest)]:
 router.register(endpoint,make_viewset(model),basename=endpoint)
urlpatterns=router.urls

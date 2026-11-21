from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group,Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

ROLE_MODELS={
 "Factory Manager":None,
 "Production Manager":["product","bom","bomline","productionorder","productionschedule","routing","operation","workcenter","machine","operationexecution","wiprecord","scraprecord","reworkorder","costsheet"],
 "Production Planner":["product","bom","bomline","productionorder","productionschedule","mrprun","mrpline","workcenter","machine"],
 "Store Manager":["product","warehouse","location","stock","stockmovement","stocktransfer","stocktransferline","goodsreceipt","goodsreceiptline","materialissue","materialissueline","batch","serialnumber"],
 "Purchase Manager":["supplier","purchaserequisition","purchaseorder","purchaseorderline","goodsreceipt","goodsreceiptline"],
 "QC Inspector":["qcinspection","inspectionparameter","inspectionfinding","defect","product","batch","serialnumber"],
 "Sales Manager":["customer","salesorder","salesorderline","delivery","returnauthorization","warrantyclaim"],
 "Maintenance Manager":["machine","maintenanceplan","maintenanceorder","safetyincident"],
 "HR Manager":["employee","shift","attendance","department"],
 "Accountant":["account","journalentry","journalline","expense","costsheet"],
 "Auditor":["auditlog","stockmovement","productionorder","purchaseorder","goodsreceipt","qcinspection","costsheet"],
}
class Command(BaseCommand):
    help="Create ERP role groups and grant module-level permissions."
    def handle(self,*args,**options):
        app_models={m._meta.model_name:m for m in apps.get_app_config("erp").get_models()}
        for role,names in ROLE_MODELS.items():
            group,_=Group.objects.get_or_create(name=role)
            selected=list(app_models.values()) if names is None else [app_models[n] for n in names if n in app_models]
            perms=[]
            for model in selected:
                ct=ContentType.objects.get_for_model(model)
                perms.extend(Permission.objects.filter(content_type=ct,codename__in=[
                    f"add_{model._meta.model_name}",f"view_{model._meta.model_name}",
                    f"change_{model._meta.model_name}",f"delete_{model._meta.model_name}"]))
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"{role}: {len(perms)} permissions"))
        self.stdout.write(self.style.SUCCESS("ERP role groups created. Assign users to groups in Users & Groups."))

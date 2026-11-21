from django.contrib import admin
from django.apps import apps
admin.site.site_header="Manufacturing ERP V2 — System Administration"
admin.site.site_title="Manufacturing ERP"
admin.site.index_title="Administration & Configuration"
for model in apps.get_app_config("erp").get_models():
    try: admin.site.register(model)
    except admin.sites.AlreadyRegistered: pass

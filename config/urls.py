from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from erp import views
urlpatterns=[
 path("admin/",admin.site.urls),
 path("accounts/login/",auth_views.LoginView.as_view(template_name="registration/login.html"),name="login"),
 path("accounts/logout/",auth_views.LogoutView.as_view(),name="logout"),
 path("",views.dashboard,name="dashboard"),
 path("module/<slug:slug>/",views.module_list,name="module-list"),
 path("module/<slug:slug>/new/",views.module_create,name="module-create"),
 path("module/<slug:slug>/<int:pk>/edit/",views.module_create,name="module-edit"),
 path("module/<slug:slug>/<int:pk>/delete/",views.module_delete,name="module-delete"),
 path("mrp/",views.mrp_view,name="mrp"),path("planning/calendar/",views.calendar_view,name="calendar"),
 path("workflow/<slug:kind>/<int:pk>/",views.workflow_action,name="workflow-action"),
 path("production/finished-goods/receive/",views.fg_receipt,name="fg-receipt"),
 path("reports/",views.reports,name="reports"),path("reports/stock.xlsx",views.export_stock,name="export-stock"),
 path("reports/production.xlsx",views.export_production,name="export-production"),\n path("reports/stock.pdf",views.export_stock_pdf,name="export-stock-pdf"),\n path("products/<int:pk>/qr.png",views.product_qr,name="product-qr"),
 path("audit/",views.audit_view,name="audit"),path("api/",include("erp.api_urls")),
 path("health/",lambda request:JsonResponse({"status":"ok"})),
]

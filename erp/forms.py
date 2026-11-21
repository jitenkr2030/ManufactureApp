from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from .models import *
class StyledModelForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            cls="form-select" if isinstance(field,forms.ModelChoiceField) else "form-control"
            field.widget.attrs["class"]=cls
            if isinstance(field,forms.DateInput): field.widget.attrs["type"]="date"
            if isinstance(field,forms.DateTimeInput): field.widget.attrs["type"]="datetime-local"
class DynamicForm(StyledModelForm):
    class Meta: model=Product; fields="__all__"
def form_for(model):
    Meta=type("Meta",(),{"model":model,"fields":"__all__","exclude":["created_at","updated_at"]})
    return type(f"{model.__name__}Form",(StyledModelForm,),{"Meta":Meta})
class MRPForm(forms.Form):
    bom=forms.ModelChoiceField(queryset=BOM.objects.filter(is_active=True))
    warehouse=forms.ModelChoiceField(queryset=Warehouse.objects.all())
    quantity=forms.DecimalField(min_value=0.001,decimal_places=3)
    demand_date=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
class FGReceiptForm(forms.Form):
    order=forms.ModelChoiceField(queryset=ProductionOrder.objects.exclude(status="COMPLETED"))
    warehouse=forms.ModelChoiceField(queryset=Warehouse.objects.all())
    quantity=forms.DecimalField(min_value=0.001,decimal_places=3)
    batch_no=forms.CharField(required=False)

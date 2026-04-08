from django.contrib import admin
from sales import models

# Register your models here.

@admin.register(models.Properties)
class propertiesAdmin(admin.ModelAdmin):
    list_display = ['description', 'project','block', 'location','state']
    list_filter = ['project']
    search_fields = ['description']

@admin.register(models.Sales_plans)
class sales_plansAdmin(admin.ModelAdmin):
    list_display = ['name', 'initial_payment', 'to_finance', 'rate','status']

@admin.register(models.Sales)
class salesAdmin(admin.ModelAdmin):
    list_display = ['id_sale', 'contract_number','project', 'first_owner', 'property_sold', 'value', 'add_date']
    list_filter = ['project']
    search_fields = ['property_sold__description','first_owner__first_name','first_owner__last_name',
                     'second_owner__first_name','second_owner__last_name',
                     'third_owner__first_name','third_owner__last_name']
    date_hierarchy = 'add_date'

@admin.register(models.Payment_plans)
class payment_plansAdmin(admin.ModelAdmin):
    list_display = ['id_payment', 'sale', 'id_quota','capital', 'interest', 'others', 'project']
    list_filter = ['project','quota_type']
    search_fields = ['sale__contract_number','sale__first_owner__first_name']

@admin.register(models.Sales_history)
class sales_historyAdmin(admin.ModelAdmin):
    list_display = ['sale', 'action', 'add_date', 'user']

@admin.register(models.Comission_position)
class comissionpositionAdmin(admin.ModelAdmin):
    list_display = ['id_charge', 'name', 'group','project','default','rate','advance_bonus','is_active']
    list_filter = ['group','project','is_active']
    
from .models import PaymentPlanRestructuring, PaymentPlanRestructuringDetail

@admin.register(PaymentPlanRestructuring)
class PaymentPlanRestructuringAdmin(admin.ModelAdmin):
    list_display = (
        'id_restructuring', 'sale', 'created_by', 'created_at', 'status', 'tasa'
    )
    list_filter = ('status', 'created_at', 'sale__project')
    search_fields = ('sale__contract_number', 'created_by__username', 'sale__project__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

@admin.register(PaymentPlanRestructuringDetail)
class PaymentPlanRestructuringDetailAdmin(admin.ModelAdmin):
    list_display = (
        'restructuring', 'id_quota', 'quota_type', 'pay_date', 'capital', 'interest', 'others', 'tipo'
    )
    list_filter = ('quota_type', 'tipo', 'pay_date')
    search_fields = ('restructuring__sale__contract_number',)


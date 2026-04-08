from django.contrib import admin
from finance import models
from finance.models import Collection_budget, Collection_budget_detail
from .models import SolicitudRecibo, AbonoCapital, ComisionGestorCartera, CommentType


# Register your models here.

@admin.register(models.Payment_methods)
class paymentmethodsAdmin(admin.ModelAdmin):
    list_display = ['name']
@admin.register(models.Incomes)
class IncomesAdmin(admin.ModelAdmin):
    list_display = ['receipt','project','add_date','sale','value','pk']
    list_filter=['project']
    search_fields = ['receipt__exact','sale__contract_number','sale__first_owner__first_name']
    date_hierarchy = 'add_date'

@admin.register(models.Incomes_detail)
class IncomesDetailAdmin(admin.ModelAdmin):
    list_display = ['pk','quota','capital','interest','others','arrears','income']
    list_filter=['income__project']
    search_fields = ['pk','income__receipt','income__sale__contract_number']

@admin.register(models.payment_accounts)
class paymentaccountsAdmin(admin.ModelAdmin):
    list_display = ['nit_to_pay','account_number','account_type']
    
@admin.register(models.cost_center)
class costcenterAdmin(admin.ModelAdmin):
    list_display = ['name','project','percentage']
    
class CollectionBudgetDetailInline(admin.TabularInline):
    model = Collection_budget_detail
    extra = 0
    readonly_fields = ('sale', 'collector', 'lt_30', 'lt_60', 'lt_90', 'lt_120', 'gt_120')
    can_delete = False
    
@admin.register(Collection_budget)
class CollectionBudgetAdmin(admin.ModelAdmin):
    list_display = ('project', 'year', 'month', 'user', 'date_add')
    list_filter = ('project', 'year', 'month')
    search_fields = ('project__name', 'user__username')
    inlines = [CollectionBudgetDetailInline]
    readonly_fields = ('project', 'year', 'month', 'user', 'date_add')
    ordering = ('-year', '-month')

@admin.register(SolicitudRecibo)
class SolicitudReciboAdmin(admin.ModelAdmin):
    list_display = ['id', 'sale', 'estado', 'add_date', 'creado_por']
    search_fields = ['sale__contract_number', 'creado_por__username']
    list_filter = ['estado', 'add_date']

@admin.register(AbonoCapital)
class AbonoCapitalAdmin(admin.ModelAdmin):
    list_display = ['id', 'sale', 'tipo', 'capital_aplicado', 'cuotas_afectadas', 'nueva_cuota', 'income']
    search_fields = ['sale__contract_number']

@admin.register(ComisionGestorCartera)
class ComisionGestorCarteraAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_cartera', 'porcentaje_comision')
    list_filter = ('tipo_cartera',)

@admin.register(CommentType)
class CommentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    ordering = ['name']
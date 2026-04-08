import calendar
from datetime import date, datetime
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum, Max
from django.db.models.query import F
from django.db.models.query_utils import Q
from mcd_site.models import Parameters, Projects
from dateutil import relativedelta
from django.conf import settings

from sales.models import Assigned_comission, Paid_comissions, Payment_plans, Sales
from terceros.models import Sellers

# Create your models here.
class Payment_methods(models.Model):
    name = models.CharField(max_length=255,verbose_name='Nombre')
    
    class Meta:
        verbose_name = 'Metodo de pago'
        verbose_name_plural = 'Metodos de pago'
        
    def __str__(self):
        return self.name

class Incomes(models.Model):
    project = models.ForeignKey(Projects,on_delete=models.PROTECT,
                                related_name='project_incomes',verbose_name='Proyecto')
    sale = models.ForeignKey(Sales,on_delete=models.PROTECT,
                             related_name='sale_income',verbose_name='Venta')
    receipt = models.CharField(verbose_name='Recibo',max_length=20)
    add_date = models.DateField(verbose_name='Fecha de registro')
    payment_date = models.DateField(verbose_name='Fecha de pago')
    value = models.IntegerField(verbose_name='Valor')
    payment_method = models.ForeignKey(Payment_methods,on_delete=models.PROTECT,
                                       verbose_name='Forma de pago')
    description = models.CharField(max_length=255,verbose_name='Descripcion')
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name='user_incomes',
                             verbose_name='Usuario')
    
    value1 = models.IntegerField(verbose_name='Valor FP1', null=True, blank=True)
    pm1 = models.ForeignKey(Payment_methods,on_delete=models.PROTECT, null=True, blank=True,
                            verbose_name='Forma de pago 1', related_name='FP1')
    value2 = models.IntegerField(verbose_name='Valor FP2', null=True, blank=True)
    pm2 = models.ForeignKey(Payment_methods,on_delete=models.PROTECT, null=True, blank=True,
                            verbose_name='Forma de pago 2', related_name='FP2')
    obs_1 = models.CharField(max_length=255, verbose_name='Observacion 1',
                             null=True, blank=True)
    obs_2 = models.CharField(max_length=255, verbose_name='Observacion 2',
                             null=True, blank=True)
    
    class Meta:
        verbose_name = 'Recaudo'
        verbose_name_plural = 'Recaudos'
        unique_together = ['receipt','project']
        
    def __str__(self):
        return f'{self.receipt}-{self.project.name}'
    
    def add_date_uk(self):
        
        return datetime.strftime(self.add_date,'%Y/%m/%d')

    def payment_date_uk(self):
        return datetime.strftime(self.payment_date, '%Y/%m/%d')
    
    def fp(self):
        val = self.payment_method.name
        
        if self.pm2:
            val += f'/{self.pm2.name}'
             
        return val
    
class Incomes_detail(models.Model):
    income = models.ForeignKey(Incomes,on_delete=models.CASCADE,
                               verbose_name='Ingresos',)
    quota = models.ForeignKey(Payment_plans,on_delete=models.DO_NOTHING,
                              verbose_name='Cuota pagada')
    capital = models.DecimalField(decimal_places=2,max_digits=20)
    interest = models.DecimalField(decimal_places=2,max_digits=20, verbose_name='Interés corriente')
    others = models.DecimalField(decimal_places=2,max_digits=20, verbose_name='Otros')
    arrears = models.DecimalField(decimal_places=2,max_digits=20, verbose_name='Mora')
    arrears_days = models.IntegerField(verbose_name='Mora')
    
    class Meta:
        verbose_name = 'Recaudo detallado'
        verbose_name_plural = 'Recaudos detallados'
        
    def total_income(self):
        total = self.capital + self.interest + self.others + self.arrears
        return total

    def __str__(self):
        return self.quota.id_quota
    
class Incomes_return(models.Model):
    sale = models.ForeignKey(Sales, on_delete=models.PROTECT,
                             verbose_name='Contrato')
    date = models.DateField(verbose_name='Fecha')
    value = models.IntegerField(verbose_name='Valor')
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    
class Meta:
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'


def get_min_commission_value(project):
    project_obj = project
    if isinstance(project_obj, str):
        project_obj = Projects.objects.filter(pk=project_obj).first()
    param = Parameters.objects.filter(name='valor_minimo_comision', project=project_obj).first()
    if param is None:
        param = Parameters.objects.filter(name='valor_minimo_comision', project__isnull=True).first()
    if param and param.value is not None:
        return Decimal(str(param.value))
    return Decimal('0')


def get_commission_method(project):
    project_obj = project
    if isinstance(project_obj, str):
        project_obj = Projects.objects.filter(pk=project_obj).first()
    method = Parameters.objects.filter(name='metodo_liquidacion_comision', project=project_obj).first()
    advance = Parameters.objects.filter(name='porcentaje_avance_comision', project=project_obj).first()
    if method is None:
        method = Parameters.objects.filter(name='metodo_liquidacion_comision', project__isnull=True).first()
    if advance is None:
        advance = Parameters.objects.filter(name='porcentaje_avance_comision', project__isnull=True).first()
    method_val = int(method.value) if method and method.value is not None else 0
    advance_val = Decimal(str(advance.value)) if advance and advance.value is not None else Decimal('30')
    return method_val, advance_val

from django.db import models
from django.contrib.auth.models import User

class SolicitudRecibo(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'), 
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('ajuste', 'Requiere Ajuste'),
    ]

    project = models.ForeignKey('mcd_site.Projects', on_delete=models.PROTECT,
                                related_name='solicitudes_recibo_proyecto', verbose_name='Proyecto')
    sale = models.ForeignKey('sales.Sales', on_delete=models.PROTECT,
                             related_name='solicitudes_recibo_venta', verbose_name='Venta')
    
    add_date = models.DateField(auto_now_add=True, verbose_name='Fecha de solicitud')
    payment_date = models.DateField(verbose_name='Fecha real de pago')
    
    # Formas de pago opcionales (desglose)
    value1 = models.CharField(max_length=255,verbose_name='Valor FP1', null=True, blank=True)
    pm1 = models.ForeignKey('Payment_methods', on_delete=models.PROTECT,
                            null=True, blank=True, verbose_name='Forma de pago 1', related_name='sol_fp1')
    value2 = models.CharField(max_length=255,verbose_name='Valor FP2', null=True, blank=True)
    pm2 = models.ForeignKey('Payment_methods', on_delete=models.PROTECT,
                            null=True, blank=True, verbose_name='Forma de pago 2', related_name='sol_fp2')

    description = models.CharField(max_length=255, verbose_name='Descripción')
    obs_1 = models.CharField(max_length=255, verbose_name='Observación 1', null=True, blank=True)
    obs_2 = models.CharField(max_length=255, verbose_name='Observación 2', null=True, blank=True)

    arrears_condonate = models.IntegerField(verbose_name='Condonación mora (%)', default=0)
    capital_payment = models.BooleanField(
        verbose_name='Abono a capital',
        default=False,
        help_text='El abono a capital se aplicará despues de pagar las cuotas vencidas.'
    )
    TIPO_ABONO_CHOICES = [
        ('', '---------'),
        ('reducir_tiempo', 'Abono con reducción de tiempo'),
        ('reducir_cuota', 'Abono con reducción de cuota'),
        ('cuotas_futuras', 'Abono a cuotas futuras'),
    ]
    tipo_abono_capital = models.CharField(
        max_length=20, choices=TIPO_ABONO_CHOICES, blank=True, default=''
    )
    
    # Archivos de soporte
    soporte = models.FileField(upload_to='soportes_recibos/', null=True, blank=True, verbose_name='Soporte')

    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente', verbose_name='Estado')
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='solicitudes_creadas')
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name='solicitudes_revisadas')
    # al final del modelo SolicitudRecibo
    condonacion_autorizada = models.BooleanField(default=False)
    condonacion_autorizada_por = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name='condonacion_autorizada_por')
    recibo_generado = models.OneToOneField('Incomes', on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name='solicitud_origen',
                                           verbose_name='Recibo generado')

    observaciones_revision = models.TextField(null=True, blank=True, verbose_name='Notas de tesorería')

    confirmado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Solicitud de Recibo"
        verbose_name_plural = "Solicitudes de Recibo"

    def __str__(self):
        return f"Solicitud #{self.id} - {self.project} - {self.sale}"
    
        # Si los campos son calculados:
        
    def total_solicitud(self):
        t1 = 0 if self.value1 == '' or self.value1 == None else int(self.value1.replace(',',''))
        t2 = 0 if self.value2 == '' or self.value2 == None else int(self.value2.replace(',',''))
        return t1 + t2

    def mora_actual(self):
        """Calcula la mora actual del cliente al momento de la solicitud"""
        from finance.models import Credit_info
        
        mora_total = 0
        cuotas = Credit_info.objects.filter(sale=self.sale)
        
        for cuota in cuotas:
            if cuota.pay_date <= self.payment_date:
                pending = cuota.quota_pending()
                if pending.get('total_pending', 0) > 0:
                    arrears_info = cuota.arrears_info(paid_day=self.payment_date)
                    mora_total += arrears_info.get('r_value', 0)
        
        return mora_total
    
    def valor_condonacion(self):
        """Calcula el valor de la condonación basado en el porcentaje"""
        if self.arrears_condonate > 0:
            return self.mora_actual() * (self.arrears_condonate / 100)
        return 0
    
    def mora_despues_condonacion(self):
        """Calcula la mora que quedaría después de aplicar la condonación"""
        return self.mora_actual() - self.valor_condonacion()
    
class AbonoCapital(models.Model):
    TIPO_ABONO_CHOICES = [
        ('', '---------'),
        ('reducir_tiempo', 'Abono con reducción de tiempo'),
        ('reducir_cuota', 'Abono con reducción de cuota'),
        ('cuotas_futuras', 'Abono a cuotas futuras'),
    ]
    income = models.ForeignKey(Incomes, on_delete=models.PROTECT)
    sale = models.ForeignKey(Sales, on_delete=models.PROTECT)
    tipo = models.CharField(choices=TIPO_ABONO_CHOICES, max_length=20, default='', verbose_name='Tipo de abono')
    capital_aplicado = models.FloatField(verbose_name='Capital aplicado')
    fecha = models.DateField(auto_now_add=True)
    cuotas_afectadas = models.IntegerField()
    nueva_cuota = models.FloatField(null=True, blank=True)
    valor_comision = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comision_pagado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='abonos_pagados_a',
        null=True, blank=True,
        limit_choices_to={'is_active': True}
    )
    comision_pagado_el = models.DateTimeField(null=True, blank=True)
    comision_pagado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='abonos_pagados_por',
        null=True, blank=True
    )
    
    def gestor(self):
        det = self.sale.collection_budget_detail_set.filter(
            budget__year=self.income.payment_date.year,
            budget__month=self.income.payment_date.month
        ).first()
        if det:
            return det.collector
        if hasattr(self.sale, "sale_collector") and self.sale.sale_collector:
            return self.sale.sale_collector.collector_user
        return None

class ComisionGestorCartera(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo_cartera = models.CharField(max_length=50,choices=[('comercial', 'Comercial'), ('administrativa', 'Administrativa')])
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2)

class Collector_per_sale(models.Model):
    sale = models.OneToOneField(Sales,on_delete=models.CASCADE,related_name='sale_collector',
                             verbose_name='Contrato')
    collector_user = models.ForeignKey(User,on_delete=models.PROTECT,related_name='user_collector_sale',
                                       verbose_name='Gestor de cobro asignado')
    
    class Meta:
        verbose_name = 'Gestor de cobro por venta'
        verbose_name_plural = 'Gestores de cobro por ventas'
        
class Collection_budget(models.Model):
    project = models.ForeignKey(Projects,on_delete=models.PROTECT,verbose_name='Proyecto',
                                related_name='project_collection')
    class Months(models.IntegerChoices):
        Enero = 1
        Febrero = 2
        Marzo = 3
        Abril = 4
        Mayo = 5
        Junio = 6
        Julio = 7
        Agosto = 8
        Septiembre = 9
        Octubre = 10
        Noviembre = 11
        Diciembre = 12
        
    month = models.IntegerField(choices=Months.choices,verbose_name='Mes')
    year = models.IntegerField(verbose_name='Año')
    user = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Usuario carga',
                             related_name='user_collection_budget')
    date_add = models.DateTimeField(auto_now_add=True,verbose_name='Fecha de carga')
    
    class Meta:
        verbose_name = 'Presupuesto de cartera'
        verbose_name_plural = 'Presupuestos de cartera'
        unique_together = ['project','year','month']

class Collection_budget_detail(models.Model):
    budget = models.ForeignKey(Collection_budget,on_delete=models.CASCADE,verbose_name='Id Presupuesto')
    sale = models.ForeignKey(Sales,on_delete=models.PROTECT,verbose_name='Venta')
    collector = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Gestor')
    lt_30 = models.FloatField(verbose_name='<30',default=0)
    lt_60 = models.FloatField(verbose_name='<60',default=0)
    lt_90 = models.FloatField(verbose_name='<90',default=0)
    lt_120 = models.FloatField(verbose_name='<120',default=0)
    gt_120 =models.FloatField(verbose_name='>120',default=0)
    CARTERA_CHOICES = [
        ('comercial', 'Comercial'),
        ('administrativa', 'Administrativa'),
    ]

    portfolio_type = models.CharField(
        max_length=20,
        choices=CARTERA_CHOICES,
        default='commercial',
        verbose_name='Portfolio type'
    )
    
    class Meta:
        verbose_name = 'Presupuesto de cartera - detalle'
        verbose_name_plural = 'Presupuestos de cartera - detalles'
        unique_together = ['budget','sale']
    
    def total(self):
        return self.lt_30 + self.lt_60 + self.lt_90 + self.lt_120 + self.gt_120
    
    def period_incomes(self):
        year = self.budget.year
        month = self.budget.month
        last_day = calendar.monthrange(year,month)[1]
        period_first_day = date(year,month,1)
        period_last_day = date(year,month,last_day)
        total = self.total()
        
        obj_inc = Incomes_detail.objects.filter(
                                    income__add_date__gte=period_first_day,
                                    income__add_date__lte=period_last_day,
                                    income__sale = self.sale.pk,
                        )
        total_period_incomes = obj_inc.aggregate(total=Sum('capital')+Sum('interest')).get('total')
        total_arrears = obj_inc.aggregate(total=Sum('arrears')).get('total')
        
        if total_period_incomes == None: total_period_incomes = 0
        if total_arrears == None: total_arrears = 0
        
        budget_pending = total - float(total_period_incomes)
        excedent = 0
        if budget_pending < 0:
            excedent = budget_pending * -1
            budget_pending = 0
        
        try:
            compliance = float(total_period_incomes) *100 / total
        except ZeroDivisionError:
            compliance = float(total_period_incomes) *100
        total_incomes = int(total_period_incomes) + int(total_arrears) + excedent

        return {
            'period_income':total_period_incomes,
            'total_arrears':total_arrears,
            'excedent':excedent,
            'total_incomes':total_incomes,
            'budget_pending':budget_pending,
            'compliance':compliance,
        }
        
class CommentType(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre', unique=True)
    description = models.CharField(max_length=255, verbose_name='Descripción', blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Tipo de comentario'
        verbose_name_plural = 'Tipos de comentarios'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Collection_feed(models.Model):
    sale = models.ForeignKey(Sales,on_delete=models.CASCADE,
                related_name='sale_colleciton_feed',verbose_name='Contrato')
    comment_type = models.ForeignKey(CommentType, on_delete=models.PROTECT,
                                     verbose_name='Tipo de seguimiento',
                                     limit_choices_to={'is_active': True})
    comment = models.CharField(max_length=500,verbose_name='Comentario')
    add_date= models.DateTimeField(auto_now_add=True,verbose_name='Fecha y hora')
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name='user_collection_feed',
                             verbose_name='Usuario')
    
    class Meta:
        verbose_name = 'Seguimiento de cartera'
        verbose_name_plural = 'Seguimientos de cartera'
    
    def __str__(self):
        return f'{self.sale.contract_number}-{self.user.username} el {self.add_date}'

class PMT(models.Model):
    add_date = models.DateField(verbose_name='Fecha',auto_now_add=True)
    project = models.ForeignKey(Projects,on_delete=models.PROTECT,
                                verbose_name='Proyecto')
    observations = models.CharField(max_length=255,verbose_name='Observaciones')
    user = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Usuario registra')
    user_approve = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Usuario aprueba',
                                     related_name='user_approve_pmt',null=True,blank=True)
    state = models.CharField(max_length=255,choices=(
        ('Pendiente','Pendiente'),
        ('Aprobado','Aporbado')
    ),verbose_name='Estado')
    
    class Meta:
        verbose_name = 'PMT'
        verbose_name_plural = 'PMTs'
        unique_together = ['project','add_date']
    
        
    def sellers_quanty(self):
        return PMT_detail.objects.filter(pmt = self.pk).count()
    
    def total(self):
        total_pmt = PMT_detail.objects.filter(pmt = self.pk).aggregate(total=Sum('value')).get('total')
        if total_pmt == None: total_pmt = 0
        
        return total_pmt

class PMT_detail(models.Model):
    pmt = models.ForeignKey(PMT,on_delete=models.CASCADE,verbose_name='PMT asociado')
    seller = models.ForeignKey(Sellers,on_delete=models.PROTECT,
                               verbose_name='Vendedor',related_name='seller_pmt')
    value = models.IntegerField(verbose_name='Valor')
    
    class Meta:
        verbose_name = 'PMT detalle'
        verbose_name_plural = 'PMTs detalle'
    
    def seller_fullname(self):
        return self.seller.full_name()
    
class payment_accounts(models.Model):
    account_number = models.BigIntegerField(verbose_name='Numero de cuenta',unique=True)
    nit_to_pay = models.IntegerField(verbose_name='Nit empresa pagadora')
    account_type = models.CharField(verbose_name='Tipo de cuenta',choices=(
        ('S','Ahorros'),
        ('D','Corriente'),
    ),max_length=10)
    
    class Meta:
        verbose_name = 'Cuenta bancaria'
        verbose_name_plural = 'Cuentas bancarias'
        
    def __str__(self):
        return str(self.account_number)

class cost_center(models.Model):
    name = models.CharField(max_length=255,verbose_name='Nombre')
    project = models.ForeignKey(Projects,on_delete=models.PROTECT,
                                verbose_name='Proyecto',related_name='project_cc')
    from_date = models.DateField(verbose_name='Periodo desde',null=True,blank=True)
    to_date = models.DateField(verbose_name='Periodo hasta',null=True,blank=True)
    percentage = models.FloatField(verbose_name='Porcentaje')
    
    class Meta:
        verbose_name = 'Centro de costo'
        verbose_name_plural = 'Centros de costo'
        
    def __str__(self):
        return self.name
    
    
    def statics(self,month,year):
        month_data = calendar.monthrange(year,month)
        last_day = date(year,month,month_data[1])
        first_day = date(year,month,month_data[0])
            
        obj_incomes = Incomes.objects.filter(
                project = self.project.name, add_date__gte = first_day,
                add_date__lte = last_day
        ).aggregate(total=Sum('value')).get('total',0)
        total_incomes = 0 if obj_incomes is None else int(obj_incomes * self.percentage/100)
        
        obj_expenses = expenses_detail.objects.filter(
                project=self.project.name,date__gte=first_day,date__lte=last_day,
                costcenter = self.pk
            ).aggregate(total=Sum('value')).get('total',0)

        print(self.pk)
        total_expenses = 0 if obj_expenses is None else obj_expenses
        
        remaining = total_incomes - total_expenses
        try:
            perc_avb = (total_incomes - total_expenses) * 100 / total_incomes 
        except ZeroDivisionError:
            perc_avb = (total_incomes - total_expenses) * 100 
        
        data = {
            'total_incomes':total_incomes,
            'total_expenses':total_expenses,
            'remaining':remaining,
            'perc_avb':perc_avb,
        }
        
        return data
        
class expenses_detail(models.Model):
    project = models.ForeignKey(Projects,on_delete=models.PROTECT,
                                verbose_name='Proyecto',related_name='project_expense')
    date = models.DateField(verbose_name='Fecha gasto')
    description = models.CharField(max_length=255)
    costcenter = models.ForeignKey(cost_center,on_delete=models.PROTECT,
                                   verbose_name='Centro de costo',related_name='cc_expenses')
    value = models.IntegerField()
    user = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Usuario registra')
    
    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'


class Commercial_budget(models.Model):
    add_date = models.DateField(verbose_name='Fecha Solicitud',auto_now_add=True)
    user_request = models.ForeignKey(User, on_delete = models.PROTECT,
                                     related_name='user_request',verbose_name='Usuario solicita')
    
    notes = models.CharField(max_length=255, null=True, blank=True, verbose_name='Notas')
    user_approve = models.ForeignKey(User, on_delete = models.PROTECT,
                                     related_name='user_approve',
                                     verbose_name='Usuario aprueba',
                                     null=True, blank=True)
    approve_date = models.DateField(verbose_name='Fecha aprovación',
                                    null=True, blank=True)
    status = models.CharField(max_length=255, choices=[
        ('Aprobado','Aprobado'),
        ('Pendiente','Pendiente')
    ],default='Pendiente')
    project = models.ForeignKey(Projects, on_delete=models.PROTECT,
                                null=True, blank=True)
    
    class Meta:
        verbose_name = 'Presupuesto comercial'
        verbose_name_plural = 'Presupuestos comerciales'
    
    def totalize(self):
        detail = Commercial_budget_detail.objects.filter(budget=self.pk)
        
        total = detail.aggregate(total=Sum('value')).get('total')
        
        total = 0 if total == None else total
        
        return total
    
    def date_uk(self):
        
        return datetime.strftime(self.add_date,'%d/%m/%Y')
    
    
class Commercial_budget_detail(models.Model):
    budget = models.ForeignKey(Commercial_budget,on_delete=models.CASCADE,
                                verbose_name='Solicitud')
    value = models.IntegerField(verbose_name='Valor solicitado')
    concept = models.CharField(max_length=255, verbose_name='Concepto')
    

#proxys 
class Sales_extra_info(Sales):
    
    class Meta:
        proxy = True
    
    def basic_info(self):
        obj_income = Incomes_detail.objects.filter(
            quota__sale = self.pk
        )
        """ for i  in obj_income:
            print(i.income,'--------------')
            print(i.income.receipt,i.income.sale) """
        paid_capital = obj_income.aggregate(Sum('capital')).get('capital__sum')
        if paid_capital is None: paid_capital = 0
        rv = self.value - paid_capital
        data = {
            'remaining_value':rv,
            'paid_capital':paid_capital
        }
        
        return data
    
    def rv_by_type_of_quota(self):
        obj_payment_plan = Payment_plans.objects.filter(
            sale = self.pk
        )
        
        ci_total = obj_payment_plan.filter(
            quota_type = 'CI'
        ).aggregate(total=Sum('capital')
                    ).get('total')
        
        if ci_total == None: ci_total = 0
        
        finance_total = self.value - ci_total
        
        obj_paid = Incomes_detail.objects.filter(
            quota__sale = self.pk,
        )
        
        paid_ci = obj_paid.filter(
            quota__quota_type="CI"
            ).aggregate(total=Sum('capital')
                    ).get('total')
        
        if paid_ci == None: paid_ci = 0    
        
        paid_finance = obj_paid.exclude(
            quota__quota_type="CI"
            ).aggregate(total=Sum('capital')
                    ).get('total')

        if paid_finance == None: paid_finance = 0
        
        
        pendient_ci = ci_total - paid_ci
        pendient_finance = finance_total - paid_finance
        
        data = {
            'paid_ci':paid_ci,
            'pendient_ci':pendient_ci,
            'paid_finance':paid_finance,
            'pendient_finance':pendient_finance,
        }
        
        return data
    
    def total_payment(self):
        total = Incomes.objects.filter(sale=self.pk).aggregate(total=Sum('value')
                                        ).get('total')
        if total == None: total = 0
        
        return total
        
    def remain_value(self):
        capital_incomes = Incomes_detail.objects.filter(quota__sale = self.pk)
        total_capital_incomes = capital_incomes.aggregate(Sum('capital')).get('capital__sum')
        if total_capital_incomes == None: total_capital_incomes = 0
        
        return self.value - total_capital_incomes
    
    def is_paid(self):
        paid = False
        rv = self.remain_value()
        if rv == 0: paid =True
        return paid
    
    def check_comissions(self, just_check = False):
        obj_paid_comiss = Paid_comissions.objects.filter(assign_paid__sale=self.pk,assign_paid__state="Activo")
        paid_comission = obj_paid_comiss.aggregate(total=Sum('comission')
                            ).get('total',0)
        if paid_comission == None: paid_comission = 0
        
        total_sale_payment = Incomes.objects.filter(sale=self.pk
                            ).aggregate(total=Sum('value')
                            ).get('total',0)
        if total_sale_payment == None: total_sale_payment = 0
        comission_base = self.comission_base
        ci_base = self.portfolio_values().get('initial',0)
        if ci_base == 0: ci_base = 1
        initial_payment_rate = total_sale_payment / ci_base
        total_paid_decimal = Decimal(str(total_sale_payment))
        min_commission = get_min_commission_value(self.project)
        meets_minimum = (min_commission <= 0) or (total_paid_decimal >= min_commission)
        method, advance_percent = get_commission_method(self.project)
        effective_payment_rate = initial_payment_rate
        if method == 0 and min_commission > 0 and meets_minimum:
            effective_payment_rate = max(effective_payment_rate, 1)
        
        obj_comission_scale = Assigned_comission.objects.filter(sale=self.pk,state="Activo")
        total_comission_scale = obj_comission_scale.aggregate(total=Sum('comission')
                                                              ).get('total',0)
        if total_comission_scale == None: total_comission_scale = 0
        
        total_comission_value = int(comission_base * total_comission_scale/100)
        
        method, advance_percent = get_commission_method(self.project)
        total_paid_decimal = Decimal(str(total_sale_payment))
        min_commission = get_min_commission_value(self.project)
        meets_minimum = (min_commission <= 0) or (total_paid_decimal >= min_commission)
        effective_payment_rate = initial_payment_rate
        if method == 0 and min_commission > 0 and meets_minimum:
            effective_payment_rate = max(effective_payment_rate, 1)
        
        if obj_paid_comiss.filter(type_of_payment__icontains='/3').exists():
            if 0.6 > effective_payment_rate >= 0.3:
                type_of_payment = '1/3'
                comission_generate = total_comission_value * 0.3
            elif 1 > effective_payment_rate >= 0.6:
                type_of_payment = '2/3'
                comission_generate = total_comission_value * 0.6
            else:
                type_of_payment = '3/3'
                comission_generate = total_comission_value
        elif obj_paid_comiss.filter(type_of_payment__icontains='/2').exists():
            if 1 > effective_payment_rate >= 0.5:
                type_of_payment = '1/2'
                comission_generate = total_comission_value * 0.5
            else:
                type_of_payment = '2/2'
                comission_generate = total_comission_value
        else:
            if 0.5 > effective_payment_rate >= 0.3:
                comission_generate = total_comission_value * 0.3
                type_of_payment = '1/3'
            elif 1 > effective_payment_rate >= 0.5:
                comission_generate = total_comission_value * 0.5
                type_of_payment = '1/2'
            elif effective_payment_rate >= 1:
                comission_generate = total_comission_value
                type_of_payment = '1'
            else:
                comission_generate = 0
                type_of_payment = 'Sin pago'

        if method == 0:
            comission_to_pay = comission_generate - paid_comission
        else:
            if not meets_minimum:
                comission_to_pay = 0
                type_of_payment = 'Pendiente mínimo'
            else:
                required_progress = Decimal(str(advance_percent)) / Decimal('100') or Decimal('1')
                progress_ratio = total_paid_decimal / (self.value * required_progress)
                if progress_ratio > 1:
                    progress_ratio = Decimal('1')
                comission_to_pay = int(total_comission_value * progress_ratio) - paid_comission
                type_of_payment = 'Mínimo + % avance'

        if method == 0 and min_commission > 0 and not meets_minimum:
            if just_check:
                return True
            comission_to_pay = 0
            type_of_payment = 'Pendiente mínimo'
        elif method == 0 and just_check:
            if comission_to_pay > 0:
                return False
            return True
        elif method == 1:
            if not meets_minimum:
                if just_check:
                    return True
                type_of_payment = 'Pendiente mínimo'
            elif just_check:
                if comission_to_pay > 0:
                    return False
                return True

        if type_of_payment=='Sin pago' and Assigned_comission.objects.filter(sale=self.pk,
                                                position__name__icontains="tlmk").exists():
            
            paid_tlmk = Paid_comissions.objects.filter(assign_paid__sale=self.pk,assign_paid__position__name='tlmk'
                                                    ).aggregate(Sum('comission')).get('comission__sum',0)
            
            
            if paid_tlmk == None: paid_tlmk = 0
            comision_tlmk = Assigned_comission.objects.get(sale=self.pk,position__name__icontains="tlmk").comision
            total_comission_tlmk = self.comission_base * comision_tlmk /100
            
            
            
            if 4000000 > total_sale_payment >=2000000 and paid_tlmk == 0:
                comission_to_pay = self.comission_base * 0.05/100
                type_of_payment = 'Tlmk'
            elif total_sale_payment > 4000000 and paid_tlmk < total_comission_tlmk: 
                comission_to_pay = self.comission_base * 0.1/100
                type_of_payment = 'Tlmk'
            
        if min_commission > 0 and not meets_minimum:
            if just_check:
                return True
            comission_to_pay = 0
            type_of_payment = 'Pendiente mínimo'
        elif just_check:
            if comission_to_pay > 0:
                return False
            return True

        if total_comission_value == 0:
            perc_to_pay = 0
            perc_paid = 0
        else:
            perc_to_pay = int(comission_to_pay*100/total_comission_value)
            perc_paid = int(paid_comission*100/total_comission_value)
        
        
        
        data = {
            'type': type_of_payment,
            'paid_comission':paid_comission,
            'comission_to_pay':comission_to_pay,
            'perc_to_pay':perc_to_pay,
            'perc_paid':perc_paid,
        }
        
        return data
    
    def check_comission_advance(self):
        liquidate = self.check_comissions(just_check=True)
        
        if not liquidate: return False

        total_payment = Incomes.objects.filter(sale=self.pk
                            ).aggregate(total=Sum('value')
                            ).get('total',0)
        if total_payment == None: total_payment = 0
        minimal_pay = self.portfolio_values().get('initial',0)
        
        obj_paid_comiss = Paid_comissions.objects.filter(
            assign_paid__sale=self.pk
        )
        
        obj_assign_comiss = Assigned_comission.objects.filter(
            Q(position__name='Generador')|
            Q(position__name='Linea')|
            Q(position__name='Cierre'),
            sale = self.pk
        )
         
        if  minimal_pay > total_payment >= 2000000 and not obj_paid_comiss.exists() and obj_assign_comiss.exists():
            if self.contract_number == 293: print('si entra')
            return True
            
        return False
    
    def budget(self,year:int=date.today().year,month:int=date.today().month):
        obj_quotas = Credit_info.objects.filter(sale = self.pk)
        last_day = calendar.monthrange(year,month)[1]
        
        period_first_day = date(year,month,1)
        period_last_day = date(year,month,last_day)
        lt30_date = period_first_day - relativedelta.relativedelta(months=1)
        lt60_date = period_first_day - relativedelta.relativedelta(months=2)
        lt90_date = period_first_day - relativedelta.relativedelta(months=3)
        lt120_date = period_first_day - relativedelta.relativedelta(months=4)
        
        lt_30 = 0
        lt_60 = 0
        lt_90 = 0
        lt_120 = 0
        gt_120 = 0
        obj_inc = Incomes_detail.objects.filter(
                                    income__add_date__gte=period_first_day,
                                    income__add_date__lte=period_last_day,
                                    income__sale = self.pk,
                        )
        
        total_period_incomes = obj_inc.aggregate(total=Sum('capital')+Sum('interest')).get('total')
        total_arrears = obj_inc.aggregate(total=Sum('arrears')).get('total')
        if total_period_incomes == None: total_period_incomes = 0
        if total_arrears == None: total_arrears = 0
        arrears_days = 0
        for qt in obj_quotas:
            
            pay_date = qt.pay_date
            if pay_date <= period_last_day:
                pending = qt.quota_pending().get('total_pending')
                
                actual_period_incomes = Incomes_detail.objects.filter(
                                    income__add_date__gte=period_first_day,
                                    income__add_date__lte=period_last_day,
                                    quota = qt.pk,
                        ).aggregate(total=Sum('capital')+Sum('interest')).get('total')
                if actual_period_incomes == None: actual_period_incomes = 0
                
                pending += actual_period_incomes
                if pending > 0:
                    if pay_date > lt30_date:
                        lt_30 += pending
                    elif lt30_date >= pay_date > lt60_date:
                        lt_60 += pending  
                    elif lt60_date >= pay_date > lt90_date:
                        lt_90 += pending 
                    elif lt90_date >= pay_date > lt120_date:
                        lt_120 += pending
                    elif  pay_date <= lt120_date:
                        gt_120 += pending

                    if qt.arrears_info().get('days') > arrears_days:
                        arrears_days = qt.arrears_info().get('days') 
                    
        total = lt_30 + lt_60 + lt_90 + lt_120 + gt_120
        budget_pending = total - total_period_incomes
        excedent = 0
        if budget_pending < 0:
            excedent = budget_pending * -1
            budget_pending = 0
        if total == 0: total = 1  
        compliance = total_period_incomes *100 / total
        total_incomes = total_period_incomes + total_arrears + excedent
        collector = Collector_per_sale.objects.filter(sale=self.pk)
        if collector.exists(): collector_sale = collector[0].collector_user
        else: collector_sale = ""
        
            
        
        return {
            'lt_30': lt_30,
            'lt_60':lt_60,
            'lt_90':lt_90,
            'lt_120':lt_120,
            'gt_120':gt_120,
            'total':total,
            'period_income':total_period_incomes,
            'total_arrears':total_arrears,
            'arrears_days':arrears_days,
            'budget_pending':budget_pending,
            'total_incomes':total_incomes,
            'excedent':excedent,
            'compliance':compliance,
            'collector':collector_sale,
        }
            
    def is_pay_day(self):
        obj_payment_plan = Payment_plans.objects.filter(sale = self.pk)
        
        if obj_payment_plan.filter(pay_date = date.today()).exists():
            return True
        
        last_pay_date = obj_payment_plan.order_by('pay_date').last()
        if last_pay_date and last_pay_date.pay_date < date.today():
            if last_pay_date.pay_date.day == date.today().day:
                return True
        
        return False
    
    def has_pending_ci_quota(self):
        cuotas_ci = Payment_plans.objects.filter(sale=self.id_sale, quota_type='CI')
        for c in cuotas_ci:
            if c.saldo() > 0:
                return True
        return False

    
class Credit_info(Payment_plans):
    
    class Meta:
        proxy = True
    
    def is_expired(self):
        if self.pay_date <= date.today():
            return True
        return False
    
    def quota_balance(self):
        obj_income = Incomes_detail.objects.filter(quota=self.pk
            ).aggregate(
                capital=Sum('capital'),
                interest=Sum('interest'),
                others = Sum('others'),
                arrears = Sum('arrears')
            )
        
        paid_capital = obj_income.get('capital')
        if paid_capital is None: paid_capital = 0
        paid_interest = obj_income.get('interest')
        if paid_interest is None: paid_interest = 0
        paid_others = obj_income.get('others')
        if paid_others is None: paid_others = 0
        paid_arrears = obj_income.get('arrears')
        if paid_arrears is None: paid_arrears = 0
        total_paid = paid_capital + paid_interest + paid_others + paid_arrears
        
        
        data = {
            'paid_capital':paid_capital,
            'paid_interest':paid_interest,
            'paid_others':paid_others,
            'paid_arrears':paid_arrears,
            'total_paid':total_paid,
        }
        
        return data

    def quota_pending(self):
        paid = self.quota_balance()
        pending_capital = self.capital - paid.get('paid_capital')
        pending_int = self.interest - paid.get('paid_interest')
        pending_others = self.others -  paid.get('paid_others')
        total_pending = pending_capital + pending_int + pending_others
        
        data = {
            'pendient_capital':pending_capital,
            'pendient_int':pending_int,
            'pendient_others':pending_others,
            'total_pending':total_pending,
        }
        
        return data
    
    def how_paid(self):
        total_income = Incomes_detail.objects.filter(quota=self.pk
            ).aggregate(
                total=Sum('capital') + Sum('interest') + Sum('others')
            ).get('total')
        if total_income == None: total_income = 0
        
        full_pendient = False
        partial_paid = False
        full_paid = False
        
        if total_income == 0:
            full_pendient = True
        elif self.total_payment() > total_income > 0:
            partial_paid = True
        elif total_income >=  self.total_payment():
            full_paid = True
        
        data = {
            'full_pendient':full_pendient,
            'partial_paid':partial_paid,
            'full_paid':full_paid,
        }
        
        return data
    
    def arrears_info(self,paid_day=date.today()):
        rate = Parameters.objects.get(name='tasa de mora mv').value
        pending = self.quota_pending().get('total_pending',0)
        
        last_pay_date = Incomes_detail.objects.filter(
            Q(capital__gt=0)|Q(interest__gt=0),quota=self.pk
            ).aggregate(max_date=Max('income__payment_date')
                        ).get('max_date',None)
        if last_pay_date is None: last_pay_date = self.pay_date
        
        last_only_arrears_date = Incomes_detail.objects.filter(
            capital=0,interest=0,arrears__gt=0,quota=self.pk
            ).aggregate(max_date=Max('income__payment_date')
                        ).get('max_date',None)
        
        if self.pay_date >= paid_day or pending<=0:
            days = 0
            value = 0
            
        elif last_only_arrears_date and last_only_arrears_date > last_pay_date:
            total_days = (paid_day - self.pay_date).days
            days = (paid_day - last_pay_date).days
            total_arrears = pending * days *(Decimal(rate)/30)/100
            arrears_paid = self.quota_balance().get('paid_arrears',0)
            
            value = total_arrears - arrears_paid
            
        else:
            if last_pay_date < self.pay_date: last_pay_date = self.pay_date
            days = (paid_day-last_pay_date).days
            if days < 0: days = 0
            value = pending * days * (Decimal(rate)/30)/100
            
        r_value = int(value)
        
        data = {
            'days':days,
            'r_value':r_value
        }
        
        return data

class Comissions_Payment(Assigned_comission):
    
    class Meta:
        proxy = True
        
    def liquidate_advance(self):
        total_payment = Incomes.objects.filter(sale=self.sale
                            ).aggregate(total=Sum('value')
                            ).get('total',0)
        if total_payment == None: total_payment = 0
        minimal_pay = self.sale.portfolio_values().get('initial',0)
        
        obj_paid_comiss = Paid_comissions.objects.filter(assign_paid=self.pk,type_of_payment='Anticipo')
        
        value = 0
        if  minimal_pay > total_payment >= 2000000 and not obj_paid_comiss.exists():
            
            if self.state == 'Activo' and self.position.advance_bonus > 0:
                value = self.position.advance_bonus
                
        return value
    
    def liquidate_comission(self):
        total_sale_payment = Incomes.objects.filter(sale=self.sale
                            ).aggregate(total=Sum('value')
                            ).get('total',0)
    
    
        obj_paid_comiss = Paid_comissions.objects.filter(assign_paid=self.pk)
        paid_comission = obj_paid_comiss.aggregate(total=Sum('comission')
                            ).get('total',0)
        if paid_comission == None: paid_comission = 0
    
    
        if total_sale_payment == None: total_sale_payment = 0
        comission_base = self.sale.comission_base
        minimal_sale_pay = self.sale.portfolio_values().get('initial',0)

        initial_payment_rate = total_sale_payment / minimal_sale_pay        
        total_paid_decimal = Decimal(str(total_sale_payment))
        min_commission = get_min_commission_value(self.sale.project)
        meets_minimum = (min_commission <= 0) or (total_paid_decimal >= min_commission)
        method, advance_percent = get_commission_method(self.sale.project)
        effective_payment_rate = initial_payment_rate
        if method == 0 and min_commission > 0 and meets_minimum:
            effective_payment_rate = max(effective_payment_rate, 1)
        
        total_comission_value = int(comission_base * self.comission/100)
        if obj_paid_comiss.filter(type_of_payment__icontains='/3').exists():
            if 0.6 > effective_payment_rate >= 0.3:
                type_of_payment = '1/3'
                comission_generate = total_comission_value * 0.3
            elif 1 > effective_payment_rate >= 0.6:
                type_of_payment = '2/3'
                comission_generate = total_comission_value * 0.6
            else:
                type_of_payment = '3/3'
                comission_generate = total_comission_value
        elif obj_paid_comiss.filter(type_of_payment__icontains='/2').exists():
            if 1 > effective_payment_rate >= 0.5:
                type_of_payment = '1/2'
                comission_generate = total_comission_value * 0.5
            else:
                type_of_payment = '2/2'
                comission_generate = total_comission_value
        else:
            if 0.5 > effective_payment_rate >= 0.3:
                comission_generate = total_comission_value * 0.3
                type_of_payment = '1/3'
            elif 1 > effective_payment_rate >= 0.5:
                comission_generate = total_comission_value * 0.5
                type_of_payment = '1/2'
            elif effective_payment_rate >= 1:
                comission_generate = total_comission_value
                type_of_payment = '1'
            else:
                comission_generate = 0
                type_of_payment = 'Sin pago'            
                
        if self.position.name.lower() == 'tlmk':
            if 4000000 > total_sale_payment >= 2000000:
                comission_generate = total_comission_value / 2
                type_of_payment = 'Tlmk'   
            elif total_sale_payment >= 4000000:
                comission_generate = total_comission_value
                type_of_payment = 'Tlmk'   
            else:
                comission_generate = 0
        
        if method == 0:
            comission_to_pay = comission_generate - paid_comission
            if min_commission > 0 and not meets_minimum:
                comission_to_pay = 0
                type_of_payment = 'Pendiente mínimo'
        else:
            if not meets_minimum:
                comission_to_pay = 0
                type_of_payment = 'Pendiente mínimo'
            else:
                required_progress = Decimal(str(advance_percent)) / Decimal('100') or Decimal('1')
                progress_ratio = total_paid_decimal / (self.sale.value * required_progress)
                if progress_ratio > 1:
                    progress_ratio = Decimal('1')
                comission_to_pay = int(total_comission_value * progress_ratio) - paid_comission
                type_of_payment = 'Mínimo + % avance'

        #if self.state == 'Inactivo': comission_to_pay = 0
        provision = int(comission_to_pay * self.seller.retencion/100)
        net_pay = comission_to_pay - provision
        
        
        data = {
            'type': type_of_payment,
            'paid_comission':paid_comission,
            'comission_to_pay':comission_to_pay,
            'provision':provision,
            'net_pay':net_pay,
        }
        
        return data





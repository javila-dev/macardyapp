from django.contrib.auth.models import User
from django.db import models
from django.db.models.query_utils import Q
from django.db.models import Sum, F
from mcd_site.models import Projects
from terceros.models import Clients, Sellers
from decimal import Decimal

import math

# Create your models here.


class Properties(models.Model):
    id_property = models.AutoField(primary_key=True)    
    project = models.ForeignKey(
        Projects, on_delete=models.PROTECT, verbose_name='Proyecto')
    description = models.CharField(max_length=255, verbose_name='Descripcion',
        help_text='Esta descripción es la forma en que este inmueble va a aparecer en TODOS los modulos e impresiones del sistema')
    area = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='Area (en m2)')
    m2_price = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='Precio m2', default=0)
    block = models.CharField(max_length=255, verbose_name='Agrupador de lotes',
                             help_text='Esto corresponde, dependiendo del proyecto, a la manzana/vereda/bloque')
    location = models.CharField(max_length=255, verbose_name='Numero de Lote')
    stage = models.CharField(max_length=255, verbose_name='Etapa de entrega',choices=(
        ('PRIMERA','PRIMERA'),
        ('SEGUNDA','SEGUNDA'),
        ('TERCERA','TERCERA'),
        ('CUARTA','CUARTA'),
        ('QUINTA','QUINTA'),
        ('SEXTA','SEXTA'),
        ('SEPTIMA','SEPTIMA'),
        ('OCTAVA','OCTAVA'),
        ('NOVENA','NOVENA'),
        ('DECIMA','DECIMA'),
    ),null=True,blank=True)
    
    prop_registry = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='Matrícula Inmobiliaria',
        help_text='Si no tiene matricula individual, ingresar la matricula del predio de mayor extensión')
    state_choices = (
        ('Libre', 'Libre'),
        ('Bloqueado', 'Bloqueado'),
        ('Asignado', 'Asignado'),
    )
    state = models.CharField(max_length=255, choices=state_choices,
                             help_text='Para un lote nuevo siempre debe ser Libre o Bloqueado, NUNCA seleccionar Asignado en este sitio')

    def __str__(self):
        return self.description

    def property_price(self):
        price = math.ceil(self.m2_price*self.area)
        values = {
            'number': price,
            'formated': f'{price:,}'
        }
        return values
    
    def description_to_search(self):
        return self.description.replace(' ','')

    class Meta:
        verbose_name = 'Inmueble'
        verbose_name_plural = 'Inmuebles'
        unique_together = ['description', 'project']

class Sales_plans(models.Model):
    name = models.CharField(max_length=255, verbose_name='Nombre')
    initial_payment = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='Pago inicial')
    to_finance = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='A financiar')
    rate = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='tasa de interés (mv)')
    status = models.BooleanField(verbose_name='Activo', default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Plan de venta'
        verbose_name_plural = 'Planes de venta'

class Sales(models.Model):
    id_sale = models.AutoField(primary_key=True, verbose_name='Id Venta')
    project = models.ForeignKey(
        Projects, on_delete=models.PROTECT, verbose_name='Proyecto')
    contract_number = models.IntegerField(verbose_name='Numero de contrato')
    first_owner = models.ForeignKey(Clients, on_delete=models.PROTECT,
                                    related_name='first_owner', verbose_name='Primer propietario')
    second_owner = models.ForeignKey(Clients, on_delete=models.PROTECT, related_name='second_owner',
                                     null=True, blank=True, verbose_name='Segundo propietario')
    third_owner = models.ForeignKey(Clients, on_delete=models.PROTECT, related_name='third_owner',
                                    null=True, blank=True, verbose_name='Tercer propietario')
    fourth_owner = models.ForeignKey(
        Clients, on_delete=models.PROTECT, related_name='fourth_owner',
        null=True, blank=True, verbose_name='Cuarto propietario'
    )
    property_sold = models.ForeignKey(
        Properties, on_delete=models.PROTECT, verbose_name='Inmueble')
    value = models.IntegerField(verbose_name='Valor')
    comission_base = models.IntegerField(verbose_name='Comisión base')
    sale_plan = models.ForeignKey(
        Sales_plans, on_delete=models.PROTECT, verbose_name='Plan de venta')
    status = models.CharField(max_length=255, choices=(
        ('Pendiente', 'Pendiente'),
        ('Aprobado', 'Aprobado'),
        ('Adjudicado', 'Adjudicado'),
        ('Anulado', 'Anulado'),
        ('Desistido', 'Desistido')
    ), verbose_name='Estado')
    observations = models.CharField(max_length=255, null=True, blank=True)
    club = models.BooleanField(default=False, verbose_name = "Club Mediterraneo")
    add_date = models.DateField(auto_now_add=True)
    scheduled_delivery_date = models.DateField(null=True, blank=True, verbose_name="Fecha programada de entrega")
    actual_delivery_date = models.DateField(null=True, blank=True, verbose_name="Fecha real de entrega")
    delivery_observations = models.TextField(blank=True, verbose_name="Observaciones de entrega")
    scheduled_deed_date = models.DateField(null=True, blank=True, verbose_name="Fecha programada de escrituración")
    actual_deed_date = models.DateField(null=True, blank=True, verbose_name="Fecha real de escrituración")
    notary = models.CharField(max_length=200, blank=True, verbose_name="Notaría")
    deed_number = models.CharField(max_length=100, blank=True, verbose_name="Número de escritura")
    deed_observations = models.TextField(blank=True, verbose_name="Observaciones de escrituración")
    tasa = models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Tasa de interés', default=Decimal('0.00'))

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        unique_together = ['project', 'contract_number']

    def __str__(self):
        return 'CTR' + str(self.contract_number) + ' - '+self.first_owner.full_name()

    def portfolio_values(self):
        payment_plan = Payment_plans.objects.filter(
            sale=self.pk
        )
        initial = payment_plan.filter(quota_type='CI')
        total_initial = initial.aggregate(Sum('capital')).get('capital__sum')
        if total_initial == None:
            total_initial = 0
        to_finance = self.value - total_initial

        data = {
            'initial': total_initial,
            'to_finance': to_finance,
        }

        return data

class Payment_plans(models.Model):
    id_payment = models.AutoField(primary_key=True)
    id_quota = models.CharField(max_length=255, verbose_name='id Cuota')
    quota_type = models.CharField(max_length=5, verbose_name='Tipo de cuota')
    sale = models.ForeignKey(
        Sales, on_delete=models.CASCADE, verbose_name='Número de contrato')
    pay_date = models.DateField(verbose_name='Fecha de pago')
    capital = models.DecimalField(decimal_places=2, max_digits=20)
    interest = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='Interés corriente')
    others = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='Otros')
    project = models.ForeignKey(
        Projects, on_delete=models.PROTECT, verbose_name='Proyecto')

    def __str__(self):
        return self.id_quota

    def capital_paid(self):
        from finance.models import Incomes_detail  # import interno para evitar circularidad
        return Incomes_detail.objects.filter(quota=self).aggregate(
            total=Sum(F('capital'))
        )['total'] or 0
        
    def interest_paid(self):
        from finance.models import Incomes_detail  # import interno para evitar circularidad
        return Incomes_detail.objects.filter(quota=self).aggregate(
            total=Sum(F('interest'))
        )['total'] or 0
    
    def others_paid(self):
        from finance.models import Incomes_detail  # import interno para evitar circularidad
        return Incomes_detail.objects.filter(quota=self).aggregate(             
            total=Sum(F('others'))
        )['total'] or 0
        
    def paid(self):
        from finance.models import Incomes_detail  # import interno para evitar circularidad
        return Incomes_detail.objects.filter(quota=self).aggregate(
            total=Sum(F('capital') + F('interest') + F('others'))
        )['total'] or 0

    def total_payment(self):
        total = self.capital + self.interest + self.others
        return total
    
    def saldo(self):
        return self.total_payment() - self.paid()

    class Meta:
        verbose_name = 'Plan de pago'
        verbose_name_plural = 'Planes de pago'
        unique_together = ['id_quota', 'project']

class PaymentPlanRestructuring(models.Model):
    STATUS_CHOICES = (
        ('Pendiente', 'Pendiente'),
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
    )

    id_restructuring = models.AutoField(primary_key=True)
    sale = models.ForeignKey(
        Sales, on_delete=models.CASCADE, related_name='restructurings', verbose_name='Venta'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Solicitado por'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de solicitud')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pendiente')
    observations = models.TextField(null=True, blank=True, verbose_name='Observaciones')
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='restructurings_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    tasa = models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Tasa de interés', default=Decimal('0.00'))
    nuevo_valor_venta = models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Nuevo valor de venta', null=True, blank=True)
    

    class Meta:
        verbose_name = 'Reestructuración de plan de pagos'
        verbose_name_plural = 'Reestructuraciones de planes de pago'
        ordering = ['-created_at']

    def __str__(self):
        return f'Reestructuración {self.id_restructuring} - {self.sale} ({self.status})'

class IncomeDetailsBackup(models.Model):
    """
    Modelo para almacenar backups de los detalles de ingresos cuando se desvinculan
    los recaudos de una venta. Permite revertir el proceso si es necesario.
    """
    sale = models.ForeignKey(
        'Sales', 
        on_delete=models.CASCADE, 
        verbose_name="Venta",
        related_name="income_details_backups"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Usuario",
        related_name="income_details_backups"
    )
    details = models.TextField(
        verbose_name="Detalles de aplicaciones", 
        help_text="Almacena en formato JSON los detalles de aplicaciones antes de desvincular"
    )
    motivo = models.TextField(
        verbose_name="Motivo de desvinculación", 
        help_text="Razón por la que se realizó la desvinculación de recaudos"
    )
    backup_date = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha del backup"
    )
    is_applied = models.BooleanField(
        default=False, 
        verbose_name="¿Fue aplicado nuevamente?",
        help_text="Indica si este backup ya fue usado para restaurar aplicaciones"
    )

    class Meta:
        verbose_name = "Backup de aplicaciones de recaudos"
        verbose_name_plural = "Backups de aplicaciones de recaudos"
        ordering = ['-backup_date']

    def __str__(self):
        return f"Backup {self.id} - Venta {self.sale.contract_number} ({self.backup_date.strftime('%d/%m/%Y %H:%M')})"
    
    def get_details_json(self):
        """Devuelve los detalles como objeto Python desde el JSON almacenado"""
        if self.details:
            return json.loads(self.details)
        return []

class PaymentPlanRestructuringDetail(models.Model):
    restructuring = models.ForeignKey(
        PaymentPlanRestructuring, on_delete=models.CASCADE, related_name='details'
    )
    id_quota = models.CharField(max_length=255, verbose_name='id Cuota')
    quota_type = models.CharField(max_length=5, verbose_name='Tipo de cuota')
    pay_date = models.DateField(verbose_name='Fecha de pago')
    capital = models.DecimalField(decimal_places=2, max_digits=20)
    interest = models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Interés corriente')
    others = models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Otros')
    tipo = models.CharField(
        max_length=20,
        choices=(
            ('pagada', 'Pagada'),
            ('split', 'Split'),
            ('nueva', 'Nueva'),
            ('pendiente', 'Pendiente'),
        ),
        default='pendiente',
        verbose_name='Tipo de modificación'
    )

    class Meta:
        verbose_name = 'Detalle de reestructuración'
        verbose_name_plural = 'Detalles de reestructuración'

    def __str__(self):
        return f'{self.id_quota} ({self.pay_date}) - {self.get_tipo_display()}'

    def total(self):
        return self.capital + self.interest + self.others
    
class Sales_history(models.Model):
    sale = models.ForeignKey(Sales, on_delete=models.CASCADE,
                             related_name="sale_id_history", verbose_name='Número de contrato')
    action = models.CharField(max_length=255)
    add_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Usuario')

    class Meta:
        verbose_name = 'Historial de venta'
        verbose_name_plural = 'Historial de ventas'

class Comission_position(models.Model):
    id_charge = models.AutoField(primary_key=True, verbose_name='Id cargo')
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='comission_positions', verbose_name='Proyecto')
    name = models.CharField(max_length=255, verbose_name='Nombre')
    rate = models.DecimalField(
        decimal_places=2, max_digits=10, verbose_name='Porcentaje')
    group = models.CharField(max_length=255, choices=(
        ('Publico', 'Publico'),
        ('Privado', 'Privado'),
    ), verbose_name='Grupo',
        help_text='Dependiendo del grupo escogido, el cargo se mostrará en la vista de asignaciones o no')
    default = models.ForeignKey(Sellers,on_delete=models.PROTECT,
        verbose_name='Asesor por defecto',null=True,blank=True)
    advance_bonus = models.IntegerField(default = 0,
                                        verbose_name='Monto para anticipossales')
    include_default = models.BooleanField(default=True, verbose_name='Incluir en escala automaticamente')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Cargo de comision'
        verbose_name_plural = 'Cargos de comisiones'
        unique_together = ['project', 'name']

    def __str__(self):
        scope = self.project.name_to_show if self.project else 'Global'
        return f'{self.id_charge}-{self.name} ({scope})'

class Assigned_comission(models.Model):
    id_asigned = models.AutoField(primary_key=True)
    id_comission = models.CharField(max_length=255)
    project = models.ForeignKey(Projects, on_delete=models.PROTECT, related_name='project_asigned_comiss',
                                verbose_name='Proyecto')
    sale = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='asigned_comiss_sale',
                             verbose_name='Venta')
    position = models.ForeignKey(Comission_position, on_delete=models.PROTECT, related_name='position_asigned_comission',
                                 verbose_name='Comisiones asignadas')
    seller = models.ForeignKey(Sellers, on_delete=models.PROTECT, related_name='seller_asigned',
                               verbose_name='Vendedor')
    comission = models.DecimalField(
        decimal_places=2, max_digits=10, verbose_name='Comision')
    state = models.CharField(max_length=255,choices=(
        ('Activo','Activo'),
        ('Inactivo','Inactivo')
    ),verbose_name= 'Estado',default='Activo')

    class Meta:
        verbose_name = 'Comision asignada'
        verbose_name_plural = 'Comisiones asignadas'
        #unique_together = ['id_comission','project']

    def __str__(self):
        return self.id_comission + ' ' + self.project.name_to_show
    
    def comission_total_value(self):
        total = (self.comission/100) * self.sale.comission_base
        return f'{total:,.0f}'

class Paid_comissions(models.Model):
    project = models.ForeignKey(Projects, on_delete=models.PROTECT, related_name='paid_comission_project',
                                verbose_name='Comisiones pagadas')
    assign_paid = models.ForeignKey(Assigned_comission, on_delete=models.PROTECT,
                                    related_name='assign_paid_comission',
                                    verbose_name='Comision asignada')
    pay_date = models.DateField(verbose_name='Fecha de pago')
    comission = models.FloatField(verbose_name='Comision')
    provision = models.FloatField(verbose_name='Provision')
    net_payment = models.FloatField(verbose_name='Pago Neto')
    type_of_payment = models.CharField(max_length=255, choices=(
        ('Anticipo', 'Anticipo'),
        ('30-30-40', '30-30-40'),
        ('50-50', '50-50'),
    ))
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='paid_comission_user',
                             verbose_name='Usuario')

    class Meta:
        verbose_name = 'Comision pagada'
        verbose_name_plural = 'Comisiones pagadas'

    def __str__(self):
        return f'{self.assign_paid.id_comission} el {self.pay_date}'

class backup_payment_plans(models.Model):
    backup_date = models.DateTimeField(verbose_name= 'Fecha de creación')
    id_payment = models.IntegerField(verbose_name='id pago')
    id_quota = models.CharField(max_length=255, verbose_name='id Cuota')
    quota_type = models.CharField(max_length=5, verbose_name='Tipo de cuota')
    sale = models.ForeignKey(
        Sales, on_delete=models.CASCADE, verbose_name='Número de contrato')
    pay_date = models.DateField(verbose_name='Fecha de pago')
    capital = models.DecimalField(decimal_places=2, max_digits=20)
    interest = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='Interés corriente')
    others = models.DecimalField(
        decimal_places=2, max_digits=20, verbose_name='Otros')
    project = models.ForeignKey(
        Projects, on_delete=models.PROTECT, verbose_name='Proyecto')

    def __str__(self):
        return self.id_quota

    def total_payment(self):
        total = self.capital + self.interest + self.others
        return total

    class Meta:
        verbose_name = 'Plan de pago'
        verbose_name_plural = 'Planes de pago'
        unique_together = ['id_quota', 'project','backup_date']

class SalesFiles(models.Model):
    id_file = models.AutoField(primary_key=True, verbose_name='ID Archivo')
    sale = models.ForeignKey(
        Sales, on_delete=models.CASCADE, related_name='files', verbose_name='Venta'
    )
    description = models.CharField(
        max_length=255, verbose_name='Descripción del archivo',
        help_text='Breve descripción del archivo cargado'
    )
    file = models.FileField(
        upload_to='sales/files/', verbose_name='Archivo',
        help_text='Archivo asociado a la venta'
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Cargado por',
        help_text='Usuario que cargó el archivo'
    )
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de carga')
    file_type = models.CharField(
        max_length=50, verbose_name='Tipo de archivo', null=True, blank=True,
        help_text='Tipo de archivo (ejemplo: contrato, factura, etc.)'
    )
    is_active = models.BooleanField(
        default=True, verbose_name='Activo',
        help_text='Indica si el archivo está activo o ha sido eliminado'
    )
    observations = models.TextField(
        null=True, blank=True, verbose_name='Observaciones',
        help_text='Comentarios adicionales sobre el archivo'
    )

    class Meta:
        verbose_name = 'Archivo de venta'
        verbose_name_plural = 'Archivos de ventas'
        ordering = ['-upload_date']

    def __str__(self):
        return f'{self.description} - {self.sale}'

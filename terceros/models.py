from datetime import datetime, date
from tabnanny import verbose
from django.db import models
from django.db.models.query_utils import Q
from mcd_site.models import Bank_entities, Projects



# Create your models here.
class Sellers_groups(models.Model):
    name = models.CharField(max_length=255, verbose_name='Nombre')
    project = models.ForeignKey(
        Projects, on_delete=models.PROTECT, verbose_name='Proyecto')
    status = models.BooleanField(verbose_name='Estado', default=True)

    class Meta:
        verbose_name = 'Grupo de venta'
        verbose_name_plural = 'Grupos de venta'
        unique_together = ['name', 'project']

    def __str__(self):
        return self.project.name_to_show+' | '+self.name


class Sellers(models.Model):
    seller_document = models.CharField(
        max_length=255, primary_key=True, verbose_name='Documento vendedor')
    first_name = models.CharField(max_length=255, verbose_name='Nombres')
    last_name = models.CharField(max_length=255, verbose_name='Apellidos')
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True,
                             blank=True, verbose_name='Celular')
    address = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='Dirección de residencia')
    city = models.IntegerField(
        null=True, blank=True, verbose_name='Ciudad de residencia')
    state = models.IntegerField(
        null=True, blank=True, verbose_name='Departamento')
    country = models.IntegerField(null=True, blank=True, verbose_name='País')
    cv = models.FileField(null=True, blank=True,
                          upload_to='Sellers', verbose_name='Hoja de vida')
    rut_support = models.FileField(
        null=True, blank=True, upload_to='Sellers', verbose_name='RUT')
    bank_certificate = models.FileField(
        null=True, blank=True, upload_to='Sellers', verbose_name='Certificado bancario')
    account_type = models.CharField(max_length=255, choices=(
        ('S', 'Ahorros'), ('D', 'Corriente')
    ), verbose_name='Tipo de cuenta')
    bank_entity = models.ForeignKey(
        Bank_entities, on_delete=models.PROTECT, verbose_name='Entidad Bancaria')
    bank_account_number = models.CharField(
        max_length=255, null=True, blank=True)
    seller_type = models.CharField(max_length=255, choices=(
        ('I', 'Interno'), ('E', 'Externo')
    ), verbose_name='Tipo de vendedor')
    seller_state_choices = (
        ('Activo', 'Activo'), ('Retirado', 'Retirado'), ('Inactivo', 'Inactivo')
    )
    seller_state = models.CharField(
        max_length=255, choices=seller_state_choices, default='Inactivo', verbose_name='Estado')
    retencion = models.FloatField(default=10)
    projects = models.ManyToManyField(Projects, verbose_name='Proyectos')
    birth_date = models.DateField(
        null=True, blank=True, verbose_name='Fecha de nacimiento')
    marital_status = models.CharField(max_length=255, null=True, blank=True, choices=(
        ('Soltero(a)', 'Soltero(a)'),
        ('Casado(a)', 'Casado(a)'),
        ('Union Libre', 'Union Libre')
    ), verbose_name='Estado Civil')
    pay_pmt = models.BooleanField(verbose_name='Se paga PMT')
    add_date = models.DateField(auto_now_add=True)
    sales_group = models.ForeignKey(Sellers_groups, on_delete=models.PROTECT, verbose_name='Grupo de ventas',
                                    null=True, blank=True)

    class Meta:
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def active_days(self):
        return (datetime.today().date() - self.add_date).days

    def __str__(self):
        return self.full_name()


class Clients(models.Model):
    IDENTIFICATION_TYPES = (
        ('CC', 'Cédula de Ciudadanía'),
        ('TI', 'Tarjeta de Identidad'),
        ('RC', 'Registro Civil de nacimiento'),
        ('CE', 'Cédula de Extranjería'),
        ('P', 'Pasaporte'),
    )

    client_document = models.CharField(
        max_length=255, primary_key=True, verbose_name='Documento cliente')
    identification_type = models.CharField(
        max_length=2, choices=IDENTIFICATION_TYPES, default='CC', verbose_name='Tipo de Identificación'
    )
    first_name = models.CharField(max_length=255, verbose_name='Nombre')
    last_name = models.CharField(max_length=255, verbose_name='Apellidos')
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True,
                             blank=True, verbose_name='Celular')
    address = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='Dirección')
    
    # ✅ NUEVOS CAMPOS AGREGADOS
    neighborhood = models.CharField(max_length=255, verbose_name='Barrio', blank=True)
    birth_place = models.CharField(max_length=255, verbose_name='Lugar de nacimiento', blank=True)
    lives_in_own_house = models.BooleanField(verbose_name='Vive en casa propia', default=False)
    
    marital_status = models.CharField(max_length=255, null=True, blank=True, choices=(
        ('Soltero(a)', 'Soltero(a)'),
        ('Casado(a)', 'Casado(a)'),
        ('Union Libre', 'Union Libre')
    ), verbose_name='Estado Civil')
    birth_date = models.DateField(
        null=True, blank=True, verbose_name='Fecha de nacimiento')
    
    # IDs de ubicación (mantener para compatibilidad)
    city = models.IntegerField(
        null=True, blank=True, verbose_name='Ciudad de Residencia')
    state = models.IntegerField(
        null=True, blank=True, verbose_name='Departamento')
    country = models.IntegerField(null=True, blank=True, verbose_name='País')
    
    # ✅ NOMBRES DE UBICACIÓN EN TEXTO
    city_name = models.CharField(max_length=255, verbose_name='Ciudad (texto)', blank=True)
    state_name = models.CharField(max_length=255, verbose_name='Departamento (texto)', blank=True)
    country_name = models.CharField(max_length=255, verbose_name='País (texto)', blank=True)
    
    office = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='Direccion oficina')
    phone_office = models.CharField(
        max_length=50, null=True, blank=True, verbose_name='Telefono de Oficina')
    house_phone = models.CharField(
        max_length=50, null=True, blank=True, verbose_name='Telefono de Residencia')
    
    add_date = models.DateTimeField(auto_now_add=True)
    seller = models.ForeignKey(Sellers, on_delete=models.PROTECT, related_name='seller_client',
                               verbose_name='Captado por', null=True, blank=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    # ✅ MÉTODO CALCULADO PARA EDAD
    @property
    def age(self):
        """Calcula la edad basada en la fecha de nacimiento"""
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None

    # ✅ MÉTODO PARA UBICACIÓN COMPLETA
    @property
    def full_location(self):
        """Retorna ubicación completa en formato texto"""
        parts = [self.city_name, self.state_name, self.country_name]
        return ', '.join([part for part in parts if part])

    def __str__(self):
        return self.full_name()
    
    @property
    def full_birth_info(self):
        """Retorna información completa de nacimiento en formato texto"""
        if self.birth_date and self.birth_place:
            return f'{self.birth_place}, {self.birth_date|date:"d/m/Y"}'
        return '________________________'


class Collaborators(models.Model):
    id_document = models.CharField(max_length=255, verbose_name='Cedula', unique=True)
    first_name = models.CharField(max_length=255, verbose_name='Nombres')
    last_name = models.CharField(max_length=255, verbose_name='Apellidos')
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True,
                             blank=True, verbose_name='Celular')
    address = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='Dirección de residencia')
    city = models.IntegerField(
        null=True, blank=True, verbose_name='Ciudad de residencia')
    state = models.IntegerField(
        null=True, blank=True, verbose_name='Departamento')
    country = models.IntegerField(null=True, blank=True, verbose_name='País')
    cv = models.FileField(null=True, blank=True,
                          upload_to='Collaborators', verbose_name='Hoja de vida')
    contract_support = models.FileField(
        null=True, blank=True, upload_to='Collaborators', verbose_name='Contrato')
    bank_certificate = models.FileField(
        null=True, blank=True, upload_to='Collaborators', verbose_name='Certificado bancario')
    account_type = models.CharField(max_length=255, choices=(
        ('S', 'Ahorros'), ('D', 'Corriente')
    ), verbose_name='Tipo de cuenta')
    bank_entity = models.ForeignKey(Bank_entities, on_delete=models.PROTECT,
                                    verbose_name='Entidad Bancaria')
    bank_account_number = models.CharField(
        max_length=255, null=True, blank=True)
    seller_state_choices = (
        ('Activo', 'Activo'), ('Retirado', 'Retirado')
    )
    status = models.CharField(
        max_length=255, choices=seller_state_choices, default='Activo', verbose_name='Estado')
    birth_date = models.DateField(
        null=True, blank=True, verbose_name='Fecha de nacimiento')
    scholarity = models.CharField(max_length=255, choices=(
        ('Bachillerato', 'Bachillerato'),  ('Tecnico', 'Tecnico'),
        ('Tecnologo', 'Tecnologo'), ('Pregrado', 'Pregrado'),
        ('Postgrado', 'Postgrado'), ('Maestria', 'Maestria')
    ), verbose_name='Escolaridad')
    eps = models.IntegerField()
    pension = models.IntegerField()
    cesantias = models.IntegerField()

    class Meta:
        verbose_name = 'Colaborador'
        verbose_name_plural = 'Colaboradores'

    def __str__(self):
        return self.full_name()

    def full_name(self):
        return self.first_name + ' ' + self.last_name

    def last_contract(self):
        obj_contracts = Collaborator_contracts.objects.filter(
            collaborator=self.pk)
        values = None
        if obj_contracts.exists():
            values =  dict(obj_contracts.values().last())
        return values
    
    def all_contracts(self):
        obj_contracts = Collaborator_contracts.objects.filter(
            collaborator=self.pk).reverse()
        return list(obj_contracts.values())


class Collaborator_contracts(models.Model):
    collaborator = models.ForeignKey(Collaborators, on_delete=models.CASCADE,
                                     verbose_name='Colaborador')
    type_of_contract = models.CharField(max_length=255, choices=(
        ('Fijo', 'Fijo'),
        ('Obra labor', 'Obra labor'),
        ('Indefinido', 'Indefinido'),
        ('Prestación de servicios', 'Prestación de servicios'),
    ), verbose_name='Tipo de contrado')
    duration = models.PositiveIntegerField(
        verbose_name='Duración', null=True, blank=True)
    initial_date = models.DateField(verbose_name='Fecha de inicio')
    end_date = models.DateField(
        verbose_name='Fecha de finalización', null=True, blank=True)
    position_name = models.CharField(max_length=255, verbose_name='Cargo')
    salary = models.IntegerField(verbose_name='Salario')
    comments = models.CharField(max_length=255,verbose_name='Observaciones',null=True,blank=True)
    

    class Meta:
        verbose_name = 'Contrato colaborador'
        verbose_name_plural = 'Contratos colaboradores'

    def __str__(self):
        return self.collaborator.full_name() + ' - ' + self.type_of_contract


class collaborators_files(models.Model):
    collaborator = models.ForeignKey(Collaborators, on_delete=models.CASCADE)
    description = models.CharField(max_length=255,verbose_name='Descripcion')
    load_date = models.DateField(auto_now_add=True,verbose_name='Fecha de registro')
    file = models.FileField(verbose_name='Archivo',upload_to='Collaborators')

    class Meta:
        verbose_name = 'Archivo colaborador'
        verbose_name_plural = 'Archivos colaboradores'
        unique_together = ['collaborator','description']
    
    def __str__(self):  
        return self.collaborator.full_name + ' | ' + self.description

class Client_reference(models.Model):
    REFERENCE_TYPES = (
        ('familiar', 'Familiar'),
        ('personal', 'Personal'),
    )
    
    client = models.ForeignKey(Clients, on_delete=models.CASCADE, related_name='references')
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPES)
    name = models.CharField(max_length=255, verbose_name='Nombre')
    occupation = models.CharField(max_length=255, verbose_name='Ocupación', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Teléfono', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Referencia de Cliente'
        verbose_name_plural = 'Referencias de Clientes'
    
    def __str__(self):
        return f"{self.name} - {self.get_reference_type_display()}"

class Client_employment_info(models.Model):
    client = models.OneToOneField(Clients, on_delete=models.CASCADE, related_name='employment_info')
    company_name = models.CharField(max_length=255, verbose_name='Empresa donde labora', blank=True)
    position = models.CharField(max_length=255, verbose_name='Cargo', blank=True)
    profession = models.CharField(max_length=255, verbose_name='Profesión', blank=True)
    occupation = models.CharField(max_length=255, verbose_name='Ocupación', blank=True)
    monthly_salary = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Salario/Ingresos Mensuales', null=True, blank=True)
    years_experience = models.PositiveIntegerField(verbose_name='Antigüedad (años)', null=True, blank=True)
    company_city = models.CharField(max_length=255, verbose_name='Ciudad', blank=True)
    company_address = models.CharField(max_length=500, verbose_name='Dirección', blank=True)
    company_phone = models.CharField(max_length=20, verbose_name='Teléfono empresa', blank=True)
    social_organizations = models.TextField(verbose_name='Entidades sociales, Deportivas, Culturales o Agremiaciones', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Información Laboral de Cliente'
        verbose_name_plural = 'Información Laboral de Clientes'
    
    def __str__(self):
        return f"Info laboral - {self.client.full_name()}"
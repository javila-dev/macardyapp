from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import unicodedata

# Create your models here.

class Projects(models.Model):
    name = models.CharField(max_length=255,primary_key=True, verbose_name='Nombre del proyecto')
    name_to_show = models.CharField(max_length=255,verbose_name='Nombre para mostrar')
    formats_path = models.CharField(max_length=255,verbose_name='Directorio de formatos')
    logo = models.ImageField(upload_to='project_logos',verbose_name='Logo proyecto')
    logo_empresa = models.ImageField(upload_to='project_logos',verbose_name='Logo empresa',
                                   null=True, blank=True)
    text_ds = models.CharField(max_length=255,verbose_name='Texto resolucion documento soporte DIAN', 
                               null=True, blank=True)
    default_admin_collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='default_admin_projects'
    )
    
    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
    
    def __str__(self):
        return self.name_to_show

class Permiso(models.Model):
    descripcion = models.CharField(unique=True,max_length=255)

    class Meta:
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'

    def __str__(self):
        return self.descripcion.capitalize()

class Rol(models.Model):
    descripcion = models.CharField(unique=True,max_length=255)
    permisos = models.ManyToManyField(Permiso)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.descripcion.capitalize()

class Perfil(models.Model):
    usuario = models.OneToOneField(User,on_delete=models.CASCADE,related_name='user_profile')
    identificacion = models.CharField(max_length=255,blank=True,null=True)
    fecha_nacimiento = models.DateField(null=True,blank=True)
    avatar = models.ImageField(upload_to='users',null=True,blank=True,verbose_name='Foto')
    rol = models.ManyToManyField(Rol,blank=True)
    permiso = models.ManyToManyField(Permiso,blank=True,)
    projects = models.ManyToManyField(Projects,verbose_name='Proyectos')
    force_change_pswd = models.BooleanField(default=1,verbose_name='Forzar cambio de contraseña',
        help_text='Selecciona esta opcion para que el usuario deba cambiar su contraseña en el proximo inicio de sesión') 
    
    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuarios'
        
    def __str__(self):
        return self.usuario.get_full_name()
    
    def all_permissions(self):
        owned_permissions = []
        roles = self.rol.all()
        for rol in roles:
            permisos = rol.permisos.all()
            for permiso in permisos:
                owned_permissions.append(permiso.descripcion.lower())
        permisos_individuales = self.permiso.all()
        for permiso in permisos_individuales:
            owned_permissions.append(permiso.descripcion.lower())
        if owned_permissions is not list:
            permissions_list = (owned_permissions,)
        else: permissions_list = owned_permissions
        return owned_permissions
    
    def all_rols(self):
        rols = self.rol.all()
        rol_list = []
        for rol in rols:
            rol_list.append(rol.descripcion.lower())
        return rol_list

    def has_permission(self, perm):
        if self.usuario.is_superuser:
            return True
        perms = [_norm(p) for p in self.all_permissions()]
        return _norm(perm) in perms

    def has_permissions(self, perms):
        if self.usuario.is_superuser:
            return True
        user_perms = [_norm(p) for p in self.all_permissions()]
        return all(_norm(p) in user_perms for p in perms)

    def has_rols(self, rols):
        if self.usuario.is_superuser:
            return True
        roles = [_norm(r) for r in self.all_rols()]
        needed = [_norm(r) for r in rols]
        return all(n in roles for n in needed)

    def has_project(self,project):
        if self.usuario.is_superuser:
            return True
        project_user = self.projects.all()
        
        for proj in project_user:
            if proj.name == project:
                return True
        
        return False
        

class Bank_entities(models.Model):
    id_bank = models.CharField(max_length=255)
    name = models.CharField(max_length=255, unique=True)
    
    class Meta:
        verbose_name = 'Banco'
        verbose_name_plural = 'Bancos'
        
    def __str__(self):
        return self.name


class Parameters(models.Model):
    name = models.CharField(max_length=255)
    project = models.ForeignKey(Projects,on_delete=models.PROTECT,
                                 null=True,blank=True)
    section = models.CharField(max_length=255)
    state = models.BooleanField()
    value = models.FloatField(null=True,blank=True)
    json = models.JSONField(null=True, blank=True)  # <-- Nuevo campo

    class Meta:
        verbose_name ='Parametro'
        verbose_name_plural = 'Parametros'
        unique_together = ['name','project']

class Counters(models.Model):
    name = models.CharField(max_length=255,verbose_name='Nombre')
    prefix = models.CharField(max_length=255,verbose_name='Prefijo')
    value = models.IntegerField(verbose_name='Consecutivo')
    project = models.ForeignKey(Projects,on_delete=models.PROTECT)
    
    class Meta:
        verbose_name ='Consecutivo'
        verbose_name_plural = 'Consecutivos'
        unique_together = ['name','project']

class Timeline(models.Model):
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name='user_timeline',verbose_name='Usuario')
    date = models.DateTimeField(auto_now_add=True,verbose_name='Fecha y hora')
    action = models.CharField(max_length=255,verbose_name='Accion')
    project = models.ForeignKey(Projects,on_delete=models.PROTECT,verbose_name='Proyecto',
                                related_name='project_timeline',null=True,blank=True)
    aplication = models.CharField(max_length=255,verbose_name='Aplicación')
    
    class Meta:
        verbose_name = 'Accion'
        verbose_name = 'Historial de acciones'
        
    def __str__(self):
        return self.user.username + '-' +str(self.date)
    
class Notifications_email(models.Model):
    name = models.CharField(unique=True,verbose_name='Descripción',max_length=255)
    users_to_send = models.ManyToManyField(User,verbose_name='Usuarios a enviar')
    
    class Meta:
        verbose_name = 'Notificacion por email'
        verbose_name = 'Notificaciones por email'
    
    def __str__(self) -> str:
        return self.name

def _norm(txt):
    return unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode('ascii').lower().strip()
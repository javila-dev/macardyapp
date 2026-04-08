from django.contrib import admin
from mcd_site import models

# Register your models here.

@admin.register(models.Perfil)
class profilesAdmin(admin.ModelAdmin):
    list_display = ['usuario','identificacion','fecha_nacimiento','avatar']
    filter_horizontal = ['rol','permiso']

@admin.register(models.Permiso)
class PermissionsAdmin(admin.ModelAdmin):
    list_display = ['pk','descripcion']
    
@admin.register(models.Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['pk','descripcion']
    filter_horizontal = ['permisos']

@admin.register(models.Projects)
class projectsAdmin(admin.ModelAdmin):
    list_display = ['name',]
    
@admin.register(models.Notifications_email)
class Notifications_emailAdmin(admin.ModelAdmin):
    list_display = ['name',]
    
@admin.register(models.Counters)
class CountersAdmin(admin.ModelAdmin):
    list_display = ['name','project','value']
    list_filter = ['project']
    
@admin.register(models.Parameters)
class ParametersAdmin(admin.ModelAdmin):
    list_display = ['name','project','state','value']
    list_filter = ['project']
    

admin.site.site_header ='Administración de MacardyApp'
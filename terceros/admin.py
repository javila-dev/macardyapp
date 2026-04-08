from django.contrib import admin
from terceros import models

# Register your models here.
@admin.register(models.Clients)
class clientsAdmin(admin.ModelAdmin):
    list_display = ['client_document','first_name','last_name','email']
    list_filter = ['marital_status']
    search_fields = ['client_document','first_name','last_name']

@admin.register(models.Sellers)
class sellersAdmin(admin.ModelAdmin):
    list_display = ['seller_document', 'first_name', 'last_name', 'email', 'phone']

@admin.register(models.Collaborators)
class collabAdmin(admin.ModelAdmin):
    list_display = ['id_document', 'first_name', 'last_name', 'email', 'phone']
    list_filter = ['status']
    search_fields = ['id_document','first_name','last_name']

@admin.register(models.Sellers_groups)
class sellers_groupsAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'status']
    list_filter = ['status']


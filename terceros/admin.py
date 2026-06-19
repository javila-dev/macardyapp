from django.contrib import admin
from terceros import models


class ClientReferenceInline(admin.TabularInline):
    model = models.Client_reference
    extra = 0


class ClientEmploymentInfoInline(admin.StackedInline):
    model = models.Client_employment_info
    extra = 0
    max_num = 1
    can_delete = False


class CollaboratorContractInline(admin.TabularInline):
    model = models.Collaborator_contracts
    extra = 0


class CollaboratorFileInline(admin.TabularInline):
    model = models.collaborators_files
    extra = 0


@admin.register(models.Clients)
class clientsAdmin(admin.ModelAdmin):
    list_display = ['client_document', 'first_name', 'last_name', 'email', 'phone']
    list_filter = ['marital_status', 'identification_type']
    search_fields = ['client_document', 'first_name', 'last_name', 'email']
    inlines = [ClientReferenceInline, ClientEmploymentInfoInline]


@admin.register(models.Sellers)
class sellersAdmin(admin.ModelAdmin):
    list_display = [
        'seller_document', 'first_name', 'last_name', 'email', 'phone', 'seller_state',
    ]
    list_filter = ['seller_state', 'seller_type', 'pay_pmt']
    search_fields = ['seller_document', 'first_name', 'last_name', 'email']
    filter_horizontal = ['projects']


@admin.register(models.Collaborators)
class collabAdmin(admin.ModelAdmin):
    list_display = ['id_document', 'first_name', 'last_name', 'email', 'phone', 'status']
    list_filter = ['status', 'scholarity', 'account_type']
    search_fields = ['id_document', 'first_name', 'last_name', 'email']
    inlines = [CollaboratorContractInline, CollaboratorFileInline]


@admin.register(models.Sellers_groups)
class sellers_groupsAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'status']
    list_filter = ['status', 'project']
    search_fields = ['name', 'project__name', 'project__name_to_show']


@admin.register(models.Collaborator_contracts)
class collaboratorContractsAdmin(admin.ModelAdmin):
    list_display = [
        'collaborator', 'type_of_contract', 'position_name', 'initial_date',
        'end_date', 'salary',
    ]
    list_filter = ['type_of_contract', 'initial_date', 'end_date']
    search_fields = [
        'collaborator__id_document', 'collaborator__first_name',
        'collaborator__last_name', 'position_name',
    ]
    autocomplete_fields = ['collaborator']


@admin.register(models.collaborators_files)
class collaboratorFilesAdmin(admin.ModelAdmin):
    list_display = ['collaborator', 'description', 'load_date']
    list_filter = ['load_date', 'description']
    search_fields = [
        'collaborator__id_document', 'collaborator__first_name',
        'collaborator__last_name', 'description',
    ]
    autocomplete_fields = ['collaborator']


@admin.register(models.Client_reference)
class clientReferenceAdmin(admin.ModelAdmin):
    list_display = ['client', 'reference_type', 'name', 'occupation', 'phone']
    list_filter = ['reference_type']
    search_fields = [
        'client__client_document', 'client__first_name', 'client__last_name',
        'name', 'phone',
    ]
    autocomplete_fields = ['client']


@admin.register(models.Client_employment_info)
class clientEmploymentInfoAdmin(admin.ModelAdmin):
    list_display = [
        'client', 'company_name', 'position', 'profession', 'monthly_salary',
    ]
    search_fields = [
        'client__client_document', 'client__first_name', 'client__last_name',
        'company_name', 'position', 'profession',
    ]
    autocomplete_fields = ['client']

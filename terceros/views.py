import math
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path
from django.contrib import messages
from django.db import IntegrityError
from django.db.models.query_utils import Q
from django.db.models import Min
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.conf import settings
from django.core.exceptions import PermissionDenied
from mcd_site.utils import JsonRender
from sales.models import Assigned_comission, Sales
from terceros import forms
from terceros.models import (
    Clients, Collaborator_contracts, Collaborators, Sellers, 
    Sellers_groups, collaborators_files, Client_reference, 
    Client_employment_info
)
from mcd_site.models import Projects, Bank_entities, Timeline
from mcd_site.utils import JsonRender, parse_semantic_date, pdf_gen, user_check_perms, user_permission
from dateutil.relativedelta import relativedelta

import datetime
import locale
import unicodedata

locale.setlocale(locale.LC_ALL,'es_CO.UTF-8')

# Create your views here.
@login_required
def partners_principal(request):
    can_view_clients = user_check_perms(request,'modulo clientes',raise_exception=False)
    can_view_sellers = user_check_perms(request,'modulo vendedores',raise_exception=False)
    
    if can_view_clients and can_view_sellers:
        class_clients = 'active'
        class_sellers = ''
    elif can_view_clients and not can_view_sellers:
        class_clients = 'active'
        class_sellers = 'disabled'
    elif not can_view_clients and can_view_sellers:
        class_clients = 'disabled'
        class_sellers = 'active'
    else:
        raise PermissionDenied
        
    
    context = {
        'form_clientes':forms.nuevo_cliente_form,
        'form_gestores':forms.gestores_form,
        'sellers_states':Sellers.seller_state_choices,
        'sellers_groups': Sellers_groups.objects.filter(status=True),
        'class_clients':class_clients,
        'class_sellers':class_sellers,
        'projects': Projects.objects.all()
    }
    
    
    
    return render(request,'partners.html',context)

@user_permission('ver colaboradores')
def collaborators(request):
    obj_collaborators = Collaborators.objects.filter(status='Activo'
                                    ).order_by('state')

    today = datetime.date.today()

    near_to_end_contracts = Collaborator_contracts.objects.filter(
        collaborator__status = 'Activo',
        end_date__gte = today,
        end_date__lte = today + relativedelta(months=1)
    )
    

    context = {
        'collaborators': obj_collaborators,
        'nte_contracts':near_to_end_contracts,
        'form': forms.collaborators_form,
        'form_react':forms.collab_react,
    }
    
    if request.method == 'GET' and request.GET:
        if request.is_ajax():
            type_of = request.GET.get('type')
            
            if type_of == 'active':
                obj_collaborators = Collaborators.objects.filter(status='Activo'
                                    ).order_by('state')
            elif type_of == 'all':
                obj_collaborators = Collaborators.objects.all().order_by('state')
            
            json = JsonRender(obj_collaborators,
                query_functions=('full_name','last_contract','all_contracts'))
            data = {
                'data':json.render()
            }
            
            return JsonResponse(data)
            
        
    elif request.method == 'POST':
        if request.is_ajax():
            action = request.POST.get('action')
            if action == 'retire':
                user_check_perms(
                    request, 'retirar colaborador', raise_exception=True)
                document = request.POST.get('colab_document')
                end_date = request.POST.get('retire_date')
                end_date = parse_semantic_date(end_date,'date')
                comments = request.POST.get('comments')
                
                collab = Collaborators.objects.get(id_document=document)

                active_contract = Collaborator_contracts.objects.filter(
                    collaborator = collab.pk
                ).last()

                if end_date.date() < active_contract.initial_date:
                    data = {
                        'class':'error',
                        'msj': 'No puedes retirar a un colaborador con fecha inferior o igual a la de inicio de su ultimo contrato'
                    }
                    return JsonResponse(data)

                collab.status = 'Retirado'
                collab.save()

                active_contract.end_date = end_date
                active_contract.comments = comments
                active_contract.save()

                data = {
                    'class':'success',
                    'msj': 'El colaborador fué retirado de la compañia'
                }
                Timeline.objects.create(
                    user=request.user,
                    action=f'Retiró al colaborador {collab.full_name()}',
                    aplication='RRHH'
                )

                return JsonResponse(data)

            elif action == 'reactivate':
                
                user_check_perms(
                    request, 'reactivar colaborador', raise_exception=True)
                document = request.POST.get('colab_document')
                
                type_of_contract = request.POST.get('type_of_contract_react')
                initial_date = request.POST.get('initial_date_react')
                initial_date = parse_semantic_date(initial_date,'date')
                duration = request.POST.get('duration_react',0)
                salary = request.POST.get('salary_react').replace(',','')
                position_name = request.POST.get('position_name_react')
                if type_of_contract == 'Indefinido':
                    end_date = None
                else:
                    end_date = initial_date + relativedelta(months=int(duration))

                collab = Collaborators.objects.get(id_document=document)

                last_contract = Collaborator_contracts.objects.filter(
                    collaborator = collab.pk
                ).last()

                if initial_date.date() <= last_contract.end_date:
                    data = {
                        'class':'error',
                        'msj': 'No puedes ingresar a un colaborador con fecha inferior o igual a la de terminación de su ultimo contrato'
                    }
                    return JsonResponse(data)
                
                collab.status = 'Activo'
                collab.save()

                Collaborator_contracts.objects.create(
                        collaborator = collab, type_of_contract = type_of_contract,
                        duration = duration, initial_date = initial_date,
                        end_date = end_date, position_name = position_name,
                        salary = salary
                    )
                data = {
                    'class':'success',
                    'msj': 'Reactivaste al colaborador seleccionado'
                }
                Timeline.objects.create(
                    user=request.user,
                    action=f'Reactivó al colaborador {collab.full_name()}',
                    aplication='RRHH'
                )

                return JsonResponse(data)

        else:
            user_check_perms(
                    request, 'crear colaborador', raise_exception=True)
            type_of = request.POST.get('type_of')
            document = request.POST.get('col_document')
            first_name = request.POST.get('col_first_name')
            last_name = request.POST.get('col_last_name')
            email = request.POST.get('col_email')
            phone = request.POST.get('col_phone')
            address = request.POST.get('col_address')
            birth_date = request.POST.get('col_birth_date')
            birth_date = parse_semantic_date(birth_date,'date')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            scholarity = request.POST.get('scholarity')
            bank_entity = request.POST.get('bank_entity')
            obj_bank_entity = Bank_entities.objects.get(pk=bank_entity)
            account_type = request.POST.get('account_type')
            bank_account_number = request.POST.get('bank_account_number')
            type_of_contract = request.POST.get('type_of_contract')
            initial_date = request.POST.get('initial_date')
            initial_date = parse_semantic_date(initial_date,'date')
            duration = request.POST.get('duration',0)
            if duration != '': duration = int(duration)
            salary = request.POST.get('salary').replace(',','')
            position_name = request.POST.get('position_name')
            cv_support = request.FILES.get('cv_support')
            contract_support = request.FILES.get('contract_support')
            bank_certificate = request.FILES.get('bank_certificate')
            eps = request.POST.get('eps')
            pension = request.POST.get('pension')
            cesantias = request.POST.get('cesantias')

            if type_of_contract == 'Indefinido':
                    end_date = None
            else:
                end_date = initial_date + relativedelta(months=int(duration))
            
            if type_of=='create':
                
                cv_support.name = ''.join(c for c in unicodedata.normalize('NFD', cv_support.name)
                                        if unicodedata.category(c) != 'Mn'
                                        ).replace('ñ','n')
                contract_support.name = ''.join(c for c in unicodedata.normalize('NFD', contract_support.name)
                                        if unicodedata.category(c) != 'Mn'
                                        ).replace('ñ','n')
                bank_certificate.name = ''.join(c for c in unicodedata.normalize('NFD', bank_certificate.name)
                                        if unicodedata.category(c) != 'Mn'
                                        ).replace('ñ','n')
                
                
                try:
                    collab = Collaborators.objects.create(
                        id_document = document, first_name = first_name, last_name = last_name,
                        email = email, phone = phone, address = address, city = city,
                        state = state, country = country, scholarity = scholarity,
                        bank_entity = obj_bank_entity, account_type = account_type,
                        bank_account_number = bank_account_number, birth_date = birth_date,
                        eps = eps, pension = pension, cesantias = cesantias
                    )
                    
                    Collaborator_contracts.objects.create(
                        collaborator = collab, type_of_contract = type_of_contract,
                        duration = duration, initial_date = initial_date,
                        end_date = end_date, position_name = position_name,
                        salary = salary
                    )
                    collaborators_files.objects.bulk_create([
                        collaborators_files(collaborator = collab,
                                            description = 'Hoja de vida',
                                            file = cv_support),
                        collaborators_files(collaborator = collab,
                                            description = 'Contrato',
                                            file = contract_support),
                        collaborators_files(collaborator = collab,
                                            description = 'Certificado bancario',
                                            file = bank_certificate)
                    ])
                    Timeline.objects.create(
                        user=request.user,
                        action=f'Creó al colaborador {collab.full_name()}',
                        aplication='RRHH'
                    )
                    
                    messages.success(request,'<div class="header">¡Lo hiciste!</div>Creaste al colaborador sin problemas.')
                except IntegrityError:
                    messages.error(request,'<div class="header">¡Ups!</div>El colaborador que intentas crear ya existe')
            
            elif type_of == 'modify':
                
                collab = Collaborators.objects.get(id_document=document)
                
                collab.first_name = first_name
                collab.last_name = last_name
                collab.email = email
                collab.phone = phone
                collab.address = address
                collab.city = city
                collab.state = state
                collab.country = country
                collab.scholarity = scholarity
                collab.bank_entity = obj_bank_entity
                collab.account_type = account_type
                collab.bank_account_number = bank_account_number
                collab.birth_date = birth_date
                collab.eps = eps
                collab.pension = pension
                collab.cesantias = cesantias
                collab.save()

                active_contract = Collaborator_contracts.objects.filter(
                    collaborator = collab.pk
                ).last()

                msj = 'Los datos del colaborador fueron actualizados con exito.'

                

                new_contract = False
                if type_of_contract != active_contract.type_of_contract:
                    new_contract = True
                elif initial_date.date() != active_contract.initial_date:
                    new_contract = True
                elif duration != active_contract.duration:
                    new_contract = True
                elif int(salary) != active_contract.salary:
                    new_contract = True

                if new_contract:
                    change_ok = True
                    if initial_date.date() <= active_contract.initial_date:
                        change_ok = False
                        msj = 'No puedes crear un contrato con fecha de inicio igual o inferior al contrato vigente.'
                    if active_contract.type_of_contract == 'Indefinido' and \
                        type_of_contract != 'Indefinido':
                        change_ok = False
                        msj = 'No puedes cambiar a un colaborador de contrato indefinido a otro tipo de contrato'
                    if change_ok:
                        if collab.status == 'Activo':
                            active_contract.end_date = initial_date - relativedelta(days=1)
                            active_contract.save()
                        Collaborator_contracts.objects.create(
                            collaborator = collab, type_of_contract = type_of_contract,
                            duration = duration, initial_date = initial_date,
                            end_date = end_date, position_name = position_name,
                            salary = salary
                        )
                        
                        msj += '; fué agregado un nuevo contrato'
                        messages.success(request,f'<div class="header">¡Lo hiciste!</div>{msj}')
                    else:
                        messages.error(request,f'<div class="header">¡Ups!</div>{msj}')
                
                else: 
                    messages.success(request,f'<div class="header">¡Lo hiciste!</div>{msj}')
                    Timeline.objects.create(
                        user=request.user,
                        action=f'Modificó los datos y/o contrato del colaborador {collab.full_name()}',
                        aplication='RRHH'
                    )
                
                

    else:
        msj = ''
        for contract in near_to_end_contracts:
            msj+= f'<li>El <b>{contract.end_date}</b>: {contract.collaborator.full_name()}</li>'
        if near_to_end_contracts.count() > 0:
            messages.warning(request,f'<div class="header">Contratos cercanos a su vencimiento:</div><ol>{msj}</ol>')
    
    return render(request,'collaborators.html',context)


def collaborators_docfiles(request):
    if request.is_ajax():
        if request.method == 'POST':
            to_do = request.POST.get('todo')
            description = request.POST.get('description')
            collab = request.POST.get('collab')
            
            
            if to_do == 'delete':
                user_check_perms(request,'eliminar documentos rrhh',raise_exception=True)
                obj_file = collaborators_files.objects.get(collaborator__id_document=collab,description=description)
                obj_file.delete()
                data = {
                    'class':'success',
                    'msj':'El documento seleccionado fué eliminado',
                }

                Timeline.objects.create(
                    user=request.user,
                    action=f'Eliminó un documento del gestor ({collab})',
                    aplication ='RRHH'
                )
                
                return JsonResponse(data)

            if to_do == 'create':
                if not request.FILES:
                    return JsonResponse({'class':'error','msj':'Debes cargar un archivo'})
                else:
                    file = request.FILES.get('file[0]')
                    collab = request.POST.get('collab_doc_id')
                    description = request.POST.get('doc_description')

                    obj_collab = Collaborators.objects.get(id_document=collab)

                    try:
                        collaborators_files.objects.create(
                            collaborator = obj_collab,
                            description = description,
                            file = file
                        )
                        data = {'class':'success','msj':'Listo! El documento se cargo sin problemas','code':1}
                    except IntegrityError:
                        data = {'class':'error','msj':'Error! Ya existe un documento con este nombre','code':2}
                        
                
                    return JsonResponse(data)
            
            
        elif request.method == 'GET':
            collab = request.GET.get('collab_doc')
            obj_files = collaborators_files.objects.filter(collaborator__id_document=collab)
            data ={
                'data':JsonRender(obj_files).render()
            }

            return JsonResponse(data)
    else:
        if request.method == 'POST':
            if not request.FILES:
                return JsonResponse({'class':'error','msj':'Debes cargar un archivo'})
            else:
                file = request.FILES.get('file[0]')
                collab = request.POST.get('collab_doc_id')
                description = request.POST.get('doc_description')

                obj_collab = Collaborators.objects.get(id_document=collab)

                try:
                    collaborators_files.objects.create(
                        collaborator = obj_collab,
                        description = description,
                        file = file
                    )
                    data = {'class':'success','msj':'Listo! El documento se cargo sin problemas','code':1}
                except IntegrityError:
                    data = {'class':'error','msj':'Error! Ya existe un documento con este nombre','code':2}
                    
            
                return JsonResponse(data)
        

#ajax
@login_required
def ajax_clients_info(request):
    #if request.is_ajax():
    if request.method == 'GET':
        todo = request.GET.get('todo')
        if todo == 'datatable':
            project = request.GET.get('project')
            obj_client = Clients.objects.exclude(client_document='')

            if project and project != 'Todos':
                obj_client = obj_client.filter(
                    Q(first_owner__project__pk=project) |
                    Q(second_owner__project__pk=project) |
                    Q(third_owner__project__pk=project)
                ).distinct('pk')

            # OPTIMIZADO: prefetch usando related_name correcto
            obj_client = obj_client.select_related('seller', 'employment_info').prefetch_related('references')

            data_rows = []
            for client in obj_client:
                employment = getattr(client, 'employment_info', None)
                refs = list(client.references.all())
                ref_fam = [r for r in refs if r.reference_type == 'familiar']
                ref_per = [r for r in refs if r.reference_type == 'personal']

                row = {
                    'client_document': client.client_document,
                    'identification_type': client.identification_type,
                    'first_name': client.first_name,
                    'last_name': client.last_name,
                    'full_name': client.full_name(),
                    'phone': client.phone,
                    'phone_house': getattr(client, 'house_phone', ''),
                    'phone_office': getattr(client, 'phone_office', ''),
                    'email': client.email,
                    'marital_status': client.marital_status,
                    'birth_date': client.birth_date.strftime('%Y-%m-%d') if client.birth_date else '',
                    'country': client.country,
                    'state': client.state,
                    'city': client.city,
                    'address': client.address,
                    'office_address': getattr(client, 'office', ''),
                    'neighborhood': getattr(client, 'neighborhood', ''),
                    'birth_place': getattr(client, 'birth_place', ''),
                    'lives_in_own_house': getattr(client, 'lives_in_own_house', False),
                    'seller': client.seller.pk if client.seller else '',
                    # Datos laborales
                    'company_name': employment.company_name if employment else '',
                    'position': employment.position if employment else '',
                    'profession': employment.profession if employment else '',
                    'occupation': employment.occupation if employment else '',
                    'monthly_salary': employment.monthly_salary if employment else '',
                    'years_experience': employment.years_experience if employment else '',
                    'company_city': employment.company_city if employment else '',
                    'company_address': employment.company_address if employment else '',
                    'company_phone': employment.company_phone if employment else '',
                    'social_organizations': employment.social_organizations if employment else '',
                    # Referencias familiares
                    'ref_familiar_1_name': ref_fam[0].name if len(ref_fam) > 0 else '',
                    'ref_familiar_1_occupation': ref_fam[0].occupation if len(ref_fam) > 0 else '',
                    'ref_familiar_1_phone': ref_fam[0].phone if len(ref_fam) > 0 else '',
                    'ref_familiar_2_name': ref_fam[1].name if len(ref_fam) > 1 else '',
                    'ref_familiar_2_occupation': ref_fam[1].occupation if len(ref_fam) > 1 else '',
                    'ref_familiar_2_phone': ref_fam[1].phone if len(ref_fam) > 1 else '',
                    # Referencias personales
                    'ref_personal_1_name': ref_per[0].name if len(ref_per) > 0 else '',
                    'ref_personal_1_occupation': ref_per[0].occupation if len(ref_per) > 0 else '',
                    'ref_personal_1_phone': ref_per[0].phone if len(ref_per) > 0 else '',
                    'ref_personal_2_name': ref_per[1].name if len(ref_per) > 1 else '',
                    'ref_personal_2_occupation': ref_per[1].occupation if len(ref_per) > 1 else '',
                    'ref_personal_2_phone': ref_per[1].phone if len(ref_per) > 1 else '',
                }
                data_rows.append(row)

            data = {'data': data_rows}
            return JsonResponse(data)
    if request.method == 'POST':
        client_document = request.POST.get('client_document')
        first_name = request.POST.get('first_name').upper()
        last_name = request.POST.get('last_name').upper()
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        marital_status = request.POST.get('marital_status')
        address = request.POST.get('address')
        country = request.POST.get('country')
        state = request.POST.get('state')
        city = request.POST.get('city')
        birth_date = request.POST.get('birth_date')
        dt_birth_date = datetime.datetime.strptime(birth_date, '%B %d, %Y')
        seller = request.POST.get('seller')
        office = request.POST.get('office_address')
        phone_office = request.POST.get('phone_office')
        house_phone = request.POST.get('phone_house')

        # Nuevos campos básicos
        identification_type = request.POST.get('identification_type', 'CC')
        neighborhood = request.POST.get('neighborhood', '')
        birth_place = request.POST.get('birth_place', '')
        lives_in_own_house = request.POST.get('lives_in_own_house') == 'on'
        city_name = request.POST.get('city', '')
        state_name = request.POST.get('state', '')
        country_name = request.POST.get('country', '')

        obj_seller = Sellers.objects.filter(pk=seller).first() if seller else None

        try:
            if not user_check_perms(request, 'modificar clientes'):
                data = {
                    'type': 'error',
                    'title': 'Permisos insuficientes',
                    'msj': 'No tienes permisos suficientes para hacer esto',
                }
                return JsonResponse(data)

            # Actualiza todos los campos del modelo Clients
            Clients.objects.filter(client_document=client_document).update(
                identification_type=identification_type,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                marital_status=marital_status,
                address=address,
                country=country,
                state=state,
                city=city,
                birth_date=dt_birth_date,
                seller=obj_seller,
                office=office,
                phone_office=phone_office,
                house_phone=house_phone,
                neighborhood=neighborhood,
                birth_place=birth_place,
                lives_in_own_house=lives_in_own_house,
                city_name=city_name,
                state_name=state_name,
                country_name=country_name,
            )

            client = Clients.objects.get(client_document=client_document)

            # Información laboral (OneToOne)
            employment_data = {
                'company_name': request.POST.get('company_name', ''),
                'position': request.POST.get('position', ''),
                'profession': request.POST.get('profession', ''),
                'occupation': request.POST.get('occupation', ''),
                'monthly_salary': request.POST.get('monthly_salary') or None,
                'years_experience': request.POST.get('years_experience') or None,
                'company_city': request.POST.get('company_city', ''),
                'company_address': request.POST.get('company_address', ''),
                'company_phone': request.POST.get('company_phone', ''),
                'social_organizations': request.POST.get('social_organizations', ''),
            }
            

            if any(employment_data.values()):
                Client_employment_info.objects.update_or_create(
                    client=client, defaults=employment_data
                )

            # Referencias familiares y personales
            Client_reference.objects.filter(client=client).delete()
            referencias = []
            # Familiares
            for i in [1, 2]:
                name = request.POST.get(f'ref_familiar_{i}_name')
                if name:
                    referencias.append(Client_reference(
                        client=client,
                        reference_type='familiar',
                        name=name,
                        occupation=request.POST.get(f'ref_familiar_{i}_occupation', ''),
                        phone=request.POST.get(f'ref_familiar_{i}_phone', '')
                    ))
            # Personales
            for i in [1, 2]:
                name = request.POST.get(f'ref_personal_{i}_name')
                if name:
                    referencias.append(Client_reference(
                        client=client,
                        reference_type='personal',
                        name=name,
                        occupation=request.POST.get(f'ref_personal_{i}_occupation', ''),
                        phone=request.POST.get(f'ref_personal_{i}_phone', '')
                    ))
            if referencias:
                Client_reference.objects.bulk_create(referencias)

            data = {
                'type': 'success',
                'title': '¡Lo hicimos!',
                'msj': 'La información del cliente fue modificada correctamente.',
            }

        except Exception as e:
            data = {
                'type': 'error',
                'title': 'Error',
                'msj': f'Ocurrió un error al modificar el cliente: {str(e)}',
            }

        return JsonResponse(data)
    
    
    return JsonResponse({'error':'error en el request'})

def ajax_sales_by_client(request):
    if request.is_ajax():
        if request.method == 'GET':
            client = request.GET.get('client_id')
            obj_sales = Sales.objects.filter(Q(first_owner = client)|Q(second_owner = client)|Q(third_owner = client))
        
            data = '<div class="ui list">'
            if obj_sales.count() == 0:
                data += f'<div class="item">Ningun contrato asociado</div>'
            for sale in obj_sales:
                if sale.status == 'Adjudicado' or sale.status == 'Desistido':
                    href = f'/sales/{sale.project.name}/adjudicatesales?sale={sale.contract_number}'
                    msj = f'{sale.project.name_to_show}: <a href="{href}">CTR{sale.contract_number}</a> ({sale.status})'
                elif sale.status == 'Pendiente':
                    href = f'/sales/{sale.project.name}/nonapprovedsales?sale={sale.contract_number}'
                    msj = f'{sale.project.name_to_show}: <a href="{href}">CTR{sale.contract_number}</a> ({sale.status})'
                elif sale.status == 'Aprobado': 
                    href = f'/sales/{sale.project.name}/toadjudicatesales?sale={sale.contract_number}'
                    msj = f'{sale.project.name_to_show}: <a href="{href}">CTR{sale.contract_number}</a> ({sale.status})'
                elif sale.status == 'Anulado':
                    msj = f'{sale.project.name_to_show}: CTR{sale.contract_number} ({sale.status})'
                data += f'<div class="item">{msj}</div>'
                
            data += '</div>'
            
            return JsonResponse({'data':data})
            
@login_required
def ajax_sellers_info(request):
    if request.method == 'GET':
        seller = request.GET.get('seller')
        if seller:
            seller_data = Sellers.objects.filter(seller_document=seller)
            if seller_data.exists():
                seller_projects = seller_data[0].projects.all()
                data = {
                    'data':JsonRender(seller_data,query_functions=['full_name']).render(),
                    'projects_data':JsonRender(seller_projects).render(),
                }
                return JsonResponse(data)
        obj_sellers = Sellers.objects.all()
        data = {
            'data':JsonRender(obj_sellers,query_functions=['full_name']).render()
        }
        return JsonResponse(data)

    if request.method == 'POST':
        seller_document = request.POST.get('seller_document')
        seller_first_name = request.POST.get('seller_first_name')
        seller_last_name = request.POST.get('seller_last_name')
        seller_email = request.POST.get('seller_email')
        seller_phone = request.POST.get('seller_phone')
        seller_address = request.POST.get('seller_address')
        seller_birth_date = request.POST.get('seller_birth_date')
        seller_marital_status = request.POST.get('seller_marital_status')
        seller_city = request.POST.get('seller_city')
        seller_state = request.POST.get('seller_state')
        seller_country = request.POST.get('seller_country')
        cv_support = request.FILES.get('cv_support')
        rut_support = request.FILES.get('rut_support')
        bank_certificate = request.FILES.get('bank_certificate')
        bank_entity = request.POST.get('bank_entity')
        account_type = request.POST.get('account_type')
        bank_account_number = request.POST.get('bank_account_number')
        retencion = request.POST.get('retencion')
        projects = request.POST.getlist('projects')
        obj_bank_ent = Bank_entities.objects.get(pk=bank_entity)
        dt_birth_date = datetime.datetime.strptime(seller_birth_date, '%B %d, %Y')
        pmt = request.POST.get('pay_pmt')
        if pmt == 'on': pmt = True
        else: pmt = False
        
        files_limit = 10 * 1024 * 1024
        
        if cv_support.size > files_limit or rut_support.size > files_limit or bank_certificate.size > files_limit:
            data = {
                    'type':'error',
                    'title':'Encontramos un problema',
                    'msj':'Cargaste un archivo soporte de un tamaño mayor a 10mb',
                    'formaction':''
                }

            return JsonResponse(data)
        
        try:
            cv_support.name = ''.join(c for c in unicodedata.normalize('NFD', cv_support.name)
                                        if unicodedata.category(c) != 'Mn'
                                        ).replace('ñ','n')
            rut_support.name = ''.join(c for c in unicodedata.normalize('NFD', rut_support.name)
                                        if unicodedata.category(c) != 'Mn'
                                        ).replace('ñ','n')
            bank_certificate.name = ''.join(c for c in unicodedata.normalize('NFD', bank_certificate.name)
                                        if unicodedata.category(c) != 'Mn'
                                        ).replace('ñ','n')
            new_seller = Sellers.objects.create(seller_document=seller_document, first_name=seller_first_name,
                    last_name = seller_last_name, email=seller_email, phone =seller_phone, address = seller_address,
                    city = seller_city, state = seller_state, country = seller_country, cv = cv_support,
                    rut_support = rut_support, bank_certificate = bank_certificate, bank_entity = obj_bank_ent,
                    seller_type = 'Inactivo', retencion = retencion, account_type = account_type,
                    bank_account_number = bank_account_number, birth_date = dt_birth_date,
                    marital_status = seller_marital_status, pay_pmt = pmt
                )

            
            for project in projects:
                if project != "":
                    obj_project = Projects.objects.get(pk=project)
                    new_seller.projects.add(obj_project)

            data = {
                    'type':'success',
                    'title':'¡Lo hicimos!',
                    'msj':'El gestor fue creado sin problemas',
                }
            
        except IntegrityError:
            data = {
                    'type':'error',
                    'title':'Encontramos un problema',
                    'msj':'El gestor que intentas registrar ya existe en la base de datos, por favor revisa el numero de documento',
                    'formaction':''
                }

        return JsonResponse(data)
    
    return JsonResponse({'error':'no hay response asociado'})    

@login_required
def ajax_update_seller_info(request,seller_id):
    data = {}
    if request.method == 'POST':
        type_of_change = request.POST.get('type_of_change')
        
        if type_of_change == 'state':
            new_state = request.POST.get('new_state')
            obj_seller = Sellers.objects.get(seller_document = seller_id)
            obj_seller.seller_state = new_state
            obj_seller.save()
            Timeline.objects.create(
                user=request.user,
                action=f'Modificó el estado del gestor {seller_id} a {new_state.upper()}',
                aplication ='Partners'
            )
            data = {
                'type':'success',
                'title':'¡Lo hicimos!',
                'msj':'Se actualizó el estado del gestor',
            }
        elif type_of_change == 'group':
            new_group = request.POST.get('group')
            obj_seller = Sellers.objects.get(seller_document = seller_id)
            obj_group = Sellers_groups.objects.get(pk=new_group)
            obj_seller.sales_group = obj_group
            obj_seller.save()
            Timeline.objects.create(
                user=request.user,
                action=f'Asignó el grupo de ventas {obj_group.name} al gestor {seller_id}',
                aplication ='Partners'
            )
            data = {
                'type':'success',
                'title':'¡Lo hicimos!',
                'msj':f'Se el gestor al grupo de ventas {obj_group.name}',
            }

            
    return JsonResponse(data)

@login_required
def ajax_seller_statics(request):
    if request.is_ajax():
        if request.method == 'GET':
            seller = request.GET.get('seller')
            obj_seller = Sellers.objects.get(pk=seller)
            
            obj_cxs = Clients.objects.filter(
                seller = seller
            )
            weeksago = datetime.date.today() - relativedelta(days=7)
            monthago = datetime.date.today() - relativedelta(months=1)
            days = obj_seller.active_days()
            if days == 0: days = 1
            
            avg = obj_cxs.count() / math.ceil(days/30)
            
            clients_per_seller = {
                'weeksago': obj_cxs.filter(add_date__gte=weeksago).count(),
                'monthago':obj_cxs.filter(add_date__gte=monthago).count(),
                'always':obj_cxs.count(),
                'avg':avg
            }
            
            obj_sxs = Assigned_comission.objects.filter(
                position__name='Generador',
                seller = seller, 
            )
            avg = obj_sxs.count() / math.ceil(days/30)
            
            sales_per_seller = {
                'weeksago': obj_sxs.filter(sale__add_date__gte=weeksago).count(),
                'monthago':obj_sxs.filter(sale__add_date__gte=monthago).count(),
                'always':obj_sxs.count(),
                'avg':avg
            }
            
            data = {
                'clients_per_seller':clients_per_seller,
                'sales_per_seller':sales_per_seller,
            }
            
            return JsonResponse(data)

@login_required
def clients_projects_view(request):
    """
    Renderiza la página interactiva para buscar clientes y mostrar sus proyectos asociados.
    """
    return render(request, 'clients_projects.html')

@login_required
def ajax_clients_projects(request):
    if request.method == 'GET' and request.is_ajax():
        clients_data = {}
        sales = Sales.objects.select_related('project', 'first_owner', 'second_owner', 'third_owner')

        for sale in sales:
            # Procesar el primer titular
            if sale.first_owner and sale.first_owner.client_document.strip():
                client_key = sale.first_owner.client_document
                if client_key not in clients_data:
                    clients_data[client_key] = {
                        'document': sale.first_owner.client_document,
                        'name': sale.first_owner.full_name(),
                        'email': sale.first_owner.email or "N/A",
                        'phone': sale.first_owner.phone or "N/A",
                        'project': [],  # Cambiado de set() a lista []
                        'contracts': [],
                        'roles': set()
                    }
                clients_data[client_key]['project'].append({
                    'name': sale.project.name_to_show,
                    'logo_url': sale.project.logo.url  # Suponiendo que el modelo Project tiene este campo
                })
                clients_data[client_key]['contracts'].append(f"CTR{sale.contract_number} ({sale.status})")
                clients_data[client_key]['roles'].add("Titular 1")

            # Procesar el segundo titular
            if sale.second_owner and sale.second_owner.client_document.strip():
                client_key = sale.second_owner.client_document
                if client_key not in clients_data:
                    clients_data[client_key] = {
                        'document': sale.second_owner.client_document,
                        'name': sale.second_owner.full_name(),
                        'email': sale.second_owner.email or "N/A",
                        'phone': sale.second_owner.phone or "N/A",
                        'project': [],
                        'contracts': [],
                        'roles': set()
                    }
                clients_data[client_key]['project'].append({
                    'name': sale.project.name_to_show,
                    'logo_url': sale.project.logo.url
                })
                clients_data[client_key]['contracts'].append(f"CTR{sale.contract_number} ({sale.status})")
                clients_data[client_key]['roles'].add("Titular 2")

            # Procesar el tercer propietario
            if sale.third_owner and sale.third_owner.client_document.strip():
                client_key = sale.third_owner.client_document
                if client_key not in clients_data:
                    clients_data[client_key] = {
                        'document': sale.third_owner.client_document,
                        'name': sale.third_owner.full_name(),
                        'email': sale.third_owner.email or "N/A",
                        'phone': sale.third_owner.phone or "N/A",
                        'project': [],
                        'contracts': [],
                        'roles': set()
                    }
                clients_data[client_key]['project'].append({
                    'name': sale.project.name_to_show,
                    'logo_url': sale.project.logo.url
                })
                clients_data[client_key]['contracts'].append(f"CTR{sale.contract_number} ({sale.status})")
                clients_data[client_key]['roles'].add("Titular 3")

        # Convertir los datos a una lista y formatear los campos
        formatted_data = []
        for client in clients_data.values():
            formatted_data.append({
                'document': client['document'],
                'name': client['name'],
                'email': client['email'],
                'phone': client['phone'],
                'project': [
                    f"<img src='{p['logo_url']}' alt='Logo' style='height: 20px; margin-right: 5px;'>{p['name']}"
                    for p in client['project']
                ],
                'contracts': ', '.join(client['contracts']),
                'roles': ', '.join(client['roles'])
            })

        return JsonResponse({'data': formatted_data})

def success_page(request):
    return render(request, 'success.html')

# ...existing code...

def public_client_registration(request):
    """Vista pública para el registro de clientes."""
    if request.method == 'POST':
        if request.is_ajax():
            valid_countries = [(request.POST.get('country'), request.POST.get('country'))]
            valid_states = [(request.POST.get('state'), request.POST.get('state'))]
            valid_cities = [(request.POST.get('city'), request.POST.get('city'))]

            form = forms.nuevo_cliente_form(request.POST, valid_countries=valid_countries, 
                                          valid_states=valid_states, valid_cities=valid_cities)
            
            if form.is_valid():
                try:
                    # Crear cliente con TODOS los campos incluidos los nuevos
                    client = Clients.objects.create(
                        client_document=form.cleaned_data['client_document'],
                        identification_type=form.cleaned_data['identification_type'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        phone_office=form.cleaned_data.get('phone_office', ''),
                        house_phone=form.cleaned_data.get('phone_house', ''),
                        address=form.cleaned_data['address'],
                        office=form.cleaned_data.get('office_address', ''),
                        birth_date=form.cleaned_data['birth_date'],
                        marital_status=form.cleaned_data['marital_status'],
                        country=form.cleaned_data['country'],
                        state=form.cleaned_data['state'],
                        city=form.cleaned_data['city'],
                        seller=form.cleaned_data.get('seller'),
                        
                        # ✅ NUEVOS CAMPOS AGREGADOS
                        neighborhood=form.cleaned_data.get('neighborhood', ''),
                        birth_place=form.cleaned_data.get('birth_place', ''),
                        lives_in_own_house=form.cleaned_data.get('lives_in_own_house', False),
                        city_name=form.cleaned_data.get('city', ''),
                        state_name=form.cleaned_data.get('state', ''),
                        country_name=form.cleaned_data.get('country', ''),
                    )
                    
                    # Crear información laboral si se proporcionó
                    employment_data = {
                        'company_name': form.cleaned_data.get('company_name', ''),
                        'position': form.cleaned_data.get('position', ''),
                        'profession': form.cleaned_data.get('profession', ''),
                        'occupation': form.cleaned_data.get('occupation', ''),
                        'monthly_salary': form.cleaned_data.get('monthly_salary'),
                        'years_experience': form.cleaned_data.get('years_experience'),
                        'company_city': form.cleaned_data.get('company_city', ''),
                        'company_address': form.cleaned_data.get('company_address', ''),
                        'company_phone': form.cleaned_data.get('company_phone', ''),
                        'social_organizations': form.cleaned_data.get('social_organizations', ''),
                    }
                    
                    # Solo crear si hay algún dato laboral
                    if any(employment_data.values()):
                        Client_employment_info.objects.create(client=client, **employment_data)
                    
                    # Crear referencias familiares y personales
                    references_to_create = []
                    
                    # Referencias familiares
                    for i in [1, 2]:
                        name = form.cleaned_data.get(f'ref_familiar_{i}_name')
                        if name:
                            references_to_create.append(Client_reference(
                                client=client,
                                reference_type='familiar',
                                name=name,
                                occupation=form.cleaned_data.get(f'ref_familiar_{i}_occupation', ''),
                                phone=form.cleaned_data.get(f'ref_familiar_{i}_phone', '')
                            ))
                    
                    # Referencias personales
                    for i in [1, 2]:
                        name = form.cleaned_data.get(f'ref_personal_{i}_name')
                        if name:
                            references_to_create.append(Client_reference(
                                client=client,
                                reference_type='personal',
                                name=name,
                                occupation=form.cleaned_data.get(f'ref_personal_{i}_occupation', ''),
                                phone=form.cleaned_data.get(f'ref_personal_{i}_phone', '')
                            ))
                    
                    # Crear todas las referencias en bulk
                    if references_to_create:
                        Client_reference.objects.bulk_create(references_to_create)
                    
                    return JsonResponse({
                        'type': 'success',
                        'title': '¡Registro exitoso!',
                        'msj': 'Tus datos fueron registrados correctamente.'
                    })
                    
                except Exception as e:
                    return JsonResponse({
                        'type': 'error',
                        'title': 'Error al registrar',
                        'msj': f'Ocurrió un error: {str(e)}'
                    })
            else:
                return JsonResponse({
                    'type': 'error',
                    'title': 'Error en el formulario',
                    'msj': 'Por favor corrige los errores en el formulario.',
                    'errors': form.errors
                })
    else:
        form = forms.nuevo_cliente_form()
        # Eliminar campo seller para registro público
        if 'seller' in form.fields:
            form.fields.pop('seller')
            # Ajustar layout para registro público
            form.helper.layout[0][0][0].css_class = 'two fields'

    return render(request, 'public_client_registration.html', {'form': form})

# ...existing code...

urls = [
    path('principal',partners_principal,name='partners principal'),
    path('collaborators',collaborators),
    path('collaborators/uploadfiles',collaborators_docfiles),
    path('clientes', clients_projects_view, name='clients_projects_view'),
    path('registro-clientes/', public_client_registration, name='public_client_registration'),
    path('registro-exitoso/', success_page, name='success_page'),
] + [
    path('ajax/clientsinfo',ajax_clients_info),
    path('ajax/sellersinfo',ajax_sellers_info),
    path('ajax/salesbyclient',ajax_sales_by_client),
    path('ajax/updateseller/<seller_id>',ajax_update_seller_info),
    path('ajax/seller_statics',ajax_seller_statics),
    path('ajax/clients_projects', ajax_clients_projects, name='ajax_clients_projects'),
]


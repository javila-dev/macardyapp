from calendar import month
from datetime import date, datetime
import json

import xhtml2pdf
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.template.loader import get_template
from django.urls.conf import path
from django.contrib.sites.models import Site
from django.contrib import messages
from xhtml2pdf import pisa
import numpy_financial as npf
from dateutil.relativedelta import relativedelta
from mcd_site.forms import usersForm
from mcd_site.models import Perfil, Rol, Timeline, Projects, Permiso
from mcd_site.utils import JsonRender, link_callback, parse_semantic_date, passwordgenerate, send_email_template, user_permission
from terceros.models import Collaborators

#messages.success(request,'<div class="header">¡Lo hicimos!</div>Aprobaste el contrato '+sale)
# Create your views here.

@login_required
def landing(request):
    profiles_actives = Perfil.objects.filter(usuario__is_active=True)
    today = date.today()
    sp_dt = []
    """ for profile in profiles_actives:
        if profile.fecha_nacimiento and profile.fecha_nacimiento.month == today.month:
            sp_dt.append({
                'type':'birthday',
                'profile':profile
            })
        if profile.usuario.date_joined.month == today.month:
            years_in_company = relativedelta(today,profile.usuario.date_joined.date()).years
            if years_in_company > 0:
                sp_dt.append({
                    'type':'aniversary',
                    'profile':profile,
                    'years':years_in_company
                }) """
    
    obj_collaborators = Collaborators.objects.filter(status='Activo')

    for collab in obj_collaborators:
        if collab.birth_date.month == today.month:
            sp_dt.append({
                'type':'birthday',
                'profile':collab
            })
        last_contract = collab.last_contract()
        if last_contract != None:
            if collab.last_contract().get('initial_date').month == today.month:
                years_in_company = relativedelta(today,collab.last_contract().get('initial_date')).years
                if years_in_company > 0:
                    sp_dt.append({
                        'type':'aniversary',
                        'profile':collab,
                        'years':years_in_company
                    })

    context = {
        'special_dates':sp_dt
    }
    
    return render(request,'landing_page.html',context)

def render_pdf_view(request):
    template_path = 'pdf/ejemplo_pdf.html'
    context = {'proyecto': 'EJEMPLO DE PROYECTO'}
    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=response, link_callback=link_callback)
    # if error then show some funy view
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

@user_permission('ver historial')
def history_actions(request):
    obj_hist = Timeline.objects.all().order_by('-date')
    context = {
        'timeline':obj_hist
    }
    return render(request,'timeline.html',context)

@login_required
@user_permission('administrar usuarios')
def users_admin(request):
    context = {
        'users': User.objects.exclude(is_superuser=True).order_by('-is_active','username'),
        'projects': Projects.objects.all(),
        'form': usersForm,
    }
    if request.is_ajax():
        if request.method == 'GET':
            user = request.GET.get('user')
            obj_profile = Perfil.objects.filter(usuario = user)
            rols = obj_profile[0].rol.all().values_list('id')
            projects = obj_profile[0].projects.all().values_list('name')
            
            obj_user = User.objects.filter(pk=user).values(
                'username','first_name','last_name','email','is_staff','is_active'
            )
            
            data = {
                'profile':JsonRender(obj_profile).render(),
                'rols':list(rols),
                'projects':list(projects),
                'user':list(obj_user)
            }
            
            return JsonResponse(data)
    
    else:
        if request.method == 'POST':
            if request.POST.get('is_new'):
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email = request.POST.get('email')
                is_staff = request.POST.get('is_staff')
                birth_date = request.POST.get('birth_date')
                rols = request.POST.getlist('rols')
                projects = request.POST.getlist('projects')
                
                username_p1 = first_name.split(" ")[0][0]
                username_p2 = last_name.split(" ")[0]
                username = username_p1 + username_p2
                
                if User.objects.filter(email = email).exists():
                    messages.error(request,'<div class="header">¡Ups!</div>Ya existe un usuario asociado a este correo electronico, intenta con uno nuevo o cambia el correo asociado en el otro usuario.')
                    return render(request,'users_admin.html',context)
                
                if User.objects.filter(username = username).exists():
                    username_p1 = first_name.split(" ")[0]
                    if len(username_p1) > 1:
                        username_p1 = first_name.split(" ")[0][0] + first_name.split(" ")[0][1]
                    username_p2 = last_name.split(" ")[0]
                    username = username_p1 + username_p2
                
                    if User.objects.filter(username = username).exists():
                        username_p1 = first_name.split(" ")[0][:2]
                        username_p2 = last_name.split(" ")[0]
                        username = username_p1 + username_p2
                        
                        if User.objects.filter(username = username).exists():
                            username_p1 = first_name.split(" ")[0]
                            username_p2 = last_name.split(" ")[0][:4]
                            username = username_p1 + username_p2
                            
                pswd = passwordgenerate()
                
                username = username.lower().replace(" ","")
                user = User.objects.create_user(                    
                    username,email,pswd)
                
                user.first_name = first_name
                user.last_name = last_name
                user.is_active = True
                user.is_staff = True if is_staff == 'on' else False
                user.save()
                
                profile = Perfil.objects.create(
                    usuario = user,
                    identificacion = request.POST.get('user_id'),
                    fecha_nacimiento = parse_semantic_date(birth_date,'date'),
                    force_change_pswd = True
                )
                
                for rol in rols:
                    if rol == "": continue
                    obj_rol = Rol.objects.get(pk=rol)
                    profile.rol.add(obj_rol)
                    
                for project in projects:
                    if project == "": continue
                    obj_project = Projects.objects.get(pk=project)
                    profile.projects.add(obj_project)
                
                if request.FILES.get('picture'):
                    profile.avatar = request.FILES.get('picture')
                    profile.save()
                    
                messages.success(request,f'<div class="header">¡Lo hicimos!</div>Se creó el usuario <strong>{username}</strong>, los datos para el inicio de sesión fueron enviados al correo registrado.')

                Timeline.objects.create(
                    user = request.user,
                    action = f'Creó el usuario {username}',
                    aplication = 'users'
                )
                domain = Site.objects.get_current().domain
                
                protocol = 'HTTP'
                email_message = f'''Te damos la bienvenida a MacardyApp, a continuación te damos los datos para tu inicio de sesión:
                    <ul>
                        <li>
                            <strong>Usuario:</strong> {username}
                        </li>
                        <li>
                            <strong>Contraseña:</strong> {pswd}
                        </li>
                    </ul><br>
                    Para ingresar puedes hacer click <a href="{protocol}://{domain}/accounts/login">aquí</a>,
                     te recomendamos cambiar la contraseña una vez ingreses por primera vez.
                '''
                
                email_context = {
                    'email_title': '¡Bienvenid@!',
                    'email_message': email_message,
                    'user':user
                }
                
                send_email_template(f'Bienvenido a MacardyApp {username}',
                                    [email,],
                                    template='email_notification.html',
                                    template_context=email_context)
                
            else:
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email = request.POST.get('email')
                is_staff = request.POST.get('is_staff')
                is_active = request.POST.get('is_active')
                birth_date = request.POST.get('birth_date')
                rols = request.POST.getlist('rols')
                projects = request.POST.getlist('projects')
                username = request.POST.get('username')
                
                user = User.objects.get(username = username)
                
                if User.objects.filter(email = email).exists() and email != user.email:
                    messages.error(request,'<div class="header">¡Ups!</div>Ya existe un usuario asociado a este correo electronico, intenta con uno nuevo o cambia el correo asociado en el otro usuario.')
                    return render(request,'users_admin.html',context)
                
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.is_active = True if is_active == 'on' else False 
                user.is_staff = True if is_staff == 'on' else False
                user.save()
                
                profile = Perfil.objects.get(usuario = user.pk)
                profile.identificacion = request.POST.get('user_id'),
                profile.fecha_nacimiento = parse_semantic_date(birth_date,'date'),
                
                profile_rols = profile.rol.all()
                for rol in profile_rols:
                    if rol.pk not in rols:
                        profile.rol.remove(rol)
                
                for rol in rols:
                    obj_rol = Rol.objects.get(pk=rol)
                    has_rol = profile.rol.filter(pk=rol).exists()
                    if not has_rol:
                        profile.rol.add(obj_rol)
                
                profile_projects = profile.projects.all()
                for proj in profile_projects:
                    if proj.pk not in projects:
                        profile.projects.remove(proj)
                
                for project in projects:
                    obj_project = Projects.objects.get(pk=project)
                    has_project = profile.projects.filter(pk=project).exists()
                    
                    if not has_project:
                        profile.projects.add(obj_project)
                        
                messages.success(request,
                    f'<div class="header">¡Lo hicimos!</div>Se actualizaron los datos del usuario <strong>{username}</strong>')

                Timeline.objects.create(
                    user = request.user,
                    action = f'Actualizó los datos del usuario {username}',
                    aplication = 'users'
                )
    
    context = {
        'users': User.objects.exclude(is_superuser=True).order_by('-is_active','username'),
        'projects': Projects.objects.all(),
        'form': usersForm,
    }
    
    
    
    return render(request,'users_admin.html',context)

@login_required
@user_permission('administrar usuarios')
def rol_form(request, pk=None):
    rol = get_object_or_404(Rol, pk=pk) if pk else None
    if request.method == 'POST':
        desc = request.POST.get('descripcion', '').strip()
        permisos = request.POST.getlist('permisos')
        if not desc:
            messages.error(request, 'La descripción es obligatoria.')
        else:
            if rol:
                rol.descripcion = desc
                rol.save()
                rol.permisos.set(Permiso.objects.filter(pk__in=permisos))
                Timeline.objects.create(
                    user=request.user,
                    action=f'Modificó el rol "{rol.descripcion}"',
                    aplication='mcd_site'
                )
                messages.success(request, 'Rol actualizado.')
            else:
                rol = Rol.objects.create(descripcion=desc)
                rol.permisos.set(Permiso.objects.filter(pk__in=permisos))
                Timeline.objects.create(
                    user=request.user,
                    action=f'Creó el rol "{rol.descripcion}"',
                    aplication='mcd_site'
                )
                messages.success(request, 'Rol creado.')
            return redirect(reverse('rol_form', args=[rol.pk]))
    permisos = Permiso.objects.all()
    roles = Rol.objects.all().order_by('descripcion')
    return render(request, 'rol_form.html', {
        'rol': rol,
        'permisos': permisos,
        'roles': roles,
    })

#Ajax requests

def ajax_countries_data(request):
    if request.is_ajax():
        if request.method == 'GET':
            tipo = request.GET.get('tipo')
            paises = []
            estados = []
            ciudades = []
            if tipo == 'countries':
                file_paises = open(settings.STATIC_ROOT /'json/countries.json',encoding="utf8")
                json_file = json.loads(file_paises.read().encode().decode('utf-8-sig'))
                
                for pais in json_file['countries']:
                    paises.append((pais.get('id'),pais.get('name')))
                    
            elif tipo == 'states':
                pais = request.GET.get('pais')
                file_estados = open(settings.STATIC_ROOT/'json/states.json',encoding="utf8")
                json_file = json.loads(file_estados.read().encode().decode('utf-8-sig'))
                
                for estado in json_file['states']:
                    if estado.get('id_country')==int(pais):
                        estados.append((estado.get('id'),estado.get('name')))
            
            elif tipo == 'cities':
                estado = request.GET.get('estado')
                file_ciudades = open(settings.STATIC_ROOT/'json/cities.json',encoding="utf8")
                json_file = json.loads(file_ciudades.read().encode().decode('utf-8-sig'))
                
                for ciudad in json_file['cities']:
                    if ciudad.get('id_state')==int(estado):
                        ciudades.append((ciudad.get('id'),ciudad.get('name')))
            
            data = {
                'paises':paises,
                'estados':estados,
                'ciudades':ciudades,
            }
            
            return JsonResponse(data)

def ajax_ss_entities_data(request):
    type_of = request.GET.get('type')
    file = open(settings.STATIC_ROOT /'json/ss_entities.json',encoding="utf8")
    json_file = json.loads(file.read().encode().decode('utf-8-sig'))
    
    entities = []
    
    for entity in json_file[type_of]:
        entities.append((entity.get('id'),entity.get('name')))
        
    return JsonResponse({'data':entities})
        
def ajax_get_rol(request, pk):
    if request.is_ajax():
        rol = get_object_or_404(Rol, pk=pk)
        data = {
            'descripcion': rol.descripcion,
            'permisos': list(rol.permisos.values_list('pk', flat=True))
        }
        return JsonResponse(data)
        
def spanish_datatables(request):
    data ={
	"sProcessing":     "Procesando...",
	"sLengthMenu":     "Mostrar _MENU_ registros",
	"sZeroRecords":    "No se encontraron resultados",
	"sEmptyTable":     "Ningún dato disponible en esta tabla",
	"sInfo":           "Registros del _START_ al _END_ de un total de _TOTAL_ registros",
	"sInfoEmpty":      "0 Registros para mostrar",
	"sInfoFiltered":   "(filtrado de un total de _MAX_ registros)",
	"sInfoPostFix":    "",
	"sSearch":         "Buscar:",
	"sUrl":            "",
	"sInfoThousands":  ",",
	"sLoadingRecords": "Cargando...",
	"oPaginate": {
		"sFirst":    "Primero",
		"sLast":     "Último",
		"sNext":     "Siguiente",
		"sPrevious": "Anterior"
	},
	"oAria": {
		"sSortAscending":  ": Activar para ordenar la columna de manera ascendente",
		"sSortDescending": ": Activar para ordenar la columna de manera descendente"
	},
    "searchBuilder": {
        "add":'Nuevo filtro',
        "clearAll":'Borrar filtro',
        "deleteTitle":'Borrar',
        "data":'Columna',
        "logicAnd":'Y',
        "logicOr":'O',
        "condition": 'Condición',
        "value": 'Valor',
        "title": 'Filtro Avanzado',
    },
    'buttons': {
                'colvis': 'Columnas',
                'copy': '<i class="fa fa-files-o"></i>',
                'excel':'<i class="fa fa-file-excel-o"></i>',
                'pdf':'<i class="fa fa-file-pdf-o"></i>',
                'pageLength':{
                    '_': 'Ver %d',
                    -1: 'Ver todo'
                },
                'copyTitle': 'Copiado al portapapeles',
                'copySuccess': {
                    '_': '%d lineas copiadas',
                    1: '1 lineas copiadas'
                }
            }
    }
    
    return JsonResponse(data)

def calculate_amort(request):
    data = {
            'status':'no-respose'
        }
    if request.method == 'GET':
        tipo = request.GET.get('tipo')
        rate = float(request.GET.get('rate'))/100
        nper = int(request.GET.get('nper'))
        
        if tipo == 'cuota_normal':
            vp = float(request.GET.get('vp').replace(',',''))
            pago_mensual=int(npf.pmt(rate,nper,vp)*-1)
            data = {
                'cuota':pago_mensual
            }
        elif tipo == 'cuota_extra':
            total_credito = int(request.GET.get('totalamount').replace(',',''))
            pmt = int(request.GET.get('pmt').replace(',',''))
            valor_presente = int(npf.pv(rate,nper,pmt))*-1
            
            nper_extra = int(request.GET.get('nper_extra'))
            period_extra = int(request.GET.get('period_extra'))
            tasa_extra = rate * int(period_extra)
            saldo_extra = total_credito - valor_presente
            
            pago_mensual_extra=int(npf.pmt(tasa_extra,nper_extra,saldo_extra)*-1)
            data={
                'saldo_extra':saldo_extra,
                'cuota_extra':pago_mensual_extra
            }
    return JsonResponse(data)

@login_required
def start_impersonate(request, user_id):
    """
    Inicia impersonación: guarda usuario original en session y hace login con target user.
    Solo para superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para impersonar usuarios.')
        return redirect('/')

    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('/usersadmin')

    # Guardar usuario original
    request.session['impersonator_id'] = request.user.pk
    request.session['impersonator_username'] = request.user.username
    
    # Login como el usuario target
    if not hasattr(target, 'backend'):
        target.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, target)

    # Registro en timeline
    try:
        Timeline.objects.create(
            user=target,
            action=f'Usuario impersonado por {request.session.get("impersonator_username")}',
            project=None,
            aplication='auth'
        )
    except:
        pass

    messages.success(
        request, 
        f'<div class="header">Impersonación activa</div>Ahora estás navegando como <strong>{target.username}</strong>'
    )
    return redirect('/')

@login_required
def stop_impersonate(request):
    """
    Termina impersonación: restaura el usuario original guardado en session.
    """
    orig_id = request.session.pop('impersonator_id', None)
    orig_username = request.session.pop('impersonator_username', None)
    
    if not orig_id:
        messages.error(request, 'No hay sesión de impersonación activa.')
        return redirect('/')

    try:
        original = User.objects.get(pk=orig_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuario original no encontrado.')
        return redirect('/')

    if not hasattr(original, 'backend'):
        original.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, original)

    # Registro en timeline
    try:
        Timeline.objects.create(
            user=original,
            action=f'Finalizó impersonación de usuario',
            project=None,
            aplication='auth'
        )
    except:
        pass

    messages.success(
        request,
        f'<div class="header">Impersonación finalizada</div>Has regresado a tu usuario <strong>{orig_username}</strong>'
    )
    return redirect('/usersadmin')

urlpattern = [
    path('landing',landing),
    path('',landing),
    path('ejemplo_pdf',render_pdf_view),
    path('action_history',history_actions),
    path('usersadmin',users_admin),
    path('impersonate/start/<int:user_id>/', start_impersonate, name='start_impersonate'),
    path('impersonate/stop/', stop_impersonate, name='stop_impersonate'),
] + [
    path('ajax/getdatacountries',ajax_countries_data),
    path('ajax/datatable_spanish',spanish_datatables),
    path('ajax/amortizationcalc',calculate_amort),
    path('ajax/rol/<int:pk>',ajax_get_rol),
    path('roles/<int:pk>/', rol_form, name='rol_form'),
    path('roles/nuevo/', rol_form, name='rol_nuevo'),
]

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
from django.contrib.auth import views as auth_views
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import smtplib
import ssl
import socket
import traceback
from xhtml2pdf import pisa
import numpy_financial as npf
from dateutil.relativedelta import relativedelta
from mcd_site.forms import usersForm
from mcd_site.models import Perfil, Rol, Timeline, Projects, Permiso
from mcd_site.counter_utils import (
    build_contract_counter_state,
    build_receipt_counter_state,
    contract_preview,
    contract_rules_for_prefix,
    describe_contract_counter_change,
    describe_receipt_counter_change,
    get_or_create_contract_counter,
    get_or_create_receipt_counter,
    snapshot_contract_counter,
    snapshot_receipt_counter,
    validate_contract_counter_update,
    validate_receipt_counter_update,
)
from mcd_site.utils import JsonRender, link_callback, parse_semantic_date, passwordgenerate, send_email_template, project_permission, user_permission
from terceros.models import Collaborators


class PasswordResetConfirmWithMessages(auth_views.PasswordResetConfirmView):
    """
    Same behavior as Django's PasswordResetConfirmView, but surfaces validation errors
    via django.contrib.messages (helps when the template doesn't render field errors).
    """

    def form_invalid(self, form):
        for error in form.non_field_errors():
            messages.error(self.request, error)
        for field in form:
            for error in field.errors:
                messages.error(self.request, f'{field.label}: {error}')
        return super().form_invalid(form)


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
        if collab.birth_date and collab.birth_date.month == today.month:
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
            obj_profile = Perfil.objects.filter(usuario_id=user)
            profile0 = obj_profile.first()
            rols = profile0.rol.all().values_list('id') if profile0 else []
            projects = profile0.projects.all().values_list('name') if profile0 else []
            
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
                            
                username = username.lower().replace(" ","")
                # Create user without usable password; user will set it via link
                user = User.objects.create_user(username, email, None)
                
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

                protocol = 'https' if request.is_secure() else 'http'
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                set_password_path = reverse('auth_password_reset_confirm', args=[uid, token])
                set_password_url = f"{protocol}://{domain}{set_password_path}"

                email_message = f'''
                    <p style="margin:0 0 12px 0;">
                        Te damos la bienvenida a <strong>MacardyApp</strong>. Para activar tu acceso, crea tu contraseña desde el siguiente botón:
                    </p>

                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 16px 0 18px 0;">
                        <tr>
                            <td align="center" bgcolor="#003399" style="border-radius: 6px;">
                                <a href="{set_password_url}"
                                   style="display:inline-block;padding:12px 18px;font-family:Arial,Helvetica,sans-serif;font-size:16px;color:#ffffff;text-decoration:none;border-radius:6px;">
                                    Crear contraseña
                                </a>
                            </td>
                        </tr>
                    </table>

                    <p style="margin:0 0 10px 0;">
                        Usuario: <strong>{username}</strong>
                    </p>

                    <p style="margin:0;color:#666666;font-size:13px;line-height:1.4;">
                        Si no solicitaste este acceso, puedes ignorar este correo.
                    </p>
                '''
                
                email_context = {
                    'email_title': 'Activa tu cuenta',
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
                profile.identificacion = request.POST.get('user_id')
                profile.fecha_nacimiento = parse_semantic_date(birth_date,'date')
                
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

                if request.FILES.get('picture'):
                    profile.avatar = request.FILES.get('picture')

                profile.save()
                        
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


@login_required
def smtp_email_debug(request):
    """
    SMTP connectivity + send probe. Staff/superuser only.
    Does not return secrets; only booleans/lengths and safe config fields.
    """
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    if request.method != 'GET':
        return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)

    to = (request.GET.get('to') or '').strip() or (request.user.email or '').strip()
    if not to:
        return JsonResponse({'ok': False, 'error': 'missing_recipient'}, status=400)

    resend_key = (getattr(settings, 'RESEND_API_KEY', '') or '').strip()
    email_pw = (getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').strip()

    diag = {
        'ok': True,
        'email_backend': getattr(settings, 'EMAIL_BACKEND', ''),
        'email_host': getattr(settings, 'EMAIL_HOST', ''),
        'email_port': getattr(settings, 'EMAIL_PORT', None),
        'email_host_user': getattr(settings, 'EMAIL_HOST_USER', ''),
        'email_use_tls': getattr(settings, 'EMAIL_USE_TLS', None),
        'email_use_ssl': getattr(settings, 'EMAIL_USE_SSL', None),
        'default_from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
        'resend_api_key_set': bool(resend_key),
        'resend_api_key_len': len(resend_key),
        'email_host_password_len': len(email_pw),
        'recipient': to,
        'dns': {},
        'send': {},
    }

    host = getattr(settings, 'EMAIL_HOST', '') or 'smtp.resend.com'
    port = int(getattr(settings, 'EMAIL_PORT', 465) or 465)
    use_tls = bool(getattr(settings, 'EMAIL_USE_TLS', False))
    use_ssl = bool(getattr(settings, 'EMAIL_USE_SSL', False))
    user = getattr(settings, 'EMAIL_HOST_USER', '') or ''
    password = (getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').strip()

    for h in (host, 'google.com'):
        try:
            diag['dns'][h] = socket.getaddrinfo(h, None)[0][4][0]
        except Exception as e:
            diag['dns'][h] = f'FAILED: {type(e).__name__}: {e}'

    probe = (request.GET.get('probe') or 'send').strip().lower()
    if probe not in {'handshake', 'auth', 'send'}:
        probe = 'send'

    timeout = int(getattr(settings, 'EMAIL_TIMEOUT', 30) or 30)
    timeout = max(3, min(timeout, 20))

    smtp_diag = {'probe': probe, 'timeout_s': timeout, 'steps': []}

    conn = None
    try:
        if use_ssl and not use_tls:
            smtp_diag['steps'].append('connect_smtp_ssl')
            conn = smtplib.SMTP_SSL(host=host, port=port, timeout=timeout, context=ssl.create_default_context())
        else:
            smtp_diag['steps'].append('connect_smtp')
            conn = smtplib.SMTP(host=host, port=port, timeout=timeout)
            # Best-effort: make underlying socket timeouts explicit too
            if getattr(conn, 'sock', None):
                conn.sock.settimeout(timeout)

            if use_tls:
                smtp_diag['steps'].append('starttls')
                context = ssl.create_default_context()
                conn.starttls(context=context)
                if getattr(conn, 'sock', None):
                    conn.sock.settimeout(timeout)

        smtp_diag['steps'].append('ehlo')
        conn.ehlo()

        if probe in {'auth', 'send'}:
            smtp_diag['steps'].append('login')
            if not password:
                raise smtplib.SMTPException('missing_smtp_password (set RESEND_API_KEY or EMAIL_HOST_PASSWORD)')
            conn.login(user, password)

        if probe == 'send':
            smtp_diag['steps'].append('sendmail')
            msg = (
                'From: {}\r\n'
                'To: {}\r\n'
                'Subject: MacardyApp SMTP debug\r\n'
                '\r\n'
                'SMTP debug OK\r\n'
            ).format(getattr(settings, 'DEFAULT_FROM_EMAIL', ''), to)
            conn.sendmail(getattr(settings, 'DEFAULT_FROM_EMAIL', ''), [to], msg)

        smtp_diag['ok'] = True
        diag['smtp'] = smtp_diag
        diag['send'] = {'ok': True, 'via': 'smtplib', 'probe': probe}
    except Exception as e:
        diag['ok'] = False
        smtp_diag['ok'] = False
        smtp_diag['error_type'] = type(e).__name__
        smtp_diag['error'] = str(e)
        diag['smtp'] = smtp_diag
        diag['send'] = {
            'ok': False,
            'via': 'smtplib',
            'probe': probe,
            'error_type': type(e).__name__,
            'error': str(e),
        }
        if request.user.is_superuser and request.GET.get('verbose') == '1':
            diag['send']['traceback'] = traceback.format_exc()
        return JsonResponse(diag, status=500)
    finally:
        try:
            if conn is not None:
                conn.quit()
        except Exception:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass

    return JsonResponse(diag)


@login_required
@project_permission
@user_permission('configurar consecutivos')
def consecutivos(request, project):
    obj_project = Projects.objects.get(name=project)
    contract_state = build_contract_counter_state(obj_project)
    receipt_state = build_receipt_counter_state(obj_project)
    return render(request, 'consecutivos.html', {
        'project': obj_project,
        'contract_state': contract_state,
        'receipt_state': receipt_state,
    })


@login_required
@project_permission
@user_permission('configurar consecutivos')
def ajax_contract_counter_rules(request, project):
    obj_project = Projects.objects.get(name=project)
    use_prefix = request.GET.get('use_prefix') in ('true', '1', 'on', 'yes')
    prefix = request.GET.get('prefix', '')
    rules = contract_rules_for_prefix(obj_project, use_prefix, prefix)
    return JsonResponse({
        'status': 'success',
        **rules,
    })


@login_required
@project_permission
@user_permission('configurar consecutivos')
def ajax_save_consecutivos(request, project):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

    obj_project = Projects.objects.get(name=project)
    counter_type = (request.POST.get('counter_type') or '').strip()

    if counter_type == 'contratos':
        use_prefix = request.POST.get('use_prefix') in ('true', '1', 'on', 'yes')
        counter = get_or_create_contract_counter(obj_project)
        previous = snapshot_contract_counter(counter)
        result = validate_contract_counter_update(
            obj_project,
            use_prefix=use_prefix,
            prefix=request.POST.get('prefix', ''),
            next_value=request.POST.get('next_value'),
        )
        if isinstance(result, list):
            return JsonResponse({'status': 'error', 'errors': result}, status=400)

        counter.prefix = result['storage_prefix']
        counter.value = result['next_value']
        counter.save()

        Timeline.objects.create(
            user=request.user,
            project=obj_project,
            action=describe_contract_counter_change(obj_project, previous, result),
            aplication='Administración',
        )

        preview = contract_preview(
            result['use_prefix'],
            result['active_prefix'],
            result['next_value'],
        )
        return JsonResponse({
            'status': 'success',
            'message': 'Numeración de contratos actualizada.',
            'preview': preview,
            'prefix_locked': result['use_prefix'] and bool(result['active_prefix']),
        })

    if counter_type == 'recibos':
        counter = get_or_create_receipt_counter(obj_project)
        previous = snapshot_receipt_counter(counter)
        result = validate_receipt_counter_update(
            obj_project,
            next_value=request.POST.get('next_value'),
        )
        if isinstance(result, list):
            return JsonResponse({'status': 'error', 'errors': result}, status=400)

        counter.value = result['next_value']
        counter.save()

        Timeline.objects.create(
            user=request.user,
            project=obj_project,
            action=describe_receipt_counter_change(obj_project, previous, result),
            aplication='Administración',
        )
        return JsonResponse({
            'status': 'success',
            'message': 'Consecutivo de recibos actualizado.',
            'preview': str(result['next_value']),
        })

    return JsonResponse({'status': 'error', 'message': 'Tipo de consecutivo no válido.'}, status=400)


urlpattern = [
    path('landing',landing),
    path('',landing),
    path('ejemplo_pdf',render_pdf_view),
    path('action_history',history_actions),
    path('usersadmin',users_admin),
    path('__debug__/email/', smtp_email_debug, name='smtp_email_debug'),
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

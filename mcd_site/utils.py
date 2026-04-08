from functools import wraps
import os
import json
from webbrowser import get
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, resolve_url
from django.template.loader import get_template
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.models.fields.files import FileField, ImageField
from django.core.mail import EmailMultiAlternatives
from xhtml2pdf import pisa
from django.contrib.staticfiles import finders
import locale 
from datetime import datetime
from random import SystemRandom


locale.setlocale(locale.LC_ALL,'es_CO.UTF-8')


def passwordgenerate(length=8):
    values = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ<=>@#%&+"
    cryptogen = SystemRandom()
    p = ""

    while length > 0:
        p += cryptogen.choice(values)
        length -= 1

    return p
    
def searchkeyvalue(json_object,key_to_search,value_to_return,search_value):
    for dictionary in json_object:
        if dictionary.get(key_to_search) == search_value:
            return dictionary.get(value_to_return)
    return None

def numbers_names(numero):
        unidades={0:'',
                  1:'UN',
                  2:'DOS',
                  3:'TRES',
                  4:'CUATRO',
                  5:'CINCO',
                  6:'SEIS',
                  7:'SIETE',
                  8:'OCHO',
                  9:'NUEVE',
                 10:'DIEZ',
                 11:'ONCE',
                 12:'DOCE',
                 13:'TRECE',
                 14:'CATORCE',
                 15:'QUINCE',
                 16:'DIECISEIS',
                 17:'DIECISIETE',
                 18:'DIECIOCHO',
                 19:'DIECINUEVE'}
        decenas={20:('VEINTE','VEINTI'),
                 30:('TREINTA','TREINTA Y'),
                 40:('CUARENTA','CUARENTA Y'),
                 50:('CINCUENTA','CINCUENTA Y'),
                 60:('SESENTA','SESENTA Y'),
                 70:('SETENTA','SETENTA Y'),
                 80:('OCHENTA','OCHENTA Y'),
                 90:('NOVENTA','NOVENTA Y')}
        centenas={100:('CIEN','CIENTO'),
                 200:'DOSCIENTOS',
                 300:'TRESCIENTOS',
                 400:'CUATROCIENTOS',
                 500:'QUINIENTOS',
                 600:'SEISCIENTOS',
                 700:'SETECIENTOS',
                 800:'OCHOCIENTOS',
                 900:'NOVECIENTOS'}
        
        valor_letras=""
        millones=int(numero/1000000)
        numero-=(millones*1000000)
        miles=int(numero/1000)
        numero-=miles*1000
        cientos=int(numero)
        cifra=(millones,miles,cientos)
        
        index=1
        for valor in cifra:
            Cientos_valor=valor-valor%100
            Decenas_valor=valor%100
            if valor>0:
                #centenas
                if valor>=100:
                    if valor==100:
                        valor_letras+=centenas[Cientos_valor][0]
                    elif valor<200:
                        valor_letras+=centenas[Cientos_valor][1]
                    elif valor<1000:
                        valor_letras+=centenas[Cientos_valor]
                    if Decenas_valor>=20:
                        if Decenas_valor%10==0:
                            valor_letras+=' '+decenas[Decenas_valor][0]
                        else:
                            valor_letras+=' '+decenas[Decenas_valor-Decenas_valor%10][1]
                            valor_letras+=' '+unidades[Decenas_valor%10]
                    elif Decenas_valor<20 and Decenas_valor>0:
                        valor_letras+=' '+unidades[Decenas_valor]
                elif valor>=20:
                    if Decenas_valor>=20:
                        if Decenas_valor%10==0:
                            valor_letras+=' '+decenas[Decenas_valor][0]
                        else:
                            valor_letras+=' '+decenas[Decenas_valor-Decenas_valor%10][1]
                            valor_letras+=' '+unidades[Decenas_valor%10]
                    elif Decenas_valor<20:
                        valor_letras+=' '+unidades[Decenas_valor]
                elif valor>0:
                    valor_letras+=unidades[Decenas_valor]
                if index==1:
                    valor_letras+=' MILLONES '
                if index==2:
                    valor_letras+=' MIL '
                if index==3:
                    if valor==1:
                        valor_letras+=' PESO '
                    else:
                        valor_letras+=' PESOS '
            index+=1
            
        if miles==0 and cientos==0:
            valor_letras+='DE PESOS '
        elif miles!=0 and cientos==0:
            valor_letras+='PESOS '
        valor_letras+='M/CTE'    
        valor_letras.replace('VEINTI ','VEINTI')
        valor_letras.replace('  ',' ')
        
        return valor_letras

def link_callback(uri, rel):
    path=''
    if uri.startswith('/static'):   
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    elif uri.startswith('/media'):   
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    return path

def pdf_gen(template_path,context,filename,):
    # Create a Django response object, and specify content_type as pdf
    #response = HttpResponse(content_type='application/pdf')
    #response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)
    file_dir = settings.MEDIA_ROOT / f'tmp/{filename}'
    try:
        output_file = open(file_dir,"w+b")
    except FileNotFoundError:
        os.makedirs(settings.MEDIA_ROOT / 'tmp')
        output_file = open(file_dir,"w+b")
    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=output_file, link_callback=link_callback)
    # if error then show some funy view
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    
    output_url = settings.MEDIA_ROOT / f'tmp/{filename}'
   
    output = {
        'url':settings.MEDIA_URL + f'tmp/{filename}',
        'root':settings.MEDIA_ROOT / f'tmp/{filename}'
    }
   
    return output

from django.contrib import messages
from django.shortcuts import redirect
def user_permission(perms,raise_exception=True):
    
    def check_perms(user):
        if user.is_superuser:
            return True
        elif user.is_anonymous:
            return False
        if perms is not list: perm_list = (perms,) 
        else: perm_list = perms
        has_perms = user.user_profile.has_permissions(perm_list)
        if has_perms:
            return True
        if raise_exception:
            raise PermissionDenied
        return False
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not check_perms(request.user):
                perm_text = ', '.join(perms) if isinstance(perms, list) else perms
                messages.error(request, f'Permiso requerido: {perm_text}')
                return redirect('/')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator if raise_exception else user_passes_test(check_perms,login_url='/accounts/login')

def rol_permission(rols,raise_exception=True):
    
    def check(user):
        if user.is_superuser:
            return True
        elif user.is_anonymous:
            return False
        
        if rols is not list:
            perms = (rols,) 
        else: perms = rols
        
        has_perms = user.user_profile.has_permissions(perms)
        if has_perms:
            return True
        if raise_exception:
            raise PermissionDenied
        return False
    return user_passes_test(check,login_url='/accounts/login')

def project_permission(view_func):
    def check_perms(user,project):
        if user.is_superuser:
            return True
        elif user.is_anonymous:
            return False
        try:
            if user.user_profile.has_project(project):
                return True
        except:
            return False
        return False
    
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        project = kwargs.get('project')
        if check_perms(request.user,project):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view

def user_check_perms(request,perms,raise_exception=False):
    if request.user.is_superuser:
        return True
    elif request.user.is_anonymous:
        return False
    
    if perms is not list: perm_list = (perms,) 
    else: perm_list = perms
    has_perms = request.user.user_profile.has_permissions(perm_list)
    if has_perms:
        return True
    if raise_exception:
        raise PermissionDenied
    return False

class JsonRender():
    
    def __init__(self,queryset,reverse=False,query_functions=[],annotates=[]):
        self.queryset = queryset
        self.reverse = reverse
        self.query_functions = query_functions
        self.annotates = annotates
        
    
    def render(self):
        object_dict = list()
        if self.queryset.count() > 0:
            fields = [f for f in self.queryset[0]._meta._get_fields(reverse=self.reverse)]
        else: 
            fields = []
        for obj in self.queryset:
            item = {}
            for field in fields:
                field_value = eval("obj."+field.name)     
                if type(field) == ForeignKey:
                    field_value = self.ForeingKeyRender(field,field_value)
                elif type(field) == ManyToManyField:
                    field_value = 'ManytoManyField'
                elif type(field) == FileField or ImageField:
                    field_value = str(field_value)
                item[field.name] = field_value
            for func in self.query_functions:
                if func.endswith(')'): 
                    item[func.split('(')[0]] = eval('obj.'+func)
                else:
                    item[func] = eval('obj.'+func+'()')
            for anot in self.annotates:
                item[anot] = eval('obj.'+anot)
            object_dict.append(item)
        return object_dict

    def ForeingKeyRender(self,fk,queryset_item):
        query_dict = {}
        field_list = fk.related_model._meta._get_fields(reverse = self.reverse)
        for field in field_list:
            if queryset_item == None:
                field_value = None
            else:
                field_value = eval(f'queryset_item.{field.name}')
                if type(field) == ForeignKey:
                    field_value = self.ForeingKeyRender(field,field_value)
                elif type(field) == ManyToManyField:
                    field_value = 'ManytoManyField'
                elif type(field) == FileField or ImageField:
                    field_value = str(field_value)
            query_dict[field.name] = field_value
        return query_dict
    
def parse_semantic_date(date,output='date'):
    if output=='date':
        date_object = datetime.strptime(date, '%B %d, %Y')
        return date_object
    elif output == 'str':
        str_date = datetime.strftime(date, '%B %d, %Y')
        return str_date

def searchkeyvalue(json_object,key_to_search,value_to_return,search_value):
    for dictionary in json_object:
        if dictionary.get(key_to_search) == search_value:
            return dictionary.get(value_to_return)
    return None
    
class countries_data():
    
    def country(self,code):
        file_paises = open(settings.STATIC_ROOT /'json/countries.json',encoding="utf8")
        json_file = json.loads(file_paises.read().encode().decode('utf-8-sig'))
        name = searchkeyvalue(json_file['countries'],'id','name',code)
        
        return name
    
    def state(self,code):
        file_estados = open(settings.STATIC_ROOT/'json/states.json',encoding="utf8")
        json_file = json.loads(file_estados.read().encode().decode('utf-8-sig'))
        name = searchkeyvalue(json_file['states'],'id','name',code)
        
        return name
    
    def city(self,code):
        file_ciudades = open(settings.STATIC_ROOT/'json/cities.json',encoding="utf8")
        json_file = json.loads(file_ciudades.read().encode().decode('utf-8-sig'))
        name = searchkeyvalue(json_file['cities'],'id','name',code)
    
        return name

def send_email_template(subject:str,sent_to:list,template:str,template_context:dict):
    
    template=get_template(template)
    content=template.render(template_context)
    message=EmailMultiAlternatives(subject=subject,body='',
                                   from_email=settings.EMAIL_HOST_USER,to=sent_to)
    message.attach_alternative(content,'text/html')
    message.send()

def create_cartera_roles():
    from mcd_site.models import Rol, Permiso
    
    permisos = [
        "ver solicitudes de recibos",
        "validar solicitud recibo", 
        "autorizar condonacion de mora",
        "ver cartera comercial",
        "ver cartera administrativa",
        "ver comisiones de cartera",
        "ver abonos a capital", 
        "modificar parametros cartera",
        "pagar catch out"
    ]
    
    print("Creando permisos...")
    for perm in permisos:
        p, created = Permiso.objects.get_or_create(descripcion=perm)
        if created:
            print(f"✓ Permiso creado: {perm}")
        else:
            print(f"- Permiso existente: {perm}")
    
    print("\nCreando rol Gestor Cartera Comercial...")
    rol_comercial = Rol.objects.create(descripcion="Gestor de Cartera Comercial")
    comercial_perms = ["ver solicitudes de recibos", "ver cartera comercial", 
                      "ver comisiones de cartera", "ver abonos a capital"]
    rol_comercial.permisos.set(Permiso.objects.filter(descripcion__in=comercial_perms))
    print(f"✓ Rol creado con {len(comercial_perms)} permisos")
    
    print("\nCreando rol Gestor Cartera Administrativa...")
    rol_admin = Rol.objects.create(descripcion="Gestor de Cartera Administrativa")
    admin_perms = ["ver solicitudes de recibos", "ver cartera administrativa",
                  "ver comisiones de cartera", "ver abonos a capital"]
    rol_admin.permisos.set(Permiso.objects.filter(descripcion__in=admin_perms))
    print(f"✓ Rol creado con {len(admin_perms)} permisos")
    
    print("\nCreando rol Líder de Cartera...")
    rol_lider = Rol.objects.create(descripcion="Líder de Cartera")
    rol_lider.permisos.set(Permiso.objects.filter(descripcion__in=permisos))
    print(f"✓ Rol creado con {len(permisos)} permisos")
    
    print("\n🎉 Roles de cartera creados con éxito!")
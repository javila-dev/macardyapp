"""
Script para verificar permisos de usuario para acceder a fechas de entrega.
Ejecutar en Django shell:
    python manage.py shell < scripts/check_user_permissions.py

O manualmente:
    python manage.py shell
    >>> from django.contrib.auth.models import User
    >>> exec(open('scripts/check_user_permissions.py').read())
"""

from django.contrib.auth.models import User
from mcd_site.models import Perfil

def check_delivery_permissions(username):
    """
    Verifica si un usuario tiene los permisos necesarios para ver fechas de entrega.
    """
    print(f"\n{'='*60}")
    print(f"VERIFICACIÓN DE PERMISOS: {username}")
    print(f"{'='*60}\n")
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ ERROR: Usuario '{username}' no existe")
        return
    
    # Verificar si es superusuario
    if user.is_superuser:
        print("✅ Usuario es SUPERUSUARIO - Tiene todos los permisos")
        return
    
    # Verificar si tiene perfil
    try:
        perfil = user.user_profile
    except:
        print("❌ ERROR: Usuario no tiene perfil asociado")
        return
    
    print(f"👤 Nombre: {user.first_name} {user.last_name}")
    print(f"📧 Email: {user.email}")
    print(f"🔒 Activo: {'Sí' if user.is_active else 'No'}")
    print(f"\n{'='*60}")
    
    # Mostrar roles
    roles = perfil.rol.all()
    print(f"\n📋 ROLES ({roles.count()}):")
    if roles.exists():
        for rol in roles:
            print(f"   - {rol.descripcion}")
    else:
        print("   ⚠️  No tiene roles asignados")
    
    # Mostrar proyectos
    proyectos = perfil.projects.all()
    print(f"\n🏗️  PROYECTOS ({proyectos.count()}):")
    if proyectos.exists():
        for proyecto in proyectos:
            print(f"   - {proyecto.name_to_show} ({proyecto.name})")
    else:
        print("   ⚠️  No tiene proyectos asignados")
    
    # Obtener todos los permisos
    print(f"\n🔑 PERMISOS:")
    all_perms = perfil.all_permissions()
    
    if all_perms:
        print(f"   Total de permisos: {len(all_perms)}")
        print("\n   Permisos del usuario:")
        for perm in sorted(all_perms):
            print(f"      • {perm}")
    else:
        print("   ⚠️  No tiene permisos asignados")
    
    # Verificar permiso específico para fechas de entrega
    print(f"\n{'='*60}")
    print("VERIFICACIÓN ESPECÍFICA PARA FECHAS DE ENTREGA")
    print(f"{'='*60}\n")
    
    required_perms = [
        'ver entregas y escrituracion',
        'registrar entregas y escrituracion'
    ]
    
    for perm in required_perms:
        has_perm = perfil.has_permission(perm)
        status = "✅" if has_perm else "❌"
        print(f"{status} {perm}: {'SÍ tiene permiso' if has_perm else 'NO tiene permiso'}")
    
    # Verificar si tiene el permiso normalizado
    print(f"\n📊 ANÁLISIS DETALLADO:")
    normalized_user_perms = [p.lower().strip() for p in all_perms]
    
    for required_perm in required_perms:
        normalized_required = required_perm.lower().strip()
        
        print(f"\n   Buscando: '{normalized_required}'")
        
        # Buscar coincidencias parciales
        matches = [p for p in normalized_user_perms if normalized_required in p or p in normalized_required]
        
        if matches:
            print(f"   Coincidencias encontradas:")
            for match in matches:
                print(f"      • '{match}'")
        else:
            print(f"   ⚠️  No se encontraron coincidencias")
            print(f"   Permisos similares:")
            # Buscar permisos que contengan palabras clave
            keywords = ['entrega', 'escritura', 'escrituracion', 'delivery', 'deed']
            similar = [p for p in normalized_user_perms if any(kw in p for kw in keywords)]
            if similar:
                for sim in similar:
                    print(f"      • '{sim}'")
            else:
                print(f"      (ninguno)")
    
    print(f"\n{'='*60}")
    print("RESUMEN")
    print(f"{'='*60}\n")
    
    can_view = perfil.has_permission('ver entregas y escrituracion')
    can_register = perfil.has_permission('registrar entregas y escrituracion')
    
    if can_view:
        print("✅ El usuario PUEDE acceder al listado de fechas de entrega")
    else:
        print("❌ El usuario NO PUEDE acceder al listado de fechas de entrega")
        print("\n💡 SOLUCIÓN:")
        print("   1. Ir a /usersadmin")
        print("   2. Seleccionar el usuario")
        print("   3. Asignar un rol que tenga el permiso 'ver entregas y escrituracion'")
        print("   O agregar el permiso individual al perfil del usuario")
    
    if can_register:
        print("✅ El usuario PUEDE registrar fechas de entrega y escrituración")
    else:
        print("⚠️  El usuario NO PUEDE registrar fechas de entrega y escrituración")
    
    print("\n")


# Solicitar username
print("\n" + "="*60)
print("VERIFICADOR DE PERMISOS - FECHAS DE ENTREGA")
print("="*60)
print("\nIngresa el username del usuario a verificar:")
print("Ejemplo: sgomez")
print("\nO ejecuta directamente:")
print(">>> check_delivery_permissions('sgomez')")
print("\n")

# Si quieres verificar un usuario específico, descomenta y cambia el username:
# check_delivery_permissions('sgomez')

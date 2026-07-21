from django.db import migrations


def create_permission(apps, schema_editor):
    Permiso = apps.get_model('mcd_site', 'Permiso')
    Permiso.objects.get_or_create(descripcion='borrar venta')


def remove_permission(apps, schema_editor):
    Permiso = apps.get_model('mcd_site', 'Permiso')
    Permiso.objects.filter(descripcion='borrar venta').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mcd_site', '0015_permiso_configurar_consecutivos'),
    ]

    operations = [
        migrations.RunPython(create_permission, remove_permission),
    ]

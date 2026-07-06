from django.db import migrations


def create_permission(apps, schema_editor):
    Permiso = apps.get_model('mcd_site', 'Permiso')
    Permiso.objects.get_or_create(descripcion='configurar consecutivos')


def remove_permission(apps, schema_editor):
    Permiso = apps.get_model('mcd_site', 'Permiso')
    Permiso.objects.filter(descripcion='configurar consecutivos').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mcd_site', '0014_auto_20250721_2126'),
    ]

    operations = [
        migrations.RunPython(create_permission, remove_permission),
    ]

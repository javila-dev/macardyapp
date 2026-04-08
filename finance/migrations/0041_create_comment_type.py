from django.db import migrations, models

def create_initial_comment_types(apps, schema_editor):
    CommentType = apps.get_model('finance', 'CommentType')
    
    types = [
        {'name': 'Cobro', 'description': 'Comentarios de gestión de cobro'},
        {'name': 'Saludo', 'description': 'Comentarios de saludo y contacto'},
        {'name': 'Otro', 'description': 'Otros tipos de comentarios'},
    ]
    
    for type_data in types:
        CommentType.objects.get_or_create(
            name=type_data['name'],
            defaults={'description': type_data['description']}
        )

def reverse_comment_types(apps, schema_editor):
    CommentType = apps.get_model('finance', 'CommentType')
    CommentType.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0040_auto_20250708_0927'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommentType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='Descripción')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Tipo de comentario',
                'verbose_name_plural': 'Tipos de comentarios',
                'ordering': ['name'],
            },
        ),
        migrations.RunPython(create_initial_comment_types, reverse_comment_types),
    ]
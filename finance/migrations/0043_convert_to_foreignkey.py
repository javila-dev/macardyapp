from django.db import migrations, models
import django.db.models.deletion

def map_numbers_to_fk(apps, schema_editor):
    Collection_feed = apps.get_model('finance', 'Collection_feed')
    CommentType = apps.get_model('finance', 'CommentType')
    
    # Obtener IDs de los tipos
    cobro_id = CommentType.objects.get(name='Cobro').id
    saludo_id = CommentType.objects.get(name='Saludo').id
    otro_id = CommentType.objects.get(name='Otro').id
    
    # Mapear números a IDs
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type_new_id = %s WHERE comment_type = '1'",
            [cobro_id]
        )
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type_new_id = %s WHERE comment_type = '2'",
            [saludo_id]
        )
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type_new_id = %s WHERE comment_type = '3'",
            [otro_id]
        )

class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0042_convert_strings_to_numbers'),
    ]

    operations = [
        # Agregar nuevo campo ForeignKey
        migrations.AddField(
            model_name='collection_feed',
            name='comment_type_new',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='finance.commenttype',
                verbose_name='Tipo de seguimiento'
            ),
        ),
        
        # Mapear datos
        migrations.RunPython(map_numbers_to_fk),
        
        # Eliminar campo viejo
        migrations.RemoveField(
            model_name='collection_feed',
            name='comment_type',
        ),
        
        # Renombrar campo nuevo
        migrations.RenameField(
            model_name='collection_feed',
            old_name='comment_type_new',
            new_name='comment_type',
        ),
        
        # Hacer campo obligatorio
        migrations.AlterField(
            model_name='collection_feed',
            name='comment_type',
            field=models.ForeignKey(
                limit_choices_to={'is_active': True},
                on_delete=django.db.models.deletion.PROTECT,
                to='finance.commenttype',
                verbose_name='Tipo de seguimiento'
            ),
        ),
    ]
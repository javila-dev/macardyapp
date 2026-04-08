from django.db import migrations

def convert_strings_to_numbers(apps, schema_editor):
    Collection_feed = apps.get_model('finance', 'Collection_feed')
    
    # Mapear strings a números
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type = '1' WHERE comment_type = 'Cobro'"
        )
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type = '2' WHERE comment_type = 'Saludo'"
        )
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type = '3' WHERE comment_type NOT IN ('1', '2')"
        )

def reverse_convert_strings_to_numbers(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type = 'Cobro' WHERE comment_type = '1'"
        )
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type = 'Saludo' WHERE comment_type = '2'"
        )
        cursor.execute(
            "UPDATE finance_collection_feed SET comment_type = 'Otro' WHERE comment_type = '3'"
        )

class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0041_create_comment_type'),
    ]

    operations = [
        migrations.RunPython(convert_strings_to_numbers, reverse_convert_strings_to_numbers),
    ]
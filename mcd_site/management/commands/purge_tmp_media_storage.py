from datetime import timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Borra archivos temporales del prefijo tmp/ en el storage remoto.'

    def add_arguments(self, parser):
        parser.add_argument('--older-than-hours', type=int, default=24, help='Edad minima en horas para borrar archivos tmp.')
        parser.add_argument('--dry-run', action='store_true', help='Solo informa que archivos borraria.')

    def handle(self, *args, **options):
        if not hasattr(default_storage, 'bucket'):
            self.stdout.write(self.style.ERROR('El storage actual no expone bucket; usa lifecycle en MinIO o ejecuta con S3 activo.'))
            return

        dry_run = options['dry_run']
        threshold = timezone.now() - timedelta(hours=options['older_than_hours'])
        prefix = settings.TMP_MEDIA_PREFIX
        deleted = 0

        for obj in default_storage.bucket.objects.filter(Prefix=prefix):
            if obj.key.endswith('/'):
                continue
            if obj.last_modified <= threshold:
                if dry_run:
                    self.stdout.write(f'[dry-run] borrar {obj.key}')
                else:
                    obj.delete()
                    self.stdout.write(self.style.SUCCESS(f'Borrado: {obj.key}'))
                deleted += 1

        self.stdout.write(self.style.SUCCESS(f'Objetos tmp procesados: {deleted}'))

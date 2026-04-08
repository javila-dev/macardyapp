from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import FileField, ImageField


class Command(BaseCommand):
    help = 'Sincroniza los archivos persistentes existentes en disco local hacia el storage configurado (MinIO/S3).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo informa lo que subiria sin copiar archivos.')
        parser.add_argument('--skip-existing', action='store_true', help='Omite archivos que ya existan en el bucket.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']
        local_root = Path(settings.LOCAL_MEDIA_ROOT)
        scanned = copied = skipped = missing = errors = 0
        field_types = (FileField, ImageField)

        for model in apps.get_models():
            file_fields = [field for field in model._meta.get_fields() if isinstance(field, field_types)]
            if not file_fields:
                continue

            for instance in model.objects.all().iterator():
                for field in file_fields:
                    field_file = getattr(instance, field.name, None)
                    if not field_file or not getattr(field_file, 'name', ''):
                        continue

                    name = field_file.name.replace('\\', '/').lstrip('/')
                    if name.startswith('tmp/'):
                        continue

                    scanned += 1
                    local_path = local_root / name
                    if not local_path.exists():
                        missing += 1
                        self.stdout.write(self.style.WARNING(f'No existe localmente: {model.__name__}.{field.name} -> {name}'))
                        continue

                    try:
                        exists_remote = default_storage.exists(name)
                    except Exception as exc:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f'Error verificando {name}: {exc}'))
                        continue

                    if exists_remote and skip_existing:
                        skipped += 1
                        continue

                    if dry_run:
                        copied += 1
                        self.stdout.write(f'[dry-run] subir {name}')
                        continue

                    try:
                        with local_path.open('rb') as fh:
                            default_storage.save(name, File(fh))
                        copied += 1
                        self.stdout.write(self.style.SUCCESS(f'Subido: {name}'))
                    except Exception as exc:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f'Error subiendo {name}: {exc}'))

        summary = (
            f'Revisados: {scanned} | Subidos: {copied} | Omitidos: {skipped} | '
            f'Faltantes: {missing} | Errores: {errors}'
        )
        if errors:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

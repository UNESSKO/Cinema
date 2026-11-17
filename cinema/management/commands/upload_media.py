from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Upload local media to Vercel Blob, preserving database paths.'
    def handle(self, *args, **options):
        if not settings.STORAGES['default']['BACKEND'] == 'cinema.storage.VercelBlobStorage':
            raise CommandError('Set BLOB_READ_WRITE_TOKEN in .env first.')
        count = 0
        for path in (settings.BASE_DIR / 'media').rglob('*'):
            if not path.is_file():
                continue
            name = path.relative_to(settings.BASE_DIR / 'media').as_posix()
            if default_storage.exists(name):
                continue
            with path.open('rb') as source:
                saved = default_storage.save(name, File(source))
            if saved != name:
                raise CommandError('Unexpected object name: ' + saved)
            count += 1
        self.stdout.write(f'Uploaded {count} files')

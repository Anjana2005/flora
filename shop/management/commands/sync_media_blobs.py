from django.core.management.base import BaseCommand

from shop.media_storage import sync_media_dir_to_db


class Command(BaseCommand):
    help = 'Import MEDIA_ROOT files into MediaBlob (Postgres) for durable image hosting'

    def handle(self, *args, **options):
        count = sync_media_dir_to_db()
        self.stdout.write(self.style.SUCCESS(f'Synced {count} media file(s) into database'))

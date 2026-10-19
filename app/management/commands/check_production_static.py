from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify production static assets resolve through the manifest."

    assets = ("css/theme.css", "img/main.jpg")

    def handle(self, *args, **options):
        if settings.DEBUG:
            raise CommandError("Run this check with DEBUG=False.")

        for asset in self.assets:
            try:
                stored_name = staticfiles_storage.stored_name(asset)
                asset_url = staticfiles_storage.url(asset)
            except ValueError as error:
                raise CommandError(
                    f"Static asset {asset!r} is missing from the manifest. "
                    "Run collectstatic before this check."
                ) from error

            collected_path = Path(settings.STATIC_ROOT, *stored_name.split("/"))
            if not collected_path.is_file():
                raise CommandError(
                    f"Manifest target for {asset!r} does not exist: "
                    f"{collected_path}. Run collectstatic before this check."
                )

            self.stdout.write(f"{asset} -> {asset_url}")

        self.stdout.write(self.style.SUCCESS("Production static assets verified."))

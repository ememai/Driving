import json
import os

from django.core.management.base import BaseCommand, CommandError
from app.models import UserProfile  # adjust the import if your model is in a different app

class Command(BaseCommand):
    help = 'Loads user data from a JSON fixture using update_or_create'

    def add_arguments(self, parser):
        parser.add_argument(
            'fixture',
            type=str,
            help='The path to the JSON fixture file containing the data'
        )

    def handle(self, *args, **options):
        fixture_path = options['fixture']

        if not os.path.exists(fixture_path):
            raise CommandError(f"File '{fixture_path}' does not exist.")

        try:
            with open(fixture_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Error parsing JSON: {e}")

        count = 0

        for entry in data:
            # This example assumes your fixture follows the Django serialization format:
            # {
            #     "model": "app.userprofile",
            #     "pk": <primary_key>,
            #     "fields": {
            #         "name": "Mwami",
            #         "other_field": "value",
            #         ...
            #     }
            # }
            if entry.get("model") != "app.userprofile":
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping entry for model {entry.get('model')}"
                    )
                )
                continue

            fields = entry.get("fields", {})
            name = fields.get("name")
            if not name:
                self.stdout.write(
                    self.style.WARNING("Skipping entry with no 'name' field.")
                )
                continue

            # Use update_or_create with the unique field (name) and any additional defaults
            obj, created = UserProfile.objects.update_or_create(
                name=name,  # lookup by the unique field
                defaults=fields  # update all fields provided in the fixture
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {name}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Updated: {name}"))

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {count} entries."))

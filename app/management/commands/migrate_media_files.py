import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from app.models import RoadSign, UserProfile
from django.core.files.base import ContentFile
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate media files from GitHub repo to persistent volume'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('Starting media migration...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be modified'))
        
        # Migrate road signs
        self.migrate_road_signs(dry_run)
        
        # Migrate profile pictures
        self.migrate_profile_pictures(dry_run)
        
        self.stdout.write(self.style.SUCCESS('Media migration completed!'))

    def migrate_road_signs(self, dry_run=False):
        """Migrate road sign images from repo to volume"""
        self.stdout.write('Migrating road signs...')
        
        road_signs = RoadSign.objects.filter(sign_image__isnull=False)
        migrated = 0
        failed = 0
        
        for sign in road_signs:
            try:
                # Get the filename from the database
                filename = sign.sign_image.name
                
                # Check if file already exists in volume
                full_path = os.path.join(settings.MEDIA_ROOT, filename)
                if os.path.exists(full_path):
                    self.stdout.write(f'  ✓ {filename} already exists')
                    migrated += 1
                    continue
                
                # URL-encode the filename to handle spaces and special characters
                # Split path and encode each part separately
                path_parts = filename.split('/')
                encoded_parts = [urllib.parse.quote(part, safe='') for part in path_parts]
                encoded_filename = '/'.join(encoded_parts)
                
                # Try to fetch from GitHub raw content
                github_url = f"https://raw.githubusercontent.com/ememai/Driving/main/{encoded_filename}"
                
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would migrate: {filename}')
                    migrated += 1
                    continue
                
                try:
                    # Download file from GitHub
                    with urllib.request.urlopen(github_url) as response:
                        file_content = response.read()
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    # Write to volume
                    with open(full_path, 'wb') as f:
                        f.write(file_content)
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename}'))
                    migrated += 1
                
                except urllib.error.HTTPError as e:
                    self.stdout.write(self.style.WARNING(f'  ⊘ Not found on GitHub: {filename}'))
                    failed += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error migrating {filename}: {str(e)}'))
                failed += 1
        
        self.stdout.write(f'Road signs: {migrated} migrated, {failed} failed')

    def migrate_profile_pictures(self, dry_run=False):
        """Migrate user profile pictures from repo to volume"""
        self.stdout.write('Migrating profile pictures...')
        
        users = UserProfile.objects.filter(profile_picture__isnull=False).exclude(profile_picture='')
        migrated = 0
        failed = 0
        
        for user in users:
            try:
                filename = user.profile_picture.name
                
                # Skip default avatar
                if 'avatar.png' in filename:
                    continue
                
                # Check if file already exists
                full_path = os.path.join(settings.MEDIA_ROOT, filename)
                if os.path.exists(full_path):
                    self.stdout.write(f'  ✓ {filename} already exists')
                    migrated += 1
                    continue
                
                # URL-encode the filename
                path_parts = filename.split('/')
                encoded_parts = [urllib.parse.quote(part, safe='') for part in path_parts]
                encoded_filename = '/'.join(encoded_parts)
                
                github_url = f"https://raw.githubusercontent.com/ememai/Driving/main/{encoded_filename}"
                
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would migrate: {filename}')
                    migrated += 1
                    continue
                
                try:
                    with urllib.request.urlopen(github_url) as response:
                        file_content = response.read()
                    
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, 'wb') as f:
                        f.write(file_content)
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename}'))
                    migrated += 1
                
                except urllib.error.HTTPError:
                    self.stdout.write(self.style.WARNING(f'  ⊘ Not found on GitHub: {filename}'))
                    failed += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                failed += 1
        
        self.stdout.write(f'Profile pictures: {migrated} migrated, {failed} failed')

import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from app.models import RoadSign, UserProfile
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

    def try_download_from_github(self, filename):
        """Try to download a file from GitHub with various filename variations"""
        variations = self.get_filename_variations(filename)
        
        for variation in variations:
            try:
                # URL-encode the filename
                path_parts = variation.split('/')
                encoded_parts = [urllib.parse.quote(part, safe='') for part in path_parts]
                encoded_filename = '/'.join(encoded_parts)
                
                github_url = f"https://raw.githubusercontent.com/ememai/Driving/main/{encoded_filename}"
                
                with urllib.request.urlopen(github_url, timeout=5) as response:
                    return response.read(), variation
            except (urllib.error.HTTPError, urllib.error.URLError, Exception):
                continue
        
        return None, None

    def get_filename_variations(self, filename):
        """Generate filename variations to try"""
        variations = [filename]  # Try original first
        
        # Try without spaces
        if ' ' in filename:
            variations.append(filename.replace(' ', '_'))
            variations.append(filename.replace(' ', ''))
        
        # Try different extensions
        base, ext = os.path.splitext(filename)
        if ext.lower() in ['.jpg', '.jpeg']:
            variations.append(base + '.png')
            variations.append(base + '.jpeg' if ext.lower() == '.jpg' else base + '.jpg')
        elif ext.lower() == '.png':
            variations.append(base + '.jpg')
            variations.append(base + '.jpeg')
        
        # Try without path prefix variations
        if '/' in filename:
            just_name = os.path.basename(filename)
            variations.append(just_name)
            variations.extend(self.get_filename_variations(just_name))
        
        return list(dict.fromkeys(variations))  # Remove duplicates while preserving order

    def migrate_road_signs(self, dry_run=False):
        """Migrate road sign images from repo to volume"""
        self.stdout.write('Migrating road signs...')
        
        road_signs = RoadSign.objects.filter(sign_image__isnull=False)
        migrated = 0
        failed = 0
        
        for sign in road_signs:
            try:
                filename = sign.sign_image.name
                
                # Check if file already exists in volume
                full_path = os.path.join(settings.MEDIA_ROOT, filename)
                if os.path.exists(full_path):
                    self.stdout.write(f'  ✓ {filename} already exists')
                    migrated += 1
                    continue
                
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would try to migrate: {filename}')
                    migrated += 1
                    continue
                
                # Try to download with variations
                file_content, found_as = self.try_download_from_github(filename)
                
                if file_content:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    # Write to volume
                    with open(full_path, 'wb') as f:
                        f.write(file_content)
                    
                    if found_as != filename:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename} (found as: {found_as})'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename}'))
                    migrated += 1
                else:
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
                
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would try to migrate: {filename}')
                    migrated += 1
                    continue
                
                # Try to download with variations
                file_content, found_as = self.try_download_from_github(filename)
                
                if file_content:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, 'wb') as f:
                        f.write(file_content)
                    
                    if found_as != filename:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename} (found as: {found_as})'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename}'))
                    migrated += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  ⊘ Not found on GitHub: {filename}'))
                    failed += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                failed += 1
        
        self.stdout.write(f'Profile pictures: {migrated} migrated, {failed} failed')

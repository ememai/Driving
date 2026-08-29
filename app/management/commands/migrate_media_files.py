import os
import logging
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from app.models import RoadSign, UserProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate media files from local storage to persistent volume'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )
        parser.add_argument(
            '--source-dir',
            type=str,
            default='/app/media_backup',
            help='Source directory to migrate from (default: /app/media_backup)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        source_dir = options.get('source_dir', '/app/media_backup')
        
        self.stdout.write(self.style.SUCCESS('Starting media migration from local storage...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be modified'))
        
        self.stdout.write(f'Source directory: {source_dir}')
        self.stdout.write(f'Target directory: {settings.MEDIA_ROOT}')
        
        # Check if source exists
        if not os.path.exists(source_dir):
            self.stdout.write(self.style.WARNING(f'Source directory does not exist: {source_dir}'))
            self.stdout.write('No files to migrate.')
            return
        
        # Migrate road signs
        self.migrate_road_signs(source_dir, dry_run)
        
        # Migrate profile pictures
        self.migrate_profile_pictures(source_dir, dry_run)
        
        self.stdout.write(self.style.SUCCESS('Media migration completed!'))

    def find_file_in_source(self, filename, source_dir):
        """Try to find a file in the source directory"""
        # Try exact match first
        full_path = os.path.join(source_dir, filename)
        if os.path.exists(full_path):
            return full_path
        
        # Try just the basename
        basename = os.path.basename(filename)
        basename_path = os.path.join(source_dir, basename)
        if os.path.exists(basename_path):
            return basename_path
        
        # Try without extension variations
        base, ext = os.path.splitext(filename)
        for alt_ext in ['.jpg', '.jpeg', '.png', '.gif']:
            alt_path = os.path.join(source_dir, os.path.basename(base) + alt_ext)
            if os.path.exists(alt_path):
                return alt_path
        
        return None

    def migrate_road_signs(self, source_dir, dry_run=False):
        """Migrate road sign images from source to volume"""
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
                
                # Try to find file in source
                source_path = self.find_file_in_source(filename, source_dir)
                
                if not source_path:
                    self.stdout.write(self.style.WARNING(f'  ⊘ Not found in source: {filename}'))
                    failed += 1
                    continue
                
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would copy: {filename}')
                    migrated += 1
                    continue
                
                # Ensure target directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, full_path)
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename}'))
                migrated += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error migrating {filename}: {str(e)}'))
                failed += 1
        
        self.stdout.write(f'Road signs: {migrated} migrated, {failed} failed')

    def migrate_profile_pictures(self, source_dir, dry_run=False):
        """Migrate user profile pictures from source to volume"""
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
                
                # Try to find file in source
                source_path = self.find_file_in_source(filename, source_dir)
                
                if not source_path:
                    self.stdout.write(self.style.WARNING(f'  ⊘ Not found in source: {filename}'))
                    failed += 1
                    continue
                
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would copy: {filename}')
                    migrated += 1
                    continue
                
                # Ensure target directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, full_path)
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename}'))
                migrated += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                failed += 1
        
        self.stdout.write(f'Profile pictures: {migrated} migrated, {failed} failed')

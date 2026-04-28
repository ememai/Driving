import os
import logging
import mysql.connector
from django.core.management.base import BaseCommand
from django.conf import settings
from app.models import RoadSign, UserProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate media files from remote MySQL database to persistent volume'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            default='6639-197-157-135-123.ngrok-free.app',
            help='MySQL host (default: ngrok tunnel)',
        )
        parser.add_argument(
            '--port',
            type=int,
            default=443,
            help='MySQL port (default: 443 for ngrok)',
        )
        parser.add_argument(
            '--user',
            type=str,
            default='root',
            help='MySQL user',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='ememai',
            help='MySQL password',
        )
        parser.add_argument(
            '--database',
            type=str,
            default='kds',
            help='MySQL database name',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        user = options['user']
        password = options['password']
        database = options['database']
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('Starting media migration from MySQL...'))
        self.stdout.write(f'Connecting to {host}:{port}/{database}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be modified'))
        
        try:
            # Connect to MySQL
            connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                ssl_disabled=False,
                autocommit=True
            )
            
            self.stdout.write(self.style.SUCCESS('✓ Connected to MySQL'))
            
            # Migrate road signs
            self.migrate_road_signs_from_mysql(connection, dry_run)
            
            connection.close()
            self.stdout.write(self.style.SUCCESS('Media migration completed!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Connection failed: {str(e)}'))
            self.stdout.write('Make sure ngrok tunnel is running and credentials are correct.')

    def migrate_road_signs_from_mysql(self, connection, dry_run=False):
        """Migrate road sign images from MySQL to volume"""
        self.stdout.write('Migrating road signs from MySQL...')
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Query all road signs with image paths
            cursor.execute('SELECT id, sign_image FROM app_roadsign WHERE sign_image IS NOT NULL AND sign_image != ""')
            road_signs = cursor.fetchall()
            
            self.stdout.write(f'Found {len(road_signs)} road signs in database')
            
            migrated = 0
            failed = 0
            
            for sign in road_signs:
                try:
                    filename = sign['sign_image']
                    sign_id = sign['id']
                    
                    # Check if file already exists in volume
                    full_path = os.path.join(settings.MEDIA_ROOT, filename)
                    if os.path.exists(full_path):
                        self.stdout.write(f'  ✓ {filename} already exists')
                        migrated += 1
                        continue
                    
                    # Query for the actual file data
                    cursor.execute(
                        'SELECT sign_image FROM app_roadsign WHERE id = %s',
                        (sign_id,)
                    )
                    result = cursor.fetchone()
                    
                    if not result or not result['sign_image']:
                        self.stdout.write(self.style.WARNING(f'  ⊘ No file data for: {filename}'))
                        failed += 1
                        continue
                    
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] Would save: {filename}')
                        migrated += 1
                        continue
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    # Write file
                    file_data = result['sign_image']
                    if isinstance(file_data, str):
                        file_data = file_data.encode('utf-8')
                    
                    with open(full_path, 'wb') as f:
                        f.write(file_data)
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Migrated: {filename}'))
                    migrated += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error migrating {filename}: {str(e)}'))
                    failed += 1
            
            self.stdout.write(f'Road signs: {migrated} migrated, {failed} failed')
            
        finally:
            cursor.close()

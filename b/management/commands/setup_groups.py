# b/management/commands/setup_groups.py



from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from b.models import *

class Command(BaseCommand):
    help = 'Setup user groups and permissions'
    
    def handle(self, *args, **options):
        # Create groups
        groups = ['HIM', 'NURSE', 'PHYSICIAN', 'PHARMACY', 'MLS', 'OPTOMETRIST']
        
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'Created group: {group_name}')
            else:
                self.stdout.write(f'Group already exists: {group_name}')
        
        self.stdout.write(self.style.SUCCESS('Groups setup completed!'))
# b/management/commands/cleanup_notifications.py


from django.core.management.base import BaseCommand
from django.utils import timezone
from b.models import Notification, PharmacyOrder
from datetime import timedelta

class Command(BaseCommand):
    help = 'Clean up old read notifications and mark pharmacy notifications as read when orders are dispensed'

    def handle(self, *args, **options):
        # Mark pharmacy notifications as read for dispensed orders
        dispensed_orders = PharmacyOrder.objects.filter(dispensed=True)
        count = 0
        
        for order in dispensed_orders:
            # Mark individual order notifications
            updated = Notification.objects.filter(
                link__icontains=f'/pharmacy/dispense/{order.id}/',
                is_read=False
            ).update(is_read=True)
            count += updated
            
            # Mark patient-level notifications
            if order.patient:
                updated = Notification.objects.filter(
                    link__icontains=f'/pharmacy/dispense-patient/{order.patient.id}/',
                    is_read=False
                ).update(is_read=True)
                count += updated
        
        self.stdout.write(self.style.SUCCESS(f'Marked {count} notifications as read'))
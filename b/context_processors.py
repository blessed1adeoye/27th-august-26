# b/context_processors.py

from .models import *
from django.db.models import Q, F
from datetime import date
from django.utils import timezone

def user_context(request):
    """Context processor to add user role and notifications to all templates"""
    context = {
        'role': None,
        'page': 'dashboard',
        'notification_count': 0,
        'notifications': [],
        'pending_count': 0,
        'pending_assignments': 0,
        'assigned_count': 0,
        'total_patients': 0,
        'today_patients': 0,
        'pending_nursing': 0,
        'pending_doctor': 0,
        'pending_pharmacy': 0,
        'pending_lab': 0,
        'pending_optician': 0,
        'patients': [],
        'orders': [],
        'tests': [],
        'assessments': [],
        'unassigned_patients': [],
        'nurses': [],
        'assigned_patients': [],
        'completed_today': 0,
        'low_stock_count': 0,
    }
    
    if request.user.is_authenticated:
        try:
            # Get user role
            user_profile = request.user.userprofile
            context['role'] = user_profile.role
            
            # Get notifications for the user
            context['notifications'] = Notification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:10]
            context['notification_count'] = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
            
            # Get role-specific counts and data
            if user_profile.role == 'HIM':
                from datetime import date
                context['total_patients'] = Patient.objects.count()
                context['today_patients'] = Patient.objects.filter(created_at__date=date.today()).count()
                context['pending_nursing'] = Patient.objects.filter(current_stage='REGISTERED').count()
                context['pending_doctor'] = Patient.objects.filter(current_stage='NURSING').count()
                context['pending_pharmacy'] = Patient.objects.filter(current_stage='PHARMACY').count()
                context['pending_lab'] = Patient.objects.filter(current_stage='LABORATORY').count()
                context['pending_optician'] = Patient.objects.filter(current_stage='OPTICIAN').count()
                
                # Count unassigned patients
                context['pending_assignments'] = Patient.objects.filter(
                    current_stage='REGISTERED'
                ).exclude(
                    id__in=NurseAssignment.objects.filter(is_active=True).values_list('patient_id', flat=True)
                ).count()
                
            elif user_profile.role == 'NURSE':
                # Get assigned patients
                context['assigned_patients'] = Patient.objects.filter(
                    nurseassignment__nurse=request.user,
                    nurseassignment__is_active=True
                )
                context['assigned_count'] = context['assigned_patients'].count()
                context['pending_count'] = context['assigned_patients'].filter(current_stage='REGISTERED').count()
                context['completed_today'] = context['assigned_patients'].filter(
                    current_stage='NURSING',
                    updated_at__date=timezone.now().date()
                ).count()
                
            elif user_profile.role == 'PHYSICIAN':
                # Get patients assigned to this physician (pending consultation)
                context['patients'] = Patient.objects.filter(
                    physicianassignment__physician=request.user,
                    physicianassignment__is_active=True,
                    current_stage='NURSING'
                )
                context['pending_count'] = context['patients'].count()
                
            elif user_profile.role == 'PHARMACY':
                # Get pending pharmacy orders
                context['orders'] = PharmacyOrder.objects.filter(dispensed=False)
                
                # ===== FIX: Count UNIQUE patients with pending orders =====
                # This counts each patient once, regardless of how many drugs they have
                context['pending_count'] = PharmacyOrder.objects.filter(
                    dispensed=False
                ).values('patient').distinct().count()
                
                # Get low stock count
                context['low_stock_count'] = Drug.objects.filter(
                    quantity__lte=F('reorder_level')
                ).count()
                
            elif user_profile.role == 'MLS':
                context['tests'] = LaboratoryTest.objects.filter(completed=False)
                context['pending_count'] = context['tests'].count()
                
            elif user_profile.role == 'OPTOMETRIST':
                context['assessments'] = OpticalAssessment.objects.filter(completed=False)
                context['pending_count'] = context['assessments'].count()
                
        except UserProfile.DoesNotExist:
            context['role'] = None
        except Exception as e:
            context['role'] = None
    
    return context
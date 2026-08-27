# b/views_admin.py
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
import io
from .models import *
from django.contrib.auth.decorators import login_required

# ============= ADMIN DASHBOARD =============

@staff_member_required
def admin_dashboard(request):
    """Super admin dashboard with charts"""
    context = {
        'page': 'admin_dashboard',
        'role': 'ADMIN',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/admin/dashboard.html', context)

# ============= ADMIN DASHBOARD DATA API =============

@staff_member_required
def admin_dashboard_data(request):
    """API endpoint for admin dashboard data"""
    # Patient statistics
    total_patients = Patient.objects.count()
    patients_by_gender = Patient.objects.values('gender').annotate(count=Count('id'))
    patients_by_stage = Patient.objects.values('current_stage').annotate(count=Count('id'))
    
    # Age distribution
    age_groups = {
        '0-18': 0,
        '19-30': 0,
        '31-50': 0,
        '51-70': 0,
        '70+': 0
    }
    today = timezone.now().date()
    for patient in Patient.objects.all():
        age = (today - patient.date_of_birth).days // 365
        if age <= 18:
            age_groups['0-18'] += 1
        elif age <= 30:
            age_groups['19-30'] += 1
        elif age <= 50:
            age_groups['31-50'] += 1
        elif age <= 70:
            age_groups['51-70'] += 1
        else:
            age_groups['70+'] += 1
    
    # Consultation statistics
    total_consultations = MedicalConsultation.objects.count()
    completed_consultations = MedicalConsultation.objects.filter(completed=True).count()
    referrals = {
        'pharmacy': MedicalConsultation.objects.filter(refer_to_pharmacy=True).count(),
        'laboratory': MedicalConsultation.objects.filter(refer_to_laboratory=True).count(),
        'optician': MedicalConsultation.objects.filter(refer_to_optician=True).count(),
        'specialist': MedicalConsultation.objects.filter(refer_to_specialist=True).count(),
    }
    
    # Lab test statistics
    total_lab_tests = LaboratoryTest.objects.count()
    completed_lab_tests = LaboratoryTest.objects.filter(completed=True).count()
    lab_results = {
        'positive': LaboratoryTest.objects.filter(malaria_parasite='POSITIVE').count(),
        'negative': LaboratoryTest.objects.filter(malaria_parasite='NEGATIVE').count(),
        'pending': LaboratoryTest.objects.filter(malaria_parasite='PENDING').count(),
    }
    
    # Optical statistics
    total_optical = OpticalAssessment.objects.count()
    completed_optical = OpticalAssessment.objects.filter(completed=True).count()
    walk_ins = OpticalAssessment.objects.filter(is_walk_in=True).count()
    glasses_allocated = OpticalAssessment.objects.aggregate(total=Sum('glasses_allocated'))['total'] or 0
    
    # Pharmacy statistics
    total_pharmacy_orders = PharmacyOrder.objects.count()
    dispensed_orders = PharmacyOrder.objects.filter(dispensed=True).count()
    total_drugs = Drug.objects.count()
    total_stock = Drug.objects.aggregate(total=Sum('quantity'))['total'] or 0
    
    # Drug category distribution
    drug_categories = Drug.objects.values('category').annotate(count=Count('id'))
    
    # Monthly trends (last 6 months)
    monthly_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=i*30)
        month_end = month_start + timedelta(days=30)
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'patients': Patient.objects.filter(created_at__gte=month_start, created_at__lt=month_end).count(),
            'consultations': MedicalConsultation.objects.filter(created_at__gte=month_start, created_at__lt=month_end).count(),
            'lab_tests': LaboratoryTest.objects.filter(created_at__gte=month_start, created_at__lt=month_end).count(),
        })
    monthly_data.reverse()
    
    return JsonResponse({
        'patients': {
            'total': total_patients,
            'by_gender': list(patients_by_gender),
            'by_stage': list(patients_by_stage),
            'age_groups': age_groups,
        },
        'consultations': {
            'total': total_consultations,
            'completed': completed_consultations,
            'referrals': referrals,
        },
        'lab_tests': {
            'total': total_lab_tests,
            'completed': completed_lab_tests,
            'results': lab_results,
        },
        'optical': {
            'total': total_optical,
            'completed': completed_optical,
            'walk_ins': walk_ins,
            'glasses_allocated': glasses_allocated,
        },
        'pharmacy': {
            'orders': total_pharmacy_orders,
            'dispensed': dispensed_orders,
            'drugs': total_drugs,
            'stock': total_stock,
        },
        'drug_categories': list(drug_categories),
        'monthly_trends': monthly_data,
    })

# ============= ADMIN EXPORT DATA - WITH TIMEZONE FIX =============

@staff_member_required
def admin_export_data(request):
    """Export all data to Excel"""
    try:
        import pandas as pd
        from openpyxl import Workbook
    except ImportError:
        return JsonResponse({'error': 'pandas or openpyxl not installed. Run: pip install pandas openpyxl'}, status=500)
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Helper function to convert queryset to dataframe with timezone fix
    def queryset_to_dataframe(queryset):
        data = list(queryset)
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # ===== FIX: Convert timezone-aware datetimes to naive =====
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns, UTC]' or str(df[col].dtype).startswith('datetime64'):
                # Convert to naive datetime (remove timezone)
                df[col] = pd.to_datetime(df[col]).dt.tz_localize(None)
            elif df[col].dtype == 'object':
                # Check if column contains datetime objects
                try:
                    sample = df[col].dropna()
                    if len(sample) > 0 and isinstance(sample.iloc[0], (datetime, pd.Timestamp)):
                        df[col] = pd.to_datetime(df[col]).dt.tz_localize(None)
                except:
                    pass
        
        return df
    
    # Export each table
    tables = {
        'Patients': Patient.objects.all().values(),
        'Nursing_Assessments': NursingAssessment.objects.all().values(),
        'Consultations': MedicalConsultation.objects.all().values(),
        'Lab_Tests': LaboratoryTest.objects.all().values(),
        'Optical_Assessments': OpticalAssessment.objects.all().values(),
        'Pharmacy_Orders': PharmacyOrder.objects.all().values(),
        'Drugs': Drug.objects.all().values(),
        'Dispensing': PharmacyDispensing.objects.all().values(),
        'Notifications': Notification.objects.all().values(),
        'User_Profiles': UserProfile.objects.all().values(),
    }
    
    for name, queryset in tables.items():
        df = queryset_to_dataframe(queryset)
        if not df.empty:
            # Clean column names for Excel
            df.columns = [c.replace('_', ' ').title() for c in df.columns]
            df.to_excel(writer, sheet_name=name[:31], index=False)
    
    writer.close()
    output.seek(0)
    
    # Create response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'corep_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response

# ============= OPTICIAN NOTIFICATION CHECK =============

@login_required
def optician_notification_check(request):
    """API endpoint for optician to check new assessments"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        if profile.role != 'OPTOMETRIST':
            return JsonResponse({'error': 'Not optician'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=401)
    
    # Only count UNVIEWED pending assessments
    pending_assessments = OpticalAssessment.objects.filter(
        completed=False,
        viewed_by_optician=False
    )
    
    # Count UNIQUE patients with unviewed pending assessments
    pending_patients = Patient.objects.filter(
        optical_assessments__completed=False,
        optical_assessments__viewed_by_optician=False
    ).distinct()
    patient_count = pending_patients.count()
    
    # Get count of assessments
    assessment_count = pending_assessments.count()
    
    # Get recent assessments (last 24 hours)
    from datetime import timedelta
    yesterday = timezone.now() - timedelta(days=1)
    recent_assessments = pending_assessments.filter(created_at__gt=yesterday)
    
    # Include assessment details with IDs
    recent_assessments_data = []
    for assessment in recent_assessments:
        recent_assessments_data.append({
            'id': assessment.id,
            'patient_name': assessment.patient.full_name,
            'patient_id': assessment.patient.id,
            'is_walk_in': assessment.is_walk_in,
            'created_at': assessment.created_at.isoformat(),
        })
    
    return JsonResponse({
        'count': assessment_count,
        'patient_count': patient_count,
        'recent_count': recent_assessments.count(),
        'has_new': recent_assessments.count() > 0,
        'recent_assessments': recent_assessments_data,
    })
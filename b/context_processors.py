# b/context_processors.py

from .models import *
from django.db.models import Q, F, Count
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
        'new_assignments': 0,
        'has_new_assignments': False,
        # MLS specific
        'pending_test_count': 0,
        'pending_patients': [],
        # Physician specific
        'doctor_patients': [],
        'lab_results_count': 0,
        'patients_with_lab_results': [],
        'optician_results_count': 0,
        'patients_with_optician_results': [],
        'lab_results': [],
        'optician_results': [],
        # Optician specific
        'pending_assessment_count': 0,
        'pending_patients_optical': [],
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
                assigned_patients = Patient.objects.filter(
                    nurseassignment__nurse=request.user,
                    nurseassignment__is_active=True
                )
                context['assigned_patients'] = assigned_patients
                context['assigned_count'] = assigned_patients.count()
                context['pending_count'] = assigned_patients.filter(current_stage='REGISTERED').count()
                context['completed_today'] = assigned_patients.filter(
                    current_stage='NURSING',
                    updated_at__date=timezone.now().date()
                ).count()
                
                # Check for new assignments since last session
                last_check = request.session.get('nurse_last_check', None)
                if last_check:
                    try:
                        from datetime import datetime
                        if isinstance(last_check, str):
                            last_check_dt = datetime.fromisoformat(last_check)
                        else:
                            last_check_dt = last_check
                        
                        new_assignments = NurseAssignment.objects.filter(
                            nurse=request.user,
                            assigned_at__gt=last_check_dt
                        ).count()
                        
                        context['new_assignments'] = new_assignments
                        context['has_new_assignments'] = new_assignments > 0
                    except Exception as e:
                        context['new_assignments'] = 0
                        context['has_new_assignments'] = False
                else:
                    total_assignments = NurseAssignment.objects.filter(
                        nurse=request.user,
                        is_active=True
                    ).count()
                    context['new_assignments'] = total_assignments
                    context['has_new_assignments'] = total_assignments > 0
                
                request.session['nurse_last_check'] = timezone.now().isoformat()
                
            elif user_profile.role == 'PHYSICIAN':
                # ===== DEBUG =====
                print("=" * 60)
                print("🔍 CONTEXT PROCESSOR - PHYSICIAN DEBUG")
                print(f"👤 User: {request.user.username}")
                
                # Get patients assigned to this physician
                assigned_patients = Patient.objects.filter(
                    physicianassignment__physician=request.user,
                    physicianassignment__is_active=True
                )
                print(f"📊 Assigned patients: {assigned_patients.count()}")
                
                # Patients pending consultation (NURSING stage)
                pending_patients = assigned_patients.filter(current_stage='NURSING')
                print(f"📊 Pending consultations: {pending_patients.count()}")
                
                # ===== LAB RESULTS =====
                # Only count UNVIEWED lab results
                unviewed_lab_tests_count = LaboratoryTest.objects.filter(
                    patient__in=assigned_patients,
                    completed=True,
                    viewed_by_physician=False
                ).count()
                print(f"📊 Unviewed Lab Results: {unviewed_lab_tests_count}")
                
                # Show all lab results
                all_lab = LaboratoryTest.objects.filter(patient__in=assigned_patients, completed=True)
                print(f"📊 Total completed lab tests: {all_lab.count()}")
                for l in all_lab[:5]:
                    print(f"   ID: {l.id} | Patient: {l.patient.full_name} | Viewed: {l.viewed_by_physician}")
                
                # ===== OPTICIAN RESULTS =====
                # Only count UNVIEWED optician results (viewed_by_physician=False)
                unviewed_optician_assessments_count = OpticalAssessment.objects.filter(
                    patient__in=assigned_patients,
                    completed=True,
                    viewed_by_physician=False
                ).count()
                print(f"📊 Unviewed Optician Results: {unviewed_optician_assessments_count}")
                
                # Show all optician results
                all_optician = OpticalAssessment.objects.filter(patient__in=assigned_patients, completed=True)
                print(f"📊 Total completed optician assessments: {all_optician.count()}")
                for o in all_optician[:5]:
                    print(f"   ID: {o.id} | Patient: {o.patient.full_name} | Viewed by Physician: {o.viewed_by_physician}")
                
                print("=" * 60)
                
                context['patients'] = pending_patients
                context['doctor_patients'] = assigned_patients
                context['pending_count'] = pending_patients.count()
                
                # Lab results - only unviewed counts for badge
                context['patients_with_lab_results'] = assigned_patients.filter(
                    lab_tests__completed=True,
                    lab_tests__viewed_by_physician=False
                ).distinct()
                context['lab_results_count'] = unviewed_lab_tests_count
                
                # Optician results - only unviewed counts for badge
                context['patients_with_optician_results'] = assigned_patients.filter(
                    optical_assessments__completed=True,
                    optical_assessments__viewed_by_physician=False
                ).distinct()
                context['optician_results_count'] = unviewed_optician_assessments_count
                
                # Get total counts for the results pages
                all_lab_tests = LaboratoryTest.objects.filter(
                    patient__in=assigned_patients,
                    completed=True
                )
                all_optician_assessments = OpticalAssessment.objects.filter(
                    patient__in=assigned_patients,
                    completed=True
                )
                
                context['total_lab_tests'] = all_lab_tests.count()
                context['total_optician_assessments'] = all_optician_assessments.count()
                
                # Build lab results data for the view
                lab_results_data = []
                for test in all_lab_tests:
                    lab_results_data.append({
                        'patient': test.patient,
                        'test': test,
                        'viewed': test.viewed_by_physician,
                    })
                context['lab_results'] = lab_results_data
                
                # Build optician results data for the view
                optician_results_data = []
                for assessment in all_optician_assessments:
                    optician_results_data.append({
                        'patient': assessment.patient,
                        'assessment': assessment,
                        'viewed': assessment.viewed_by_physician,
                    })
                context['optician_results'] = optician_results_data
                
            elif user_profile.role == 'PHARMACY':
                # Get pending pharmacy orders
                context['orders'] = PharmacyOrder.objects.filter(dispensed=False)
                
                # Count UNIQUE patients with pending orders
                context['pending_count'] = PharmacyOrder.objects.filter(
                    dispensed=False
                ).values('patient').distinct().count()
                
                # Get pending patients with their orders
                pending_patients = Patient.objects.filter(
                    pharmacy_orders__dispensed=False
                ).distinct().order_by('-created_at')
                context['pending_patients'] = pending_patients
                context['pending_patients_count'] = pending_patients.count()
                
                # Get low stock count
                context['low_stock_count'] = Drug.objects.filter(
                    quantity__lte=F('reorder_level')
                ).count()
                
            elif user_profile.role == 'MLS':
                # Count UNIQUE patients with pending tests
                pending_tests = LaboratoryTest.objects.filter(completed=False)
                pending_patients = Patient.objects.filter(
                    lab_tests__completed=False
                ).distinct().order_by('-created_at')
                
                pending_patients = pending_patients.annotate(
                    pending_test_count=Count('lab_tests', filter=Q(lab_tests__completed=False))
                )
                
                context['tests'] = pending_tests
                context['pending_patients'] = pending_patients
                context['pending_count'] = pending_patients.count()
                context['pending_test_count'] = pending_tests.count()
                
            elif user_profile.role == 'OPTOMETRIST':
                # ===== DEBUG =====
                print("=" * 60)
                print("🔍 CONTEXT PROCESSOR - OPTOMETRIST DEBUG")
                print(f"👤 User: {request.user.username}")
                
                # Check ALL assessments in the database
                all_assessments = OpticalAssessment.objects.all()
                print(f"📊 Total assessments in database: {all_assessments.count()}")
                
                for a in all_assessments:
                    print(f"   ID: {a.id} | Patient: {a.patient.full_name} | Completed: {a.completed} | Viewed by Optician: {a.viewed_by_optician}")
                
                # Count pending assessments (completed=False)
                pending_all = OpticalAssessment.objects.filter(completed=False)
                print(f"📊 Pending assessments (completed=False): {pending_all.count()}")
                
                for a in pending_all:
                    print(f"   ID: {a.id} | Patient: {a.patient.full_name} | Viewed by Optician: {a.viewed_by_optician}")
                
                # ===== FIX: Only count UNVIEWED pending assessments =====
                pending_assessments = OpticalAssessment.objects.filter(
                    completed=False,
                    viewed_by_optician=False
                )
                print(f"📊 UNVIEWED pending assessments (completed=False, viewed_by_optician=False): {pending_assessments.count()}")
                
                for a in pending_assessments:
                    print(f"   ID: {a.id} | Patient: {a.patient.full_name}")
                
                # Get unique patients with unviewed pending assessments
                pending_patients = Patient.objects.filter(
                    optical_assessments__completed=False,
                    optical_assessments__viewed_by_optician=False
                ).distinct().order_by('-created_at')
                
                patient_count = pending_patients.count()
                print(f"📊 Unique patients with unviewed pending assessments: {patient_count}")
                
                if patient_count > 0:
                    for p in pending_patients:
                        print(f"   Patient: {p.full_name} | Hospital: {p.hospital_number}")
                        for a in p.optical_assessments.filter(completed=False, viewed_by_optician=False):
                            print(f"      Assessment ID: {a.id} | Viewed: {a.viewed_by_optician}")
                
                print("=" * 60)
                
                # Annotate each patient with their pending assessment count
                pending_patients = pending_patients.annotate(
                    pending_assessment_count=Count('optical_assessments', filter=Q(
                        optical_assessments__completed=False,
                        optical_assessments__viewed_by_optician=False
                    ))
                )
                
                context['assessments'] = pending_assessments
                context['pending_patients_optical'] = pending_patients
                context['pending_count'] = pending_patients.count()
                context['pending_assessment_count'] = pending_assessments.count()
                
        except UserProfile.DoesNotExist:
            context['role'] = None
        except Exception as e:
            context['role'] = None
    
    return context
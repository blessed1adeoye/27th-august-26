# b/views


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta
import random
import string
from .models import *
from .forms import *
from django.contrib.auth.models import User, Group
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q, Sum
from django.db.models import F


# ========================= AUTHENTICATION SIGNALS =========================

def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('b:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'b:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'b/login.html')
    
    return render(request, 'b/login.html')

def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('b:home')

# ============= HELPERS =============
def generate_hospital_number():
    prefix = 'HIM'
    while True:
        suffix = ''.join(random.choices(string.digits, k=6))
        number = f"{prefix}{suffix}"
        if not Patient.objects.filter(hospital_number=number).exists():
            return number

def get_user_role(user):
    try:
        return user.userprofile.role
    except UserProfile.DoesNotExist:
        return None

def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('b:dashboard')
        return wrapper
    return decorator

# ============= AUTH VIEWS =============
def home(request):
    if request.user.is_authenticated:
        return redirect('b:dashboard')
    return render(request, 'b/home.html')

def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('b:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'b:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'b/login.html')
    
    return render(request, 'b/login.html')

def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('b:home')

@login_required
def dashboard(request):
    role = get_user_role(request.user)
    context = {
        'role': role,
        'page': 'dashboard',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    
    if role == 'HIM':
        context.update({
            'total_patients': Patient.objects.count(),
            'today_patients': Patient.objects.filter(created_at__date=date.today()).count(),
            'pending_nursing': Patient.objects.filter(current_stage='REGISTERED').count(),
            'pending_doctor': Patient.objects.filter(current_stage='NURSING').count(),
            'pending_pharmacy': Patient.objects.filter(current_stage='PHARMACY').count(),
            'pending_lab': Patient.objects.filter(current_stage='LABORATORY').count(),
            'pending_optician': Patient.objects.filter(current_stage='OPTICIAN').count(),
            'pending_assignments': Patient.objects.filter(current_stage='REGISTERED').count(),
        })
    elif role == 'NURSE':
        assigned_patients = Patient.objects.filter(
            nurseassignment__nurse=request.user,
            nurseassignment__is_active=True
        )
        context.update({
            'assigned_patients': assigned_patients,
            'assigned_count': assigned_patients.count(),
            'pending_count': assigned_patients.filter(current_stage='REGISTERED').count(),
            'completed_today': assigned_patients.filter(
                current_stage='NURSING',
                updated_at__date=date.today()
            ).count(),
        })
    elif role == 'PHYSICIAN':
        assigned_patients = Patient.objects.filter(
            physicianassignment__physician=request.user,
            physicianassignment__is_active=True,
            current_stage='NURSING'
        )
        context.update({
            'pending_consultations': assigned_patients.count(),
            'patients': assigned_patients,
            'doctor_patients': assigned_patients,  # For the doctor patient sidebar
        })
    elif role == 'PHARMACY':
        # ===== PHARMACY DASHBOARD - GROUP BY PATIENT =====
        from django.db.models import Count, Q
        
        # Get unique patients with pending orders
        pending_patients = Patient.objects.filter(
            pharmacy_orders__dispensed=False
        ).distinct().order_by('-created_at')
        
        # Annotate each patient with their pending order count
        pending_patients = pending_patients.annotate(
            pending_order_count=Count('pharmacy_orders', filter=Q(pharmacy_orders__dispensed=False))
        )
        
        # Get all pending orders
        pending_orders = PharmacyOrder.objects.filter(
            dispensed=False
        ).select_related('patient').order_by('patient', 'created_at')
        
        # Get drugs and low stock
        drugs = Drug.objects.all()
        low_stock = drugs.filter(quantity__lte=F('reorder_level'))
        
        # Get dispensed today
        today = date.today()
        dispensed_today = PharmacyOrder.objects.filter(
            dispensed=True,
            dispensed_at__date=today
        ).count()
        
        context.update({
            'pending_patients': pending_patients,  # GROUPED BY PATIENT
            'pending_orders': pending_orders,
            'pending_count': pending_orders.count(),  # Total orders for stats
            'pending_patients_count': pending_patients.count(),  # Unique patients
            'drugs': drugs,
            'low_stock_count': low_stock.count(),
            'total_drugs': drugs.count(),
            'dispensed_today': dispensed_today,
        })
    elif role == 'MLS':
        tests = LaboratoryTest.objects.filter(completed=False)
        context.update({
            'pending_tests': tests.count(),
            'tests': tests,
        })
    elif role == 'OPTOMETRIST':
        assessments = OpticalAssessment.objects.filter(completed=False)
        context.update({
            'pending_assessments': assessments.count(),
            'assessments': assessments,
        })
    
    return render(request, 'b/dashboard.html', context)

# ============= PATIENT REGISTRATION (HIM) =============

@login_required
@role_required(['HIM'])
def patient_registration(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save()
            PatientWorkflow.objects.create(patient=patient, current_stage='REGISTERED')
            messages.success(request, f'Patient {patient.full_name} registered successfully!')
            return redirect('b:assign_nurse')
    else:
        initial = {'hospital_number': generate_hospital_number()}
        form = PatientRegistrationForm(initial=initial)
    
    context = {
        'page': 'register',
        'form': form,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/patient_registration.html', context)

@login_required
@role_required(['HIM'])
def patient_list(request):
    patients = Patient.objects.all().order_by('-created_at')
    context = {
        'patients': patients,
        'page': 'patients',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/patient_list.html', context)

@login_required
@role_required(['HIM'])
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create workflow
    workflow, created = PatientWorkflow.objects.get_or_create(
        patient=patient,
        defaults={'current_stage': patient.current_stage or 'REGISTERED'}
    )
    
    context = {
        'patient': patient,
        'workflow': workflow,
        'page': 'patients',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/patient_detail.html', context)


# ============= ASSIGN NURSE & PHYSICIAN =============

@login_required
@role_required(['HIM'])
def assign_nurse(request):
    # Get patients that are registered but not yet assigned to a nurse
    unassigned_nurse_patients = Patient.objects.filter(
        current_stage='REGISTERED'
    ).exclude(
        id__in=NurseAssignment.objects.filter(is_active=True).values_list('patient_id', flat=True)
    )
    
    # Get patients that have completed nursing but not yet assigned to a physician
    unassigned_physician_patients = Patient.objects.filter(
        current_stage='NURSING'
    ).exclude(
        id__in=PhysicianAssignment.objects.filter(is_active=True).values_list('patient_id', flat=True)
    )
    
    # Get all active nurses
    nurses = User.objects.filter(
        userprofile__role='NURSE', 
        userprofile__is_active=True
    )
    
    # Get all active physicians
    physicians = User.objects.filter(
        userprofile__role='PHYSICIAN', 
        userprofile__is_active=True
    )
    
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        nurse_id = request.POST.get('nurse_id')
        physician_id = request.POST.get('physician_id')
        
        result = {
            'success': False,
            'message': '',
            'nurse_assigned': False,
            'physician_assigned': False,
            'notifications': []
        }
        
        if patient_id:
            patient = get_object_or_404(Patient, id=patient_id)
            
            # ===== ADD THIS: Ensure workflow exists =====
            workflow, created = PatientWorkflow.objects.get_or_create(
                patient=patient,
                defaults={'current_stage': patient.current_stage or 'REGISTERED'}
            )
            # ==========================================
            
            assigned_count = 0
            notifications = []
            
            # Assign Nurse if selected
            if nurse_id:
                nurse = get_object_or_404(User, id=nurse_id)
                
                # Check if already assigned
                if not NurseAssignment.objects.filter(patient=patient, is_active=True).exists():
                    NurseAssignment.objects.create(
                        patient=patient,
                        nurse=nurse,
                        assigned_by=request.user
                    )
                    assigned_count += 1
                    result['nurse_assigned'] = True
                    notifications.append({
                        'recipient': nurse.get_full_name(),
                        'message': f'Assigned to patient {patient.full_name} (ID: {patient.hospital_number})'
                    })
            
            # Assign Physician if selected
            if physician_id:
                physician = get_object_or_404(User, id=physician_id)
                
                # Check if already assigned
                if not PhysicianAssignment.objects.filter(patient=patient, is_active=True).exists():
                    PhysicianAssignment.objects.create(
                        patient=patient,
                        physician=physician,
                        assigned_by=request.user
                    )
                    assigned_count += 1
                    result['physician_assigned'] = True
                    notifications.append({
                        'recipient': physician.get_full_name(),
                        'message': f'Assigned to patient {patient.full_name} (ID: {patient.hospital_number}) for consultation'
                    })
            
            if assigned_count > 0:
                result['success'] = True
                result['message'] = f'Patient {patient.full_name} assigned to {assigned_count} staff member(s) successfully!'
                result['notifications'] = notifications
                
                # Check if this is an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # Get updated lists
                    unassigned_nurse_patients = Patient.objects.filter(
                        current_stage='REGISTERED'
                    ).exclude(
                        id__in=NurseAssignment.objects.filter(is_active=True).values_list('patient_id', flat=True)
                    )
                    
                    unassigned_physician_patients = Patient.objects.filter(
                        current_stage='NURSING'
                    ).exclude(
                        id__in=PhysicianAssignment.objects.filter(is_active=True).values_list('patient_id', flat=True)
                    )
                    
                    # Render the updated table rows
                    context = {
                        'unassigned_nurse_patients': unassigned_nurse_patients,
                        'unassigned_physician_patients': unassigned_physician_patients,
                        'nurses': nurses,
                        'physicians': physicians,
                        'pending_nurse_assignments': unassigned_nurse_patients.count(),
                        'pending_physician_assignments': unassigned_physician_patients.count(),
                    }
                    
                    html = render_to_string('b/him/assign_rows.html', context, request=request)
                    
                    return JsonResponse({
                        'success': True,
                        'message': result['message'],
                        'html': html,
                        'notifications': notifications,
                        'pending_nurse': unassigned_nurse_patients.count(),
                        'pending_physician': unassigned_physician_patients.count(),
                    })
                
                messages.success(request, result['message'])
                return redirect('b:assign_nurse')
            else:
                result['message'] = 'No staff selected for assignment.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(result)
                messages.warning(request, result['message'])
                return redirect('b:assign_nurse')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(result)
        messages.error(request, 'Invalid request.')
        return redirect('b:assign_nurse')
    
    context = {
        'page': 'assign',
        'unassigned_nurse_patients': unassigned_nurse_patients,
        'unassigned_physician_patients': unassigned_physician_patients,
        'nurses': nurses,
        'physicians': physicians,
        'pending_nurse_assignments': unassigned_nurse_patients.count(),
        'pending_physician_assignments': unassigned_physician_patients.count(),
        'pending_assignments': unassigned_nurse_patients.count() + unassigned_physician_patients.count(),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/assign_nurse.html', context)



# ============= NURSING VIEWS =============


@login_required
@role_required(['NURSE'])
def nursing_assessment(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create workflow
    workflow, created = PatientWorkflow.objects.get_or_create(
        patient=patient,
        defaults={'current_stage': patient.current_stage or 'REGISTERED'}
    )
    
    if request.method == 'POST':
        form = NursingAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.patient = patient
            assessment.created_by = request.user
            assessment.completed = True
            assessment.completed_at = timezone.now()
            assessment.save()
            
            workflow.nursing_completed = True
            workflow.nursing_completed_at = timezone.now()
            workflow.current_stage = 'NURSING'
            patient.current_stage = 'NURSING'
            patient.save()
            workflow.save()
            
            messages.success(request, f'Nursing assessment completed for {patient.full_name}')
            return redirect('b:nursing_dashboard')
    else:
        form = NursingAssessmentForm()
    
    context = {
        'patient': patient, 
        'form': form, 
        'page': 'nursing_assessment',
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/nurse/assessment.html', context)




@login_required
@role_required(['NURSE'])
def nursing_dashboard(request):
    # Get patients assigned to this nurse
    assigned_patients = Patient.objects.filter(
        nurseassignment__nurse=request.user,
        nurseassignment__is_active=True
    )
    
    # Get notifications for this nurse
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    pending_count = assigned_patients.filter(current_stage='REGISTERED').count()
    
    context = {
        'page': 'nursing',
        'role': get_user_role(request.user),  # <-- ADD THIS LINE
        'assigned_patients': assigned_patients,
        'assigned_count': assigned_patients.count(),
        'pending_count': pending_count,
        'notifications': notifications,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'completed_today': assigned_patients.filter(
            current_stage='NURSING',
            updated_at__date=timezone.now().date()
        ).count()
    }
    return render(request, 'b/nurse/dashboard.html', context)



# ============= PHYSICIAN VIEWS =============



@login_required
@role_required(['PHYSICIAN'])
def doctor_consultation(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create workflow
    workflow, created = PatientWorkflow.objects.get_or_create(
        patient=patient,
        defaults={'current_stage': patient.current_stage or 'REGISTERED'}
    )
    
    nursing = NursingAssessment.objects.filter(patient=patient).first()
    
    # Get available drugs from inventory
    drugs = Drug.objects.filter(is_active=True, quantity__gt=0).order_by('name')
    
    # Define available lab tests (list of test types the doctor can request)
    # These are the standard tests available in the system
    LAB_TEST_CHOICES = [
        {'id': 'malaria', 'name': 'Malaria Parasite Test', 'category': 'Parasitology'},
        {'id': 'rbs', 'name': 'Random Blood Sugar', 'category': 'Biochemistry'},
        {'id': 'hbsag', 'name': 'HBsAg', 'category': 'Serology'},
        # {'id': 'hcv', 'name': 'HCV', 'category': 'Serology'},
        # {'id': 'hiv', 'name': 'HIV', 'category': 'Serology'},
        {'id': 'other', 'name': 'Other Tests', 'category': 'General'},
    ]
    
    if request.method == 'POST':
        form = MedicalConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = patient
            consultation.nursing_assessment = nursing
            consultation.created_by = request.user
            consultation.completed = True
            consultation.completed_at = timezone.now()
            consultation.save()
            
            workflow.doctor_completed = True
            workflow.doctor_completed_at = timezone.now()
            
            if consultation.refer_to_pharmacy:
                workflow.current_stage = 'PHARMACY'
                patient.current_stage = 'PHARMACY'
                
                # Get selected drugs from the form
                selected_drugs_json = request.POST.get('selected_drugs', '[]')
                try:
                    import json
                    selected_drugs = json.loads(selected_drugs_json)
                    
                    # Create pharmacy order for each selected drug
                    for drug_data in selected_drugs:
                        drug = Drug.objects.get(id=drug_data['id'])
                        PharmacyOrder.objects.create(
                            patient=patient,
                            consultation=consultation,
                            drug_name=drug.name,
                            quantity=drug_data.get('quantity', 1),
                            dosage=drug.dosage_form or '',
                            frequency='As prescribed',
                            instructions='Refer from consultation',
                            created_by=request.user
                        )
                    messages.success(request, f'Pharmacy referral created with {len(selected_drugs)} drug(s)')
                except Exception as e:
                    # Fallback if no drugs selected
                    PharmacyOrder.objects.create(
                        patient=patient,
                        consultation=consultation,
                        drug_name='Prescribed medication',
                        quantity=1,
                        created_by=request.user
                    )
                    messages.success(request, 'Pharmacy referral created')
                    
            elif consultation.refer_to_laboratory:
                workflow.current_stage = 'LABORATORY'
                patient.current_stage = 'LABORATORY'
                
                # Get selected tests from the form
                selected_tests_json = request.POST.get('selected_tests', '[]')
                try:
                    import json
                    selected_tests = json.loads(selected_tests_json)
                    
                    # Create a new lab test for the patient with selected tests
                    lab_test = LaboratoryTest.objects.create(
                        patient=patient,
                        consultation=consultation,
                        created_by=request.user
                    )
                    
                    # Set the test results based on selected tests
                    for test in selected_tests:
                        test_id = test.get('id')
                        if test_id == 'malaria':
                            lab_test.malaria_parasite = 'PENDING'
                        elif test_id == 'rbs':
                            lab_test.random_blood_sugar = None  # Will be filled by MLS
                        elif test_id == 'hbsag':
                            lab_test.hbsag = 'PENDING'
                        elif test_id == 'hcv':
                            lab_test.hcv = 'PENDING'
                        elif test_id == 'hiv':
                            lab_test.hiv = 'PENDING'
                        elif test_id == 'other':
                            other_test_name = test.get('name', 'Other tests')
                            if lab_test.other_tests:
                                lab_test.other_tests += f", {other_test_name}"
                            else:
                                lab_test.other_tests = other_test_name
                    
                    lab_test.save()
                    messages.success(request, f'Laboratory referral created with {len(selected_tests)} test(s)')
                    
                except Exception as e:
                    # Fallback - create a basic lab test
                    LaboratoryTest.objects.create(
                        patient=patient,
                        consultation=consultation,
                        created_by=request.user
                    )
                    messages.success(request, 'Laboratory referral created')
                    
            elif consultation.refer_to_optician:
                workflow.current_stage = 'OPTICIAN'
                patient.current_stage = 'OPTICIAN'
                OpticalAssessment.objects.create(
                    patient=patient,
                    consultation=consultation,
                    created_by=request.user
                )
                messages.success(request, 'Optician referral created')
            else:
                workflow.current_stage = 'COMPLETED'
                patient.current_stage = 'COMPLETED'
                workflow.completed_at = timezone.now()
                messages.success(request, 'Consultation completed successfully')
            
            patient.save()
            workflow.save()
            
            return redirect('b:doctor_dashboard')
    else:
        form = MedicalConsultationForm()
    
    context = {
        'patient': patient,
        'role': get_user_role(request.user),
        'form': form,
        'nursing': nursing,
        'drugs': drugs,
        'lab_tests': LAB_TEST_CHOICES,  # Pass the list of available test types
        'page': 'doctor_consultation',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/doctor/consultation.html', context)





@login_required
@role_required(['PHYSICIAN'])
def doctor_dashboard(request):
    # Get patients assigned to this physician (all patients, not just NURSING)
    assigned_patients = Patient.objects.filter(
        physicianassignment__physician=request.user,
        physicianassignment__is_active=True
    )
    
    # Patients pending consultation (NURSING stage)
    pending_patients = assigned_patients.filter(current_stage='NURSING')
    
    # Completed consultations
    completed_patients = assigned_patients.filter(current_stage='COMPLETED')
    
    # Referred patients
    referred_patients = assigned_patients.filter(
        current_stage__in=['PHARMACY', 'LABORATORY', 'OPTICIAN']
    )
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'patients': pending_patients,  # For the main table (pending consultations)
        'doctor_patients': assigned_patients,  # For the sidebar (all patients)
        'role': get_user_role(request.user),
        'page': 'doctor',
        'pending_count': pending_patients.count(),
        'completed_count': completed_patients.count(),
        'referred_count': referred_patients.count(),
        'notifications': notifications,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    }
    return render(request, 'b/doctor/dashboard.html', context)


# ============= PHARMACY VIEWS =============

@login_required
@role_required(['PHARMACY'])
def pharmacy_dashboard(request):
    # Get all pending pharmacy orders grouped by patient
    pending_orders = PharmacyOrder.objects.filter(
        dispensed=False
    ).select_related('patient').order_by('patient', 'created_at')
    
    # Get unique patients with pending orders (grouped)
    pending_patients = Patient.objects.filter(
        pharmacy_orders__dispensed=False
    ).distinct().order_by('-created_at')
    
    # Annotate each patient with their pending order count
    pending_patients = pending_patients.annotate(
        pending_order_count=Count('pharmacy_orders', filter=Q(pharmacy_orders__dispensed=False))
    )
    
    # Get all drugs for inventory
    drugs = Drug.objects.all()
    low_stock = drugs.filter(quantity__lte=F('reorder_level'))
    
    # Get dispensed orders today
    today = timezone.now().date()
    dispensed_today = PharmacyOrder.objects.filter(
        dispensed=True,
        dispensed_at__date=today
    ).count()
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]

    # Get unread notification count
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # Check if there's a refresh flag in session
    refresh_notifications = request.session.pop('refresh_notifications', False)
    
    context = {
        'pending_patients': pending_patients,
        'pending_orders': pending_orders,
        'notification_count': unread_count,
        'refresh_notifications': refresh_notifications,
        'pending_count': pending_orders.count(),  # Total orders
        'pending_patients_count': pending_patients.count(),  # Unique patients
        'drugs': drugs,
        'low_stock_count': low_stock.count(),
        'total_drugs': drugs.count(),
        'dispensed_today': dispensed_today,
        'page': 'pharmacy',
        'role': get_user_role(request.user),
        'notifications': notifications,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    }
    return render(request, 'b/pharmacy/dashboard.html', context)

@login_required
@role_required(['PHARMACY'])
def pharmacy_dispense(request, order_id):
    """Dispense a single medication order"""
    order = get_object_or_404(PharmacyOrder, id=order_id)
    
    if request.method == 'POST':
        drug_id = request.POST.get('drug_id')
        quantity = int(request.POST.get('quantity', 0))
        
        if drug_id and quantity > 0:
            drug = get_object_or_404(Drug, id=drug_id)
            
            # Check if enough stock
            if drug.quantity < quantity:
                messages.error(request, f'Insufficient stock! Only {drug.quantity} units available.')
                return redirect('b:pharmacy_dispense', order_id=order_id)
            
            # Deduct from inventory
            drug.quantity -= quantity
            drug.save()
            
            # Create dispensing record
            PharmacyDispensing.objects.create(
                patient=order.patient,
                prescription=order,
                drug=drug,
                quantity_dispensed=quantity,
                dispensed_by=request.user
            )
            
            # Update order status
            order.dispensed = True
            order.dispensed_at = timezone.now()
            order.dispensed_by = request.user
            order.save()
            
            # ===== MARK ALL RELATED NOTIFICATIONS AS READ =====
            # Mark individual order notification
            Notification.objects.filter(
                recipient=request.user,
                link__icontains=f'/pharmacy/dispense/{order.id}/'
            ).update(is_read=True)
            
            # Mark patient-level notifications
            Notification.objects.filter(
                recipient=request.user,
                link__icontains=f'/pharmacy/dispense-patient/{order.patient.id}/'
            ).update(is_read=True)
            
            # Mark notifications with drug name
            Notification.objects.filter(
                recipient=request.user,
                message__icontains=order.drug_name,
                link__icontains='/pharmacy/'
            ).update(is_read=True)
            
            # Mark ALL pharmacy order notifications (safety net)
            Notification.objects.filter(
                recipient=request.user,
                link__icontains='/pharmacy/order/'
            ).update(is_read=True)
            
            # Check if all orders for this patient are dispensed
            pending_orders = PharmacyOrder.objects.filter(
                patient=order.patient,
                dispensed=False
            )
            
            if not pending_orders.exists():
                try:
                    workflow = PatientWorkflow.objects.get(patient=order.patient)
                    workflow.pharmacy_completed = True
                    workflow.pharmacy_completed_at = timezone.now()
                    workflow.save()
                except PatientWorkflow.DoesNotExist:
                    pass
            
            messages.success(request, f'Dispensed {quantity} units of {drug.name} to {order.patient.full_name}')
            return redirect('b:pharmacy_dashboard')
        else:
            messages.error(request, 'Please select a drug and enter quantity.')
    
    # GET request - show the dispense form
    drugs = Drug.objects.filter(is_active=True, quantity__gt=0)
    
    context = {
        'order': order,
        'drugs': drugs,
        'page': 'pharmacy_dispense',
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/dispense.html', context)

@login_required
@role_required(['PHARMACY'])
def pharmacy_dispense_patient(request, patient_id):
    """Dispense all pending orders for a patient at once"""
    patient = get_object_or_404(Patient, id=patient_id)
    pending_orders = PharmacyOrder.objects.filter(
        patient=patient,
        dispensed=False
    )
    
    # Format age for display
    age_data = patient.age_data
    if age_data:
        parts = []
        if age_data.get('years', 0) > 0:
            parts.append(f"{age_data['years']} year{'s' if age_data['years'] > 1 else ''}")
        if age_data.get('months', 0) > 0:
            parts.append(f"{age_data['months']} month{'s' if age_data['months'] > 1 else ''}")
        if age_data.get('days', 0) > 0:
            parts.append(f"{age_data['days']} day{'s' if age_data['days'] > 1 else ''}")
        formatted_age = ', '.join(parts) if parts else 'Newborn'
    else:
        formatted_age = '—'
    
    if request.method == 'POST':
        selected_drugs = request.POST.getlist('selected_drugs[]')
        quantities = request.POST.getlist('quantities[]')
        
        if not selected_drugs:
            messages.error(request, 'Please select at least one drug to dispense.')
            return redirect('b:pharmacy_dispense_patient', patient_id=patient_id)
        
        dispensed_count = 0
        dispensed_order_ids = []
        failed_orders = []
        
        for order_id, quantity in zip(selected_drugs, quantities):
            order = get_object_or_404(PharmacyOrder, id=order_id, patient=patient, dispensed=False)
            quantity = int(quantity) if quantity else order.quantity
            
            try:
                drug = Drug.objects.get(name__iexact=order.drug_name)
                
                if drug.quantity < quantity:
                    failed_orders.append({
                        'drug_name': drug.name,
                        'available': drug.quantity,
                        'requested': quantity
                    })
                    continue
                
                drug.quantity -= quantity
                drug.save()
                
                PharmacyDispensing.objects.create(
                    patient=patient,
                    prescription=order,
                    drug=drug,
                    quantity_dispensed=quantity,
                    dispensed_by=request.user,
                    notes=f'Dispensed {quantity} units as part of batch dispensing'
                )
                
                order.dispensed = True
                order.dispensed_at = timezone.now()
                order.dispensed_by = request.user
                order.save()
                
                dispensed_count += 1
                dispensed_order_ids.append(order.id)
                
            except Drug.DoesNotExist:
                order.dispensed = True
                order.dispensed_at = timezone.now()
                order.dispensed_by = request.user
                order.save()
                
                PharmacyDispensing.objects.create(
                    patient=patient,
                    prescription=order,
                    drug=None,
                    quantity_dispensed=quantity,
                    dispensed_by=request.user,
                    notes=f'Drug "{order.drug_name}" not found in inventory. Dispensed without stock deduction.'
                )
                
                dispensed_count += 1
                dispensed_order_ids.append(order.id)
                messages.warning(request, f'{order.drug_name} not found in inventory. Dispensed without stock deduction.')
        
        # ===== MARK ALL RELATED NOTIFICATIONS AS READ =====
        # Use a more aggressive approach to clean up notifications
        if dispensed_order_ids:
            # 1. Mark individual order notifications
            for order_id in dispensed_order_ids:
                Notification.objects.filter(
                    recipient=request.user,
                    link__icontains=f'/pharmacy/dispense/{order_id}/'
                ).update(is_read=True)
            
            # 2. Mark patient-level notifications
            Notification.objects.filter(
                recipient=request.user,
                link__icontains=f'/pharmacy/dispense-patient/{patient.id}/'
            ).update(is_read=True)
            
            # 3. Mark ALL pharmacy notifications for this user (most aggressive)
            Notification.objects.filter(
                recipient=request.user,
                link__icontains='/pharmacy/'
            ).update(is_read=True)
            
            # 4. Also mark notifications with patient name or ID
            Notification.objects.filter(
                recipient=request.user,
                message__icontains=patient.full_name
            ).update(is_read=True)
            
            # 5. Mark ALL notifications as read (safety net - but careful!)
            # Uncomment if still having issues
            # Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        
        if failed_orders:
            for failed in failed_orders:
                messages.error(
                    request, 
                    f'Insufficient stock for {failed["drug_name"]}. '
                    f'Available: {failed["available"]}, Requested: {failed["requested"]}'
                )
        
        remaining = PharmacyOrder.objects.filter(patient=patient, dispensed=False)
        if not remaining.exists():
            try:
                workflow = PatientWorkflow.objects.get(patient=patient)
                workflow.pharmacy_completed = True
                workflow.pharmacy_completed_at = timezone.now()
                workflow.save()
            except PatientWorkflow.DoesNotExist:
                pass
        
        if dispensed_count > 0:
            messages.success(
                request, 
                f'✅ Successfully dispensed {dispensed_count} medication(s) for {patient.full_name}'
            )
        elif failed_orders:
            messages.warning(
                request, 
                'No medications were dispensed due to insufficient stock.'
            )
        else:
            messages.info(request, 'No changes were made.')
        
        return redirect('b:pharmacy_dashboard')
    
    context = {
        'patient': patient,
        'pending_orders': pending_orders,
        'formatted_age': formatted_age,
        'drugs': Drug.objects.filter(is_active=True),
        'page': 'pharmacy_dispense',
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/dispense_patient.html', context)


@login_required
@role_required(['PHARMACY'])
def pharmacy_create_order(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        form = PharmacyOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.patient = patient
            order.created_by = request.user
            order.save()
            messages.success(request, f'Pharmacy order added for {patient.full_name}')
            return redirect('b:pharmacy_dashboard')
    else:
        form = PharmacyOrderForm()
    
    context = {
        'patient': patient, 
        'role': get_user_role(request.user),
        'form': form, 
        'page': 'pharmacy',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/create_order.html', context)





def pharmacy_pending_count(request):


    if request.user.is_authenticated and get_user_role(request.user) == 'PHARMACY':
        # Count UNIQUE patients with pending orders
        count = PharmacyOrder.objects.filter(
            dispensed=False
        ).values('patient').distinct().count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})


# ============= PHARMACY DRUG MANAGEMENT VIEWS =============

@login_required
@role_required(['PHARMACY'])
def pharmacy_drug_list(request):
    """List all drugs with inventory status"""
    drugs = Drug.objects.all().order_by('name')
    
    # Low stock alert
    low_stock = drugs.filter(quantity__lte=models.F('reorder_level'))
    
    context = {
        'drugs': drugs,
        'low_stock': low_stock,
        'low_stock_count': low_stock.count(),
        'total_drugs': drugs.count(),
        'page': 'pharmacy_drugs',
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/drug_list.html', context)


@login_required
@role_required(['PHARMACY'])
def pharmacy_drug_add(request):
    """Add a new drug to inventory"""
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            drug = form.save()
            messages.success(request, f'Drug {drug.name} added successfully!')
            return redirect('b:pharmacy_drug_list')
    else:
        form = DrugForm()
    
    context = {
        'form': form,
        'page': 'pharmacy_drug_add', 
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/drug_add.html', context)


@login_required
@role_required(['PHARMACY'])
def pharmacy_drug_edit(request, drug_id):
    """Edit existing drug"""
    drug = get_object_or_404(Drug, id=drug_id)
    
    if request.method == 'POST':
        form = DrugForm(request.POST, instance=drug)
        if form.is_valid():
            form.save()
            messages.success(request, f'Drug {drug.name} updated successfully!')
            return redirect('b:pharmacy_drug_list')
    else:
        form = DrugForm(instance=drug)
    
    context = {
        'form': form,
        'drug': drug,
        'page': 'pharmacy_drug_add', 
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/drug_edit.html', context)


@login_required
@role_required(['PHARMACY'])
def pharmacy_drug_delete(request, drug_id):
    """Delete a drug from inventory"""
    drug = get_object_or_404(Drug, id=drug_id)
    
    if request.method == 'POST':
        drug_name = drug.name
        drug.delete()
        messages.success(request, f'Drug {drug_name} deleted successfully!')
        return redirect('b:pharmacy_drug_list')
    
    context = {
        'drug': drug,
        'page': 'pharmacy_drug_add', 
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/drug_delete_confirm.html', context)


# ============= LABORATORY VIEWS =============

@login_required
@role_required(['MLS'])
def laboratory_dashboard(request):
    tests = LaboratoryTest.objects.filter(completed=False)
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'tests': tests,
        'page': 'lab',
        'role': get_user_role(request.user),
        'pending_count': tests.count(),
        'notifications': notifications,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    }
    return render(request, 'b/lab/dashboard.html', context)

@login_required
@role_required(['MLS'])
def laboratory_test(request, test_id):
    test = get_object_or_404(LaboratoryTest, id=test_id)
    
    if request.method == 'POST':
        form = LaboratoryTestForm(request.POST, instance=test)
        if form.is_valid():
            lab_test = form.save(commit=False)
            lab_test.completed = True
            lab_test.completed_at = timezone.now()
            lab_test.completed_by = request.user
            lab_test.save()
            
            # Update workflow
            workflow = PatientWorkflow.objects.get(patient=test.patient)
            workflow.laboratory_completed = True
            workflow.laboratory_completed_at = timezone.now()
            
            # Check if there are other referrals
            consultation = MedicalConsultation.objects.filter(
                patient=test.patient
            ).first()
            
            # ===== NOTIFY PHYSICIAN =====
            # Find the physician assigned to this patient
            physician_assignment = PhysicianAssignment.objects.filter(
                patient=test.patient,
                is_active=True
            ).first()
            
            if physician_assignment:
                # Create notification for physician with test results
                result_summary = []
                if lab_test.malaria_parasite != 'PENDING':
                    result_summary.append(f"Malaria: {lab_test.malaria_parasite}")
                if lab_test.random_blood_sugar is not None:
                    result_summary.append(f"RBS: {lab_test.random_blood_sugar} mmol/L")
                if lab_test.hbsag != 'PENDING':
                    result_summary.append(f"HBsAg: {lab_test.hbsag}")
                
                summary_text = ", ".join(result_summary) if result_summary else "Results available"
                
                Notification.objects.create(
                    recipient=physician_assignment.physician,
                    message=f'🧪 Lab results ready for {test.patient.full_name}: {summary_text}',
                    link=f'/doctor/consultation/{test.patient.id}/',
                    is_read=False
                )
                print(f"✅ PHYSICIAN NOTIFICATION: Lab results ready for {test.patient.full_name}")
                
                # Also send WebSocket notification
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'user_{physician_assignment.physician.id}',
                        {
                            'type': 'notification_message',
                            'message': f'🧪 Lab results ready for {test.patient.full_name}: {summary_text}',
                            'link': f'/doctor/consultation/{test.patient.id}/',
                            'created_at': str(lab_test.completed_at)
                        }
                    )
                except Exception as e:
                    print(f"WebSocket error: {e}")
            
            # Determine next stage
            if consultation and consultation.refer_to_optician:
                workflow.current_stage = 'OPTICIAN'
                test.patient.current_stage = 'OPTICIAN'
            else:
                workflow.current_stage = 'COMPLETED'
                test.patient.current_stage = 'COMPLETED'
                workflow.completed_at = timezone.now()
            
            test.patient.save()
            workflow.save()
            
            messages.success(request, f'Lab test completed for {test.patient.full_name}')
            return redirect('b:laboratory_dashboard')
    else:
        form = LaboratoryTestForm(instance=test)
    
    context = {
        'test': test, 
        'form': form, 
        'role': get_user_role(request.user),
        'page': 'lab_test',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/lab/test.html', context)

# @login_required
# @role_required(['MLS'])
# def laboratory_test(request, test_id):
#     test = get_object_or_404(LaboratoryTest, id=test_id)
    
#     if request.method == 'POST':
#         form = LaboratoryTestForm(request.POST, instance=test)
#         if form.is_valid():
#             lab_test = form.save(commit=False)
#             lab_test.completed = True
#             lab_test.completed_at = timezone.now()
#             lab_test.completed_by = request.user
#             lab_test.save()
            
#             # Update workflow
#             workflow = PatientWorkflow.objects.get(patient=test.patient)
#             workflow.laboratory_completed = True
#             workflow.laboratory_completed_at = timezone.now()
            
#             # Check if there are other referrals
#             consultation = MedicalConsultation.objects.filter(
#                 patient=test.patient
#             ).first()
#             if consultation and consultation.refer_to_optician:
#                 workflow.current_stage = 'OPTICIAN'
#                 test.patient.current_stage = 'OPTICIAN'
#             else:
#                 workflow.current_stage = 'COMPLETED'
#                 test.patient.current_stage = 'COMPLETED'
#                 workflow.completed_at = timezone.now()
            
#             test.patient.save()
#             workflow.save()
            
#             # Notification is sent via signal
#             messages.success(request, f'Lab test completed for {test.patient.full_name}')
#             return redirect('b:laboratory_dashboard')
#     else:
#         form = LaboratoryTestForm(instance=test)
    
#     context = {
#         'test': test, 
#         'form': form, 
#         'role': get_user_role(request.user),
#         'page': 'lab_test',
#         'notification_count': Notification.objects.filter(
#             recipient=request.user,
#             is_read=False
#         ).count(),
#         'notifications': Notification.objects.filter(
#             recipient=request.user,
#             is_read=False
#         ).order_by('-created_at')[:10]
#     }
#     return render(request, 'b/lab/test.html', context)

# ============= OPTICIAN VIEWS =============

@login_required
@role_required(['OPTOMETRIST'])
def optician_dashboard(request):
    assessments = OpticalAssessment.objects.filter(completed=False)
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'assessments': assessments,
        'role': get_user_role(request.user),
        'page': 'optician',
        'pending_count': assessments.count(),
        'notifications': notifications,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    }
    return render(request, 'b/optician/dashboard.html', context)

@login_required
@role_required(['OPTOMETRIST'])
def optician_assessment(request, patient_id=None):
    # For walk-in patients
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
    else:
        patient = None
    
    if request.method == 'POST':
        form = OpticalAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.created_by = request.user
            assessment.completed = True
            assessment.completed_at = timezone.now()
            assessment.completed_by = request.user
            
            if patient:
                assessment.patient = patient
                assessment.save()
                
                # Update workflow
                workflow = PatientWorkflow.objects.get(patient=patient)
                workflow.optician_completed = True
                workflow.optician_completed_at = timezone.now()
                workflow.current_stage = 'COMPLETED'
                workflow.completed_at = timezone.now()
                patient.current_stage = 'COMPLETED'
                patient.save()
                workflow.save()
                
                # Notification is sent via signal
                messages.success(request, f'Optical assessment completed for {patient.full_name}')
                
                # Notify physician if this was a referral
                physician_assignment = PhysicianAssignment.objects.filter(
                    patient=patient,
                    is_active=True
                ).first()
                
                if physician_assignment:
                    Notification.objects.create(
                        recipient=physician_assignment.physician,
                        message=f'👁️ Optical assessment completed for {patient.full_name}',
                        link=f'/doctor/consultation/{patient.id}/',
                        is_read=False
                    )
                    
            else:
                # Walk-in patient - create new patient
                # You'll need to collect basic patient info from the form
                # For now, we'll create a basic patient record
                from datetime import date
                
                # Create a new patient for walk-in
                # You can add fields to the form to collect this info
                new_patient = Patient.objects.create(
                    hospital_number=f"WALK{date.today().strftime('%Y%m%d')}{random.randint(100, 999)}",
                    first_name=request.POST.get('first_name', 'Walk-in'),
                    last_name=request.POST.get('last_name', 'Patient'),
                    date_of_birth=request.POST.get('date_of_birth') or date.today(),
                    gender=request.POST.get('gender', 'OTHER'),
                    phone=request.POST.get('phone', '08000000000'),
                    address='COREP',
                    current_stage='COMPLETED'
                )
                
                # Create workflow
                PatientWorkflow.objects.create(
                    patient=new_patient,
                    current_stage='COMPLETED',
                    optician_completed=True,
                    optician_completed_at=timezone.now(),
                    completed_at=timezone.now()
                )
                
                assessment.patient = new_patient
                assessment.is_walk_in = True
                assessment.save()
                
                messages.success(request, f'Optical assessment completed for walk-in patient {new_patient.full_name}')
            
            return redirect('b:optician_dashboard')
    else:
        form = OpticalAssessmentForm()
    
    context = {
        'patient': patient,
        'role': get_user_role(request.user),
        'page': 'optician_assessment',
        'form': form,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/optician/assessment.html', context)

# @login_required
# @role_required(['OPTOMETRIST'])
# def optician_assessment(request, patient_id=None):
#     # For walk-in patients
#     if patient_id:
#         patient = get_object_or_404(Patient, id=patient_id)
#     else:
#         patient = None
    
#     if request.method == 'POST':
#         form = OpticalAssessmentForm(request.POST)
#         if form.is_valid():
#             assessment = form.save(commit=False)
#             assessment.created_by = request.user
#             assessment.completed = True
#             assessment.completed_at = timezone.now()
#             assessment.completed_by = request.user
            
#             if patient:
#                 assessment.patient = patient
#                 assessment.save()
                
#                 # Update workflow
#                 workflow = PatientWorkflow.objects.get(patient=patient)
#                 workflow.optician_completed = True
#                 workflow.optician_completed_at = timezone.now()
#                 workflow.current_stage = 'COMPLETED'
#                 workflow.completed_at = timezone.now()
#                 patient.current_stage = 'COMPLETED'
#                 patient.save()
#                 workflow.save()
                
#                 # Notification is sent via signal
#                 messages.success(request, f'Optical assessment completed for {patient.full_name}')
#             else:
#                 # Walk-in patient
#                 assessment.save()
#                 messages.success(request, 'Optical assessment completed for walk-in patient')
            
#             return redirect('b:optician_dashboard')
#     else:
#         form = OpticalAssessmentForm()
    
#     context = {
#         'patient': patient,
#         'role': get_user_role(request.user),
#         'page': 'optician_assessment',
#         'form': form,
#         'page': 'optician',
#         'notification_count': Notification.objects.filter(
#             recipient=request.user,
#             is_read=False
#         ).count(),
#         'notifications': Notification.objects.filter(
#             recipient=request.user,
#             is_read=False
#         ).order_by('-created_at')[:10]
#     }
#     return render(request, 'b/optician/assessment.html', context)

# ============= USER MANAGEMENT VIEWS =============

@login_required
@role_required(['HIM'])
def user_registration(request):
    """Register new users with default password"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Assign user to group based on role
            role = form.cleaned_data['role']
            try:
                group, created = Group.objects.get_or_create(name=role)
                user.groups.add(group)
            except:
                pass
            
            messages.success(
                request, 
                f'User {user.get_full_name()} created successfully! '
                f'Default password: {UserRegistrationForm.DEFAULT_PASSWORD}'
            )
            return redirect('b:user_list')
    else:
        form = UserRegistrationForm()
    
    context = {
        'page': 'user_register', 
        'role': get_user_role(request.user),
        'form': form,
        'title': 'Register New User',
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/user_registration.html', context)

@login_required
@role_required(['HIM'])
def user_list(request):
    """List all users with their roles"""
    users = User.objects.all().select_related('userprofile').order_by('-date_joined')
    context = {
        'page': 'user_list', 
        'role': get_user_role(request.user),
        'users': users,
        'total': users.count(),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/user_list.html', context)

@login_required
@role_required(['HIM'])
def user_edit(request, user_id):
    """Edit user details and reset password"""
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(UserProfile, user=user)
    
    if request.method == 'POST':
        # Update user details
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        # Update profile
        profile.role = request.POST.get('role', profile.role)
        profile.phone = request.POST.get('phone', profile.phone)
        profile.department = request.POST.get('department', profile.department)
        profile.is_active = request.POST.get('is_active') == 'on'
        profile.save()
        
        # Reset password if requested
        if request.POST.get('reset_password'):
            user.set_password('password123')
            user.save()
            messages.success(request, f'Password reset to default for {user.get_full_name()}')
        
        messages.success(request, f'User {user.get_full_name()} updated successfully!')
        return redirect('b:user_list')
    
    context = {
        'page': 'user_list',  
        'user': user,
        'role': get_user_role(request.user),
        'profile': profile,
        'roles': UserProfile.USER_ROLES,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/user_edit.html', context)

@login_required
@role_required(['HIM'])
def user_delete(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_name = user.get_full_name()
        user.delete()
        messages.success(request, f'User {user_name} deleted successfully!')
        return redirect('b:user_list')
    
    context = {
        'user': user,
        'page': 'users',
        'role': get_user_role(request.user),
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/him/user_delete_confirm.html', context)

@login_required
@role_required(['HIM'])
def user_toggle_active(request, user_id):
    """Toggle user active status"""
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(UserProfile, user=user)
    profile.is_active = not profile.is_active
    profile.save()
    
    status = 'activated' if profile.is_active else 'deactivated'
    messages.success(request, f'User {user.get_full_name()} {status}!')
    return redirect('b:user_list')

# ============= API ENDPOINTS =============

def get_age_from_dob(request):
    dob = request.GET.get('dob')
    if dob:
        try:
            from datetime import datetime
            dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
            today = date.today()
            
            # Calculate age in years, months, days
            years = today.year - dob_date.year
            months = today.month - dob_date.month
            days = today.day - dob_date.day
            
            if days < 0:
                months -= 1
                prev_month = date(today.year, today.month, 1) - timedelta(days=1)
                days += prev_month.day
            
            if months < 0:
                years -= 1
                months += 12
            
            # Format the age display
            parts = []
            if years > 0:
                parts.append(f"{years} year{'s' if years > 1 else ''}")
            if months > 0:
                parts.append(f"{months} month{'s' if months > 1 else ''}")
            if days > 0:
                parts.append(f"{days} day{'s' if days > 1 else ''}")
            
            display_age = ', '.join(parts) if parts else 'Newborn'
            
            return JsonResponse({
                'success': True,
                'age': display_age,
                'years': years,
                'months': months,
                'days': days
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    return JsonResponse({
        'success': False,
        'error': 'No date provided'
    })

def notification_count(request):
    """API endpoint to get unread notification count"""
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})






def notifications_latest(request):
    """API endpoint to get latest unread notifications"""
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
        
        data = []
        for notif in notifications:
            data.append({
                'id': notif.id,
                'message': notif.message,
                'link': notif.link,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat()
            })
        
        return JsonResponse({'notifications': data})
    return JsonResponse({'notifications': []})


def debug_notifications(request):
    """Debug view to check notifications"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    data = {
        'total': Notification.objects.count(),
        'unread': Notification.objects.filter(is_read=False).count(),
        'notifications': []
    }
    
    for notif in Notification.objects.all().order_by('-created_at')[:20]:
        data['notifications'].append({
            'id': notif.id,
            'recipient': notif.recipient.username,
            'message': notif.message,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat(),
            'link': notif.link
        })
    
    return JsonResponse(data)

# ================ Mark All as Read ===========================

def mark_all_notifications_read(request):
    """API endpoint to mark all notifications as read for the current user"""
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        return JsonResponse({'success': True, 'count': count})
    return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)


def hard_reset_notifications(request):
    """Hard reset all notifications for the current user"""
    if request.user.is_authenticated:
        # Mark ALL notifications as read
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        return JsonResponse({'success': True, 'count': count})
    return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)




# ========================= DEBUGs ========================

def debug_notification_count(request):
    """Debug view to check notification counts"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    total = Notification.objects.filter(recipient=request.user).count()
    unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    # Get all unread notifications with details
    unread_list = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).values('id', 'message', 'link', 'created_at')
    
    return JsonResponse({
        'total': total,
        'unread': unread,
        'unread_list': list(unread_list),
        'user': request.user.username,
        'role': get_user_role(request.user)
    })

def debug_pharmacy_orders(request):
    """Debug view to check pharmacy orders"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    pending_orders = PharmacyOrder.objects.filter(dispensed=False)
    pending_patients = pending_orders.values('patient').distinct().count()
    
    return JsonResponse({
        'total_orders': pending_orders.count(),
        'unique_patients': pending_patients,
        'orders': list(pending_orders.values('id', 'patient__full_name', 'drug_name', 'quantity', 'dispensed'))
    })

def debug_mark_notifications_read(request):
    """Debug view to mark notifications as read and show result"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    # Count before
    before = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    # Mark all as read
    updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    
    # Count after
    after = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return JsonResponse({
        'success': True,
        'before_count': before,
        'updated_count': updated,
        'after_count': after
    })

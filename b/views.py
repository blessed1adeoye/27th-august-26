# b/views


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta, datetime
import random
from django.contrib.admin.views.decorators import staff_member_required
import string
from .models import *
from .forms import *
from django.contrib.auth.models import User, Group
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Max, Prefetch, Q, Sum
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
            
            # ===== FIX: Set default values for empty required fields =====
            if assessment.blood_pressure_systolic is None or assessment.blood_pressure_systolic == '':
                assessment.blood_pressure_systolic = 0
            if assessment.blood_pressure_diastolic is None or assessment.blood_pressure_diastolic == '':
                assessment.blood_pressure_diastolic = 0
            if assessment.pulse_rate is None or assessment.pulse_rate == '':
                assessment.pulse_rate = 0
            
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
    assigned_patients = Patient.objects.filter(
        nurseassignment__nurse=request.user,
        nurseassignment__is_active=True
    )
    patient_search = request.GET.get('patient_search', '').strip()
    patients = assigned_patients
    if patient_search:
        patients = Patient.objects.filter(
            Q(hospital_number__icontains=patient_search) |
            Q(first_name__icontains=patient_search) |
            Q(middle_name__icontains=patient_search) |
            Q(last_name__icontains=patient_search)
        )

    patients = patients.prefetch_related(
        Prefetch(
            'nursing_assessments',
            queryset=NursingAssessment.objects.order_by('-completed_at', '-created_at'),
            to_attr='latest_assessments'
        )
    ).distinct()
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    pending_count = assigned_patients.filter(current_stage='REGISTERED').count()
    
    context = {
        'page': 'nursing',
        'assigned_patients': patients,
        'patient_search': patient_search,
        'is_patient_search': bool(patient_search),
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
        ).count(),
        'role': get_user_role(request.user)
    }
    return render(request, 'b/nurse/dashboard.html', context)

@login_required
@role_required(['NURSE'])
def nursing_dashboard_data_api(request):
    """API endpoint for nursing dashboard data refresh"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        if profile.role != 'NURSE':
            return JsonResponse({'error': 'Not a nurse'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=403)
    
    # Get assigned patients
    assigned_patients = Patient.objects.filter(
        nurseassignment__nurse=request.user,
        nurseassignment__is_active=True
    )
    
    assigned_count = assigned_patients.count()
    pending_count = assigned_patients.filter(current_stage='REGISTERED').count()
    completed_today = assigned_patients.filter(
        current_stage='NURSING',
        updated_at__date=timezone.now().date()
    ).count()
    
    return JsonResponse({
        'assigned_count': assigned_count,
        'pending_count': pending_count,
        'completed_today': completed_today,
    })

# ============= PHYSICIAN VIEWS =============



@login_required
@role_required(['PHYSICIAN'])
def doctor_consultation(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    workflow, created = PatientWorkflow.objects.get_or_create(
        patient=patient,
        defaults={'current_stage': patient.current_stage or 'REGISTERED'}
    )
    
    nursing = NursingAssessment.objects.filter(patient=patient).first()
    drugs = Drug.objects.filter(is_active=True, quantity__gt=0).order_by('name')
    
    LAB_TEST_CHOICES = [
        {'id': 'malaria', 'name': 'Malaria Parasite Test', 'category': 'Parasitology'},
        {'id': 'rbs', 'name': 'Random Blood Sugar', 'category': 'Biochemistry'},
        {'id': 'hbsag', 'name': 'HBsAg', 'category': 'Serology'},
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
            
            # ===== AUTO-SET PHARMACY REFERRAL IF TREATMENT PLAN HAS CONTENT =====
            if consultation.treatment_plan and consultation.treatment_plan.strip():
                consultation.refer_to_pharmacy = True
                print(f"💊 Auto-pharmacy referral set for {patient.full_name}")
            
            consultation.save()
            
            workflow.doctor_completed = True
            workflow.doctor_completed_at = timezone.now()
            
            # ===== CREATE PHARMACY ORDERS FROM TREATMENT PLAN =====
            if consultation.treatment_plan and consultation.treatment_plan.strip():
                lines = consultation.treatment_plan.strip().split('\n')
                order_count = 0
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    import re
                    
                    # Try to extract quantity
                    qty_match = re.search(r'[=:]\s*([\d,]+)', line)
                    if qty_match:
                        qty_str = qty_match.group(1).replace(',', '')
                        try:
                            qty = int(qty_str)
                        except:
                            qty = 1
                    else:
                        x_match = re.search(r'[x×]\s*(\d+)', line)
                        if x_match:
                            qty = int(x_match.group(1))
                        else:
                            qty = 1
                    
                    # Clean the drug name
                    drug_name = re.sub(r'\s*[=:].*$', '', line).strip()
                    drug_name = re.sub(r'\s*[x×]\s*\d+', '', drug_name).strip()
                    drug_name = re.sub(r'^[\d]+[\.\)\-]\s*', '', drug_name).strip()
                    
                    if drug_name:
                        PharmacyOrder.objects.create(
                            patient=patient,
                            consultation=consultation,
                            drug_name=drug_name,
                            quantity=qty,
                            dosage="As prescribed",
                            frequency="See treatment plan",
                            duration="As prescribed",
                            instructions=line,
                            created_by=request.user
                        )
                        order_count += 1
                        print(f"💊 Pharmacy order created: {drug_name} x{qty}")
                
                if order_count > 0:
                    messages.success(request, f'💊 {order_count} prescription(s) sent to pharmacy for {patient.full_name}')
            
            # Handle laboratory referral
            if consultation.refer_to_laboratory:
                workflow.current_stage = 'LABORATORY'
                patient.current_stage = 'LABORATORY'
                
                selected_tests_json = request.POST.get('selected_tests', '[]')
                try:
                    import json
                    selected_tests = json.loads(selected_tests_json)
                    
                    lab_test = LaboratoryTest.objects.create(
                        patient=patient,
                        consultation=consultation,
                        created_by=request.user
                    )
                    
                    for test in selected_tests:
                        test_id = test.get('id')
                        if test_id == 'malaria':
                            lab_test.malaria_parasite = 'PENDING'
                        elif test_id == 'rbs':
                            lab_test.random_blood_sugar = None
                        elif test_id == 'hbsag':
                            lab_test.hbsag = 'PENDING'
                        elif test_id == 'other':
                            other_test_name = test.get('name', 'Other tests')
                            if lab_test.other_tests:
                                lab_test.other_tests += f", {other_test_name}"
                            else:
                                lab_test.other_tests = other_test_name
                    
                    lab_test.save()
                    messages.success(request, f'🧪 Laboratory referral created with {len(selected_tests)} test(s)')
                    
                except Exception as e:
                    LaboratoryTest.objects.create(
                        patient=patient,
                        consultation=consultation,
                        created_by=request.user
                    )
                    messages.success(request, '🧪 Laboratory referral created')
                    
            elif consultation.refer_to_optician:
                workflow.current_stage = 'OPTICIAN'
                patient.current_stage = 'OPTICIAN'
                OpticalAssessment.objects.create(
                    patient=patient,
                    consultation=consultation,
                    created_by=request.user
                )
                messages.success(request, '👁️ Optician referral created')
            else:
                if consultation.refer_to_pharmacy:
                    workflow.current_stage = 'PHARMACY'
                    patient.current_stage = 'PHARMACY'
                else:
                    workflow.current_stage = 'COMPLETED'
                    patient.current_stage = 'COMPLETED'
                    workflow.completed_at = timezone.now()
                    messages.success(request, '✅ Consultation completed successfully')
            
            patient.save()
            workflow.save()
            
            return redirect('b:doctor_dashboard')
    else:
        form = MedicalConsultationForm()
    
    # ===== GET COUNTS FOR SIDEBAR BADGES =====
    assigned_patients = Patient.objects.filter(
        physicianassignment__physician=request.user,
        physicianassignment__is_active=True
    )
    
    # ===== DEBUG =====
    print("=" * 60)
    print("🔍 DOCTOR CONSULTATION DEBUG")
    print(f"👤 Physician: {request.user.username}")
    print(f"📊 Patient: {patient.full_name}")
    
    # Count unviewed lab results
    lab_results_count = LaboratoryTest.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).count()
    print(f"📊 Unviewed Lab Results: {lab_results_count}")
    
    # Count unviewed optician results (viewed_by_physician=False)
    optician_results_count = OpticalAssessment.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).count()
    print(f"📊 Unviewed Optician Results: {optician_results_count}")
    
    # Show all optician assessments
    all_optician = OpticalAssessment.objects.filter(patient__in=assigned_patients, completed=True)
    print(f"📊 Total completed optician assessments: {all_optician.count()}")
    for a in all_optician:
        print(f"   ID: {a.id} | Patient: {a.patient.full_name} | Viewed by Physician: {a.viewed_by_physician}")
    print("=" * 60)
    
    context = {
        'patient': patient,
        'role': get_user_role(request.user),
        'form': form,
        'nursing': nursing,
        'drugs': drugs,
        'lab_tests': LAB_TEST_CHOICES,
        'page': 'doctor_consultation',
        'lab_results_count': lab_results_count,
        'optician_results_count': optician_results_count,
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
    # Get patients assigned to this physician
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
    
    # ===== NEW: Patients with lab results ready =====
    patients_with_lab_results = assigned_patients.filter(
        lab_tests__completed=True,
        current_stage='LABORATORY'
    ).distinct()
    
    # Get lab results for each patient
    lab_results_data = []
    for patient in patients_with_lab_results:
        lab_tests = patient.lab_tests.filter(completed=True).order_by('-completed_at')
        for test in lab_tests:
            lab_results_data.append({
                'patient': patient,
                'test': test,
                'results': {
                    'malaria': test.malaria_parasite if test.malaria_parasite != 'PENDING' else None,
                    'rbs': str(test.random_blood_sugar) if test.random_blood_sugar is not None else None,
                    'hbsag': test.hbsag if test.hbsag != 'PENDING' else None,
                    'other': test.other_tests if test.other_tests else None,
                }
            })
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'patients': pending_patients,
        'page': 'doctor',
        'doctor_patients': assigned_patients,
        'patients_with_lab_results': patients_with_lab_results,
        'lab_results': lab_results_data,
        'lab_results_count': patients_with_lab_results.count(),
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


@login_required
def doctor_dashboard_data_api(request):
    """API endpoint for doctor dashboard data refresh"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        if profile.role != 'PHYSICIAN':
            return JsonResponse({'error': 'Not a physician'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=403)
    
    # Get patients assigned to this physician
    assigned_patients = Patient.objects.filter(
        physicianassignment__physician=request.user,
        physicianassignment__is_active=True
    )
    
    # Lab results with IDs
    lab_results = []
    patients_with_lab_results = assigned_patients.filter(
        lab_tests__completed=True
    ).distinct()
    
    for patient in patients_with_lab_results:
        for test in patient.lab_tests.filter(completed=True):
            tests_summary = []
            if test.malaria_parasite != 'PENDING':
                tests_summary.append(f"Malaria: {test.malaria_parasite}")
            if test.random_blood_sugar is not None:
                tests_summary.append(f"RBS: {test.random_blood_sugar} mmol/L")
            if test.hbsag != 'PENDING':
                tests_summary.append(f"HBsAg: {test.hbsag}")
            if test.other_tests:
                tests_summary.append(test.other_tests)
            
            lab_results.append({
                'id': test.id,
                'patient_name': patient.full_name,
                'patient_id': patient.id,
                'tests': ', '.join(tests_summary) if tests_summary else 'Results available',
                'completed_at': test.completed_at.isoformat() if test.completed_at else None,
            })
    
    lab_results_count = patients_with_lab_results.count()
    
    # Optician results with IDs
    optician_results = []
    patients_with_optician_results = assigned_patients.filter(
        optical_assessments__completed=True
    ).distinct()
    
    for patient in patients_with_optician_results:
        for assessment in patient.optical_assessments.filter(completed=True):
            optician_results.append({
                'id': assessment.id,
                'patient_name': patient.full_name,
                'patient_id': patient.id,
                'visual_acuity': f"{assessment.visual_acuity_left}/{assessment.visual_acuity_right}",
                'glasses': assessment.glasses_allocated,
                'glasses_type': assessment.glasses_type,
                'completed_at': assessment.completed_at.isoformat() if assessment.completed_at else None,
            })
    
    optician_results_count = patients_with_optician_results.count()
    
    # Check for new results (last 24 hours)
    from datetime import timedelta
    yesterday = timezone.now() - timedelta(days=1)
    
    has_new_lab_results = LaboratoryTest.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        completed_at__gt=yesterday
    ).exists()
    
    has_new_optician_results = OpticalAssessment.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        completed_at__gt=yesterday
    ).exists()
    
    return JsonResponse({
        'lab_results_count': lab_results_count,
        'optician_results_count': optician_results_count,
        'lab_results': lab_results,  # NEW: Return full lab results with IDs
        'optician_results': optician_results,  # NEW: Return full optician results with IDs
        'has_new_lab_results': has_new_lab_results,
        'has_new_optician_results': has_new_optician_results,
    })

# ============= PHYSICIAN LAB RESULTS VIEWS =============


@login_required
@role_required(['PHYSICIAN'])
def physician_lab_results(request):
    """List all lab results for the physician's patients"""
    assigned_patients = Patient.objects.filter(
        physicianassignment__physician=request.user,
        physicianassignment__is_active=True
    )
    
    # Get ALL completed lab tests for assigned patients
    lab_tests = LaboratoryTest.objects.filter(
        patient__in=assigned_patients,
        completed=True
    ).select_related('patient').order_by('-completed_at')
    
    # ===== Mark ALL lab tests as viewed =====
    unviewed_tests = lab_tests.filter(viewed_by_physician=False)
    if unviewed_tests.exists():
        now = timezone.now()
        updated_count = unviewed_tests.update(viewed_by_physician=True, viewed_at=now)
        print(f"👨‍⚕️ Marked {updated_count} lab results as viewed")
    
    # ===== Recalculate counts after marking =====
    total_results = lab_tests.count()
    unique_patients = lab_tests.values('patient').distinct().count()
    
    # ===== FIX: Get unviewed counts for sidebar badges =====
    unviewed_lab = LaboratoryTest.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).count()
    
    unviewed_optician = OpticalAssessment.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).count()
    
    print(f"📊 AFTER MARKING - Unviewed Lab: {unviewed_lab}")
    print(f"📊 AFTER MARKING - Unviewed Optician: {unviewed_optician}")
    
    # Build result data
    results = []
    for test in lab_tests:
        tests_summary = []
        if test.malaria_parasite != 'PENDING':
            tests_summary.append({'name': 'Malaria', 'result': test.malaria_parasite})
        if test.random_blood_sugar is not None:
            tests_summary.append({'name': 'RBS', 'result': f"{test.random_blood_sugar} mmol/L"})
        if test.hbsag != 'PENDING':
            tests_summary.append({'name': 'HBsAg', 'result': test.hbsag})
        if test.other_tests:
            tests_summary.append({'name': 'Other', 'result': test.other_tests})
        
        results.append({
            'test': test,
            'patient': test.patient,
            'tests': tests_summary,
            'completed_at': test.completed_at,
            'status': 'Completed' if test.completed else 'Pending',
            'viewed': test.viewed_by_physician
        })
    
    context = {
        'results': results,
        'total_results': total_results,
        'unique_patients': unique_patients,
        'unviewed_count': unviewed_lab,  # For the page header
        'page': 'lab_results',
        # ===== FIX: Pass the counts to the context =====
        'lab_results_count': unviewed_lab,
        'optician_results_count': unviewed_optician,
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
    return render(request, 'b/doctor/lab_results.html', context)

@login_required
@role_required(['PHYSICIAN'])
def physician_lab_result_detail(request, test_id):
    """View details of a specific lab result"""
    test = get_object_or_404(LaboratoryTest, id=test_id, completed=True)
    
    # Check if this patient is assigned to the physician
    is_assigned = PhysicianAssignment.objects.filter(
        patient=test.patient,
        physician=request.user,
        is_active=True
    ).exists()
    
    if not is_assigned:
        messages.error(request, 'You do not have access to this patient\'s lab results.')
        return redirect('b:physician_lab_results')
    
    # Build test results
    tests_results = []
    if test.malaria_parasite != 'PENDING':
        tests_results.append({
            'name': 'Malaria Parasite',
            'result': test.malaria_parasite,
            'status': 'Completed'
        })
    if test.random_blood_sugar is not None:
        tests_results.append({
            'name': 'Random Blood Sugar',
            'result': f"{test.random_blood_sugar} mmol/L",
            'status': 'Completed'
        })
    if test.hbsag != 'PENDING':
        tests_results.append({
            'name': 'HBsAg',
            'result': test.hbsag,
            'status': 'Completed'
        })
    if test.other_tests:
        tests_results.append({
            'name': 'Other Tests',
            'result': test.other_tests,
            'status': 'Completed'
        })
    
    context = {
        'test': test,
        'page': 'lab_result_detail',
        'patient': test.patient,
        'tests_results': tests_results,
        'page': 'lab_result_detail',
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
    return render(request, 'b/doctor/lab_result_detail.html', context)


# ============= PHYSICIAN OPTICIAN RESULTS VIEWS =============

@login_required
@role_required(['PHYSICIAN'])
def physician_optician_results(request):
    """List all optician results for the physician's patients"""
    assigned_patients = Patient.objects.filter(
        physicianassignment__physician=request.user,
        physicianassignment__is_active=True
    )
    
    assessments = OpticalAssessment.objects.filter(
        patient__in=assigned_patients,
        completed=True
    ).select_related('patient').order_by('-completed_at')
    
    # ===== FIX: Mark optician results as viewed by physician =====
    unviewed_assessments = assessments.filter(viewed_by_physician=False)
    if unviewed_assessments.exists():
        now = timezone.now()
        updated_count = unviewed_assessments.update(
            viewed_by_physician=True, 
            viewed_by_physician_at=now
        )
        print(f"👨‍⚕️ Marked {updated_count} optician results as viewed by physician")
    
    total_results = assessments.count()
    unique_patients = assessments.values('patient').distinct().count()
    unviewed_count = assessments.filter(viewed_by_physician=False).count()
    
    # Build result data
    results = []
    for assessment in assessments:
        results.append({
            'assessment': assessment,
            'patient': assessment.patient,
            'visual_acuity': f"{assessment.visual_acuity_left}/{assessment.visual_acuity_right}" if assessment.visual_acuity_left else "Not recorded",
            'glasses': f"{assessment.glasses_allocated} ({assessment.glasses_type})" if assessment.glasses_allocated > 0 else "None",
            'completed_at': assessment.completed_at,
            'status': 'Completed' if assessment.completed else 'Pending',
            'viewed': assessment.viewed_by_physician
        })
    
    # Count for sidebar badge (unviewed)
    lab_results_count = LaboratoryTest.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).count()
    
    optician_results_count = OpticalAssessment.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).count()
    
    context = {
        'results': results,
        'total_results': total_results,
        'unique_patients': unique_patients,
        'unviewed_count': unviewed_count,
        'page': 'optician_results',
        'lab_results_count': lab_results_count,
        'optician_results_count': optician_results_count,
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
    return render(request, 'b/doctor/optician_results.html', context)



@login_required
def mark_lab_results_read(request):
    """Mark all lab and optician results as read for the current physician"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        if profile.role != 'PHYSICIAN':
            return JsonResponse({'error': 'Not a physician'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=403)
    
    # Get patients assigned to this physician
    assigned_patients = Patient.objects.filter(
        physicianassignment__physician=request.user,
        physicianassignment__is_active=True
    )
    
    # Mark all unviewed lab tests as viewed
    updated_lab = LaboratoryTest.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).update(
        viewed_by_physician=True, 
        viewed_at=timezone.now()
    )
    
    # Mark all unviewed optician assessments as viewed
    updated_optician = OpticalAssessment.objects.filter(
        patient__in=assigned_patients,
        completed=True,
        viewed_by_physician=False
    ).update(
        viewed_by_physician=True, 
        viewed_at=timezone.now()
    )
    
    return JsonResponse({
        'success': True,
        'lab_results_marked': updated_lab,
        'optician_results_marked': updated_optician
    })




@login_required
@role_required(['PHYSICIAN'])
def physician_optician_result_detail(request, assessment_id):
    """View details of a specific optician result"""
    assessment = get_object_or_404(OpticalAssessment, id=assessment_id, completed=True)
    
    # Check if this patient is assigned to the physician
    is_assigned = PhysicianAssignment.objects.filter(
        patient=assessment.patient,
        physician=request.user,
        is_active=True
    ).exists()
    
    if not is_assigned:
        messages.error(request, 'You do not have access to this patient\'s optician results.')
        return redirect('b:physician_optician_results')
    
    context = {
        'assessment': assessment,
        'patient': assessment.patient,
        'page': 'optician_result_detail',
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
    return render(request, 'b/doctor/optician_result_detail.html', context)

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

    # Patients whose prescriptions have been dispensed, with their latest vitals.
    dispensed_patients = Patient.objects.filter(
        pharmacy_orders__dispensed=True
    ).annotate(
        last_dispensed_at=Max('pharmacy_orders__dispensed_at')
    ).prefetch_related(
        Prefetch(
            'nursing_assessments',
            queryset=NursingAssessment.objects.order_by('-completed_at', '-created_at'),
            to_attr='latest_nursing_assessments'
        )
    ).order_by('-last_dispensed_at')
    
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
        'dispensed_patients': dispensed_patients,
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
        drug_ids = request.POST.getlist('drug_ids[]')  # NEW: Get drug IDs from inventory selection
        
        if not selected_drugs:
            messages.error(request, 'Please select at least one drug to dispense.')
            return redirect('b:pharmacy_dispense_patient', patient_id=patient_id)
        
        dispensed_count = 0
        dispensed_order_ids = []
        failed_orders = []
        
        for i, order_id in enumerate(selected_drugs):
            order = get_object_or_404(PharmacyOrder, id=order_id, patient=patient, dispensed=False)
            quantity = int(quantities[i]) if i < len(quantities) and quantities[i] else order.quantity
            
            # ===== FIX: Get the selected drug from inventory =====
            drug_id = drug_ids[i] if i < len(drug_ids) and drug_ids[i] else None
            drug = None
            
            if drug_id:
                try:
                    drug = Drug.objects.get(id=drug_id, is_active=True)
                    
                    if drug.quantity < quantity:
                        failed_orders.append({
                            'drug_name': drug.name,
                            'available': drug.quantity,
                            'requested': quantity
                        })
                        continue
                    
                    # Deduct from inventory
                    drug.quantity -= quantity
                    drug.save()
                    
                except Drug.DoesNotExist:
                    messages.warning(request, f'Selected drug not found in inventory.')
                    continue
            else:
                # ===== If no drug selected, try to find by name =====
                try:
                    drug = Drug.objects.get(name__iexact=order.drug_name, is_active=True)
                    if drug.quantity >= quantity:
                        drug.quantity -= quantity
                        drug.save()
                    else:
                        failed_orders.append({
                            'drug_name': drug.name,
                            'available': drug.quantity,
                            'requested': quantity
                        })
                        continue
                except Drug.DoesNotExist:
                    # No matching drug found, dispense without stock deduction
                    drug = None
                    messages.warning(request, f'Drug "{order.drug_name}" not found in inventory. Dispensed without stock deduction.')
            
            # ===== Create dispensing record (drug can be None) =====
            PharmacyDispensing.objects.create(
                patient=patient,
                prescription=order,
                drug=drug,  # Can be None
                quantity_dispensed=quantity,
                dispensed_by=request.user,
                notes=f'Dispensed {quantity} units. Drug: {drug.name if drug else "Not in inventory"}'
            )
            
            order.dispensed = True
            order.dispensed_at = timezone.now()
            order.dispensed_by = request.user
            order.save()
            
            dispensed_count += 1
            dispensed_order_ids.append(order.id)
        
        # Mark notifications as read
        if dispensed_order_ids:
            for order_id in dispensed_order_ids:
                Notification.objects.filter(
                    recipient=request.user,
                    link__icontains=f'/pharmacy/dispense/{order_id}/'
                ).update(is_read=True)
            
            Notification.objects.filter(
                recipient=request.user,
                link__icontains=f'/pharmacy/dispense-patient/{patient.id}/'
            ).update(is_read=True)
        
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
    
    # GET request - show the dispense form
    drugs = Drug.objects.filter(is_active=True, quantity__gt=0).order_by('name')
    
    context = {
        'patient': patient,
        'pending_orders': pending_orders,
        'formatted_age': formatted_age,
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

@login_required
def pharmacy_notification_check(request):
    """API endpoint for pharmacy to check new prescriptions"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        if profile.role != 'PHARMACY':
            return JsonResponse({'error': 'Not pharmacy'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=401)
    
    # Get pending pharmacy orders
    pending_orders = PharmacyOrder.objects.filter(dispensed=False)
    
    # ===== FIX: Count UNIQUE patients with pending orders =====
    pending_patients = Patient.objects.filter(
        pharmacy_orders__dispensed=False
    ).distinct()
    patient_count = pending_patients.count()
    
    # Get count of orders
    order_count = pending_orders.count()
    
    # Get recent orders (last 24 hours)
    from datetime import timedelta
    yesterday = timezone.now() - timedelta(days=1)
    recent_orders = pending_orders.filter(created_at__gt=yesterday)
    
    # Include order details with IDs
    recent_orders_data = []
    for order in recent_orders:
        recent_orders_data.append({
            'id': order.id,
            'patient_name': order.patient.full_name,
            'patient_id': order.patient.id,
            'drug_name': order.drug_name,
            'quantity': order.quantity,
            'created_at': order.created_at.isoformat(),
        })
    
    return JsonResponse({
        'count': order_count,           
        'patient_count': patient_count,  
        'recent_count': recent_orders.count(),
        'has_new': recent_orders.count() > 0,
        'recent_orders': recent_orders_data,
    })


# ============= PHARMACY DRUG MANAGEMENT VIEWS =============

@login_required
@role_required(['PHARMACY'])
def pharmacy_drug_list(request):
    """List all drugs with inventory status"""
    drugs = Drug.objects.all().order_by('name')
    
    # Low stock alert
    low_stock = drugs.filter(quantity__lte=models.F('reorder_level'))
    low_stock_count = low_stock.count()
    
    # Calculate in-stock count (active drugs that are not low stock)
    in_stock_count = drugs.filter(
        is_active=True,
        quantity__gt=models.F('reorder_level')
    ).count()
    
    # Inactive count
    inactive_count = drugs.filter(is_active=False).count()
    
    context = {
        'drugs': drugs,
        'low_stock': low_stock,
        'low_stock_count': low_stock_count,
        'in_stock_count': in_stock_count,  # NEW
        'inactive_count': inactive_count,   # NEW
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


@login_required
@role_required(['PHARMACY'])
def pharmacy_drug_bulk_add(request):
    """Bulk add drugs from a list"""
    if request.method == 'POST':
        drug_list = request.POST.get('drug_list', '')
        category = request.POST.get('category', 'OTHER')
        default_quantity = request.POST.get('quantity', 0)
        reorder_level = request.POST.get('reorder_level', 10)
        
        if not drug_list:
            messages.error(request, 'Please enter at least one drug')
            return redirect('b:pharmacy_drug_bulk_add')
        
        # Parse the drug list (one per line)
        lines = drug_list.strip().split('\n')
        added_count = 0
        skipped_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove numbering like "1. " or "1)" or "1-"
            import re
            cleaned = re.sub(r'^[\d]+[\.\)\-]\s*', '', line)
            
            # Try to extract name and quantity
            # Format: "Drug Name = Quantity" or "Drug Name"
            if '=' in cleaned or ':' in cleaned:
                parts = re.split(r'[=:]', cleaned, 1)
                drug_name = parts[0].strip()
                # Extract quantity from the second part (remove text like "tabs", "caps", etc.)
                qty_part = parts[1].strip() if len(parts) > 1 else ''
                qty_match = re.search(r'([\d,]+)', qty_part)
                if qty_match:
                    qty_str = qty_match.group(1).replace(',', '')
                    try:
                        quantity = int(qty_str)
                    except:
                        quantity = int(default_quantity)
                else:
                    quantity = int(default_quantity)
            else:
                # Just the drug name with no quantity specified
                drug_name = cleaned
                quantity = int(default_quantity)
            
            # Check if drug already exists
            if Drug.objects.filter(name__iexact=drug_name).exists():
                skipped_count += 1
                continue
            
            # Create the drug
            Drug.objects.create(
                name=drug_name,
                category=category,
                quantity=quantity,
                reorder_level=int(reorder_level) if reorder_level else 10,
                is_active=True
            )
            added_count += 1
        
        if added_count > 0:
            messages.success(
                request, 
                f'✅ Added {added_count} drug(s). Skipped {skipped_count} duplicate(s).'
            )
        else:
            messages.warning(
                request, 
                f'⚠️ No drugs added. {skipped_count} duplicate(s) skipped.'
            )
        
        return redirect('b:pharmacy_drug_list')
    
    context = {
        'page': 'pharmacy_drug_add',
        'role': get_user_role(request.user),
        'categories': Drug.CATEGORY_CHOICES,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    }
    return render(request, 'b/pharmacy/drug_bulk_add.html', context)


# ============= LABORATORY VIEWS =============



@login_required
@role_required(['MLS'])
def laboratory_dashboard(request):
    # ===== FIX: Count UNIQUE patients with pending tests, not individual tests =====
    pending_tests = LaboratoryTest.objects.filter(completed=False)
    
    # Get unique patients with pending tests
    pending_patients = Patient.objects.filter(
        lab_tests__completed=False
    ).distinct().order_by('-created_at')
    
    # Annotate each patient with their pending test count
    from django.db.models import Count, Q
    pending_patients = pending_patients.annotate(
        pending_test_count=Count('lab_tests', filter=Q(lab_tests__completed=False))
    )
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    # Calculate average turnaround time (optional)
    completed_tests = LaboratoryTest.objects.filter(
        completed=True,
        completed_at__date=timezone.now().date()
    )
    
    context = {
        'tests': pending_tests,  # All pending tests (for detailed view)
        'pending_patients': pending_patients,  # Unique patients with pending tests
        'page': 'lab',
        'role': get_user_role(request.user),
        # ===== FIX: Use PATIENT count for the badge =====
        'pending_count': pending_patients.count(),  # Unique patients
        'pending_test_count': pending_tests.count(),  # Total tests (for reference)
        'completed_today': completed_tests.count(),
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

@login_required
def mls_notification_check(request):
    """API endpoint for MLS to check new lab test requests"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        if profile.role != 'MLS':
            return JsonResponse({'error': 'Not MLS'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=401)
    
    # Get pending lab tests
    pending_tests = LaboratoryTest.objects.filter(completed=False)
    
    # Count UNIQUE patients with pending tests
    pending_patients = Patient.objects.filter(
        lab_tests__completed=False
    ).distinct()
    patient_count = pending_patients.count()
    
    # Get count of tests
    test_count = pending_tests.count()
    
    # Get recent tests (last 24 hours)
    from datetime import timedelta
    yesterday = timezone.now() - timedelta(days=1)
    recent_tests = pending_tests.filter(created_at__gt=yesterday)
    
    # Include test details with IDs
    recent_tests_data = []
    for test in recent_tests:
        tests_summary = []
        if test.malaria_parasite == 'PENDING':
            tests_summary.append('Malaria')
        if test.hbsag == 'PENDING':
            tests_summary.append('HBsAg')
        if test.random_blood_sugar is None:
            tests_summary.append('RBS')
        if test.other_tests:
            tests_summary.append(test.other_tests)
        
        recent_tests_data.append({
            'id': test.id,
            'patient_name': test.patient.full_name,
            'patient_id': test.patient.id,
            'tests_requested': ', '.join(tests_summary) if tests_summary else 'Standard tests',
            'created_at': test.created_at.isoformat(),
        })
    
    return JsonResponse({
        'count': test_count,
        'patient_count': patient_count,
        'recent_count': recent_tests.count(),
        'has_new': recent_tests.count() > 0,
        'recent_tests': recent_tests_data,
    })



# ============= OPTICIAN VIEWS =============


@login_required
@role_required(['OPTOMETRIST'])
def optician_dashboard(request):
    print("=" * 50)
    print("🔍 OPTICIAN DASHBOARD DEBUG")
    print(f"👤 User: {request.user.username}")
    
    # Check ALL assessments
    all_assessments = OpticalAssessment.objects.all()
    print(f"📊 Total assessments in DB: {all_assessments.count()}")
    
    for a in all_assessments:
        print(f"   - ID: {a.id}, Patient: {a.patient.full_name}, Completed: {a.completed}, Viewed: {a.viewed_by_optician}")
    
    # ===== FIX: Only count UNVIEWED pending assessments =====
    pending_assessments = OpticalAssessment.objects.filter(
        completed=False,
        viewed_by_optician=False
    )
    print(f"📊 Unviewed pending assessments: {pending_assessments.count()}")
    
    # Get unique patients with unviewed pending assessments
    pending_patients = Patient.objects.filter(
        optical_assessments__completed=False,
        optical_assessments__viewed_by_optician=False
    ).distinct().order_by('-created_at')
    
    patient_count = pending_patients.count()
    print(f"📊 Unique patients with unviewed pending assessments: {patient_count}")
    
    # Annotate each patient with their pending assessment count
    from django.db.models import Count, Q
    pending_patients = pending_patients.annotate(
        pending_assessment_count=Count('optical_assessments', filter=Q(
            optical_assessments__completed=False,
            optical_assessments__viewed_by_optician=False
        ))
    )
    
    walk_in_count = OpticalAssessment.objects.filter(
        is_walk_in=True,
        completed=False,
        viewed_by_optician=False
    ).count()
    
    completed_today = OpticalAssessment.objects.filter(
        completed=True,
        completed_at__date=timezone.now().date()
    ).count()
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    # Get unread notification count for navbar
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    print("=" * 50)
    
    context = {
        'assessments': pending_assessments,
        'pending_patients': pending_patients,
        'page': 'optician',
        'role': get_user_role(request.user),
        'pending_count': pending_patients.count(),
        'pending_assessment_count': pending_assessments.count(),
        'walk_in_count': walk_in_count,
        'completed_today': completed_today,
        'notifications': notifications,
        'notification_count': unread_count
    }
    return render(request, 'b/optician/dashboard.html', context)




@login_required
@role_required(['OPTOMETRIST'])
def optician_assessment(request, patient_id=None):
    # For walk-in patients
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
        
        # ===== FIX: Check if there's already a pending assessment for this patient =====
        existing_assessment = OpticalAssessment.objects.filter(
            patient=patient,
            completed=False
        ).first()
    else:
        patient = None
        existing_assessment = None
    
    if request.method == 'POST':
        form = OpticalAssessmentForm(request.POST)
        if form.is_valid():
            if existing_assessment:
                # ===== UPDATE existing assessment instead of creating new =====
                assessment = existing_assessment
                # Update fields from form
                assessment.visual_acuity_left = form.cleaned_data.get('visual_acuity_left', '')
                assessment.visual_acuity_right = form.cleaned_data.get('visual_acuity_right', '')
                assessment.refractive_error = form.cleaned_data.get('refractive_error', '')
                assessment.eye_health_notes = form.cleaned_data.get('eye_health_notes', '')
                assessment.glasses_allocated = form.cleaned_data.get('glasses_allocated', 0)
                assessment.glasses_type = form.cleaned_data.get('glasses_type', '')
                assessment.glasses_prescription = form.cleaned_data.get('glasses_prescription', '')
                assessment.is_walk_in = form.cleaned_data.get('is_walk_in', False)
                assessment.updated_by = request.user
                assessment.updated_at = timezone.now()
            else:
                # ===== Create NEW assessment =====
                assessment = form.save(commit=False)
                assessment.patient = patient
                assessment.created_by = request.user
            
            # ===== Mark as completed and viewed =====
            assessment.completed = True
            assessment.completed_at = timezone.now()
            assessment.completed_by = request.user
            assessment.viewed_by_optician = True
            assessment.viewed_at = timezone.now()
            assessment.save()
            
            print("=" * 50)
            print("🔍 OPTICIAN ASSESSMENT COMPLETED")
            print(f"👤 Optician: {request.user.username}")
            print(f"📊 Assessment ID: {assessment.id}")
            print(f"📊 Patient: {assessment.patient.full_name}")
            print(f"📊 Completed: {assessment.completed}")
            print(f"📊 Viewed by Optician: {assessment.viewed_by_optician}")
            print("=" * 50)
            
            if patient:
                # Update workflow
                workflow = PatientWorkflow.objects.get(patient=patient)
                workflow.optician_completed = True
                workflow.optician_completed_at = timezone.now()
                workflow.current_stage = 'COMPLETED'
                workflow.completed_at = timezone.now()
                patient.current_stage = 'COMPLETED'
                patient.save()
                workflow.save()
                
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
                from datetime import date
                import random
                
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
        # ===== FIX: Pass existing assessment data to form =====
        if existing_assessment:
            form = OpticalAssessmentForm(instance=existing_assessment)
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
    
    # ===== FIX: Only count UNVIEWED pending assessments =====
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


# ============= USER MANAGEMENT VIEWS =============

@login_required
@role_required(['HIM'])
# @staff_member_required
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




@login_required
def nurse_assignment_check(request):
    """API endpoint for nurses to check if they have new assignments"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    # Check if user is a nurse
    try:
        profile = request.user.userprofile
        if profile.role != 'NURSE':
            return JsonResponse({'error': 'Not a nurse'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=403)
    
    # Get ALL active assignments for this nurse (NOT filtered by date)
    all_assignments = NurseAssignment.objects.filter(
        nurse=request.user,
        is_active=True
    ).select_related('patient').order_by('-assigned_at')
    
    # Get count
    count = all_assignments.count()
    
    # Get details for the assignments
    assignments_data = []
    for assignment in all_assignments:
        assignments_data.append({
            'id': assignment.id,
            'patient_id': assignment.patient.id,
            'patient_name': assignment.patient.full_name,
            'hospital_number': assignment.patient.hospital_number,
            'assigned_at': assignment.assigned_at.isoformat(),
        })
    
    # Log for debugging
    print(f"👩‍⚕️ Nurse {request.user.username} has {count} assignments")
    
    return JsonResponse({
        'count': count,
        'assignments': assignments_data,
    })


@login_required
def nurse_assignment_debug(request):
    """Debug endpoint to check nurse assignments"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        if profile.role != 'NURSE':
            return JsonResponse({'error': 'Not a nurse'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=403)
    
    # Get ALL active assignments for this nurse
    all_assignments = NurseAssignment.objects.filter(
        nurse=request.user,
        is_active=True
    ).select_related('patient').order_by('-assigned_at')
    
    # Get assignments from the last 24 hours
    from datetime import datetime, timedelta
    yesterday = datetime.now() - timedelta(days=1)
    recent_assignments = all_assignments.filter(assigned_at__gt=yesterday)
    
    data = {
        'total_assignments': all_assignments.count(),
        'recent_assignments': recent_assignments.count(),
        'assignments': []
    }
    
    for assignment in all_assignments[:10]:
        data['assignments'].append({
            'id': assignment.id,
            'patient_id': assignment.patient.id,
            'patient_name': assignment.patient.full_name,
            'hospital_number': assignment.patient.hospital_number,
            'assigned_at': assignment.assigned_at.isoformat(),
            'is_active': assignment.is_active
        })
    
    return JsonResponse(data)




@login_required
def dashboard_data_api(request):
    """API endpoint for dashboard data refresh"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = request.user.userprofile
        role = profile.role
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No profile'}, status=403)
    
    data = {
        'role': role,
        'notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count(),
    }
    
    if role == 'HIM':
        data.update({
            'total_patients': Patient.objects.count(),
            'today_patients': Patient.objects.filter(created_at__date=date.today()).count(),
            'pending_nursing': Patient.objects.filter(current_stage='REGISTERED').count(),
            'pending_doctor': Patient.objects.filter(current_stage='NURSING').count(),
            'pending_pharmacy': Patient.objects.filter(current_stage='PHARMACY').count(),
            'pending_lab': Patient.objects.filter(current_stage='LABORATORY').count(),
            'pending_optician': Patient.objects.filter(current_stage='OPTICIAN').count(),
        })
        
    elif role == 'NURSE':
        assigned_patients = Patient.objects.filter(
            nurseassignment__nurse=request.user,
            nurseassignment__is_active=True
        )
        pending_count = assigned_patients.filter(current_stage='REGISTERED').count()
        
        # Check for new assignments
        last_check = request.session.get('nurse_last_check', None)
        new_assignments = 0
        if last_check:
            try:
                if isinstance(last_check, str):
                    last_check_dt = datetime.fromisoformat(last_check)
                else:
                    last_check_dt = last_check
                new_assignments = NurseAssignment.objects.filter(
                    nurse=request.user,
                    assigned_at__gt=last_check_dt
                ).count()
            except:
                pass
        
        data.update({
            'pending_count': pending_count,
            'new_assignments': new_assignments,
            'has_new_assignments': new_assignments > 0,
            'patients': [
                {
                    'id': p.id,
                    'full_name': p.full_name,
                    'hospital_number': p.hospital_number,
                    'gender': p.gender,
                    'age_data': p.age_data,
                } for p in assigned_patients.filter(current_stage='REGISTERED')
            ],
        })
        
    elif role == 'PHYSICIAN':
        patients = Patient.objects.filter(
            physicianassignment__physician=request.user,
            physicianassignment__is_active=True,
            current_stage='NURSING'
        )
        data.update({
            'pending_count': patients.count(),
            'patients': [
                {
                    'id': p.id,
                    'full_name': p.full_name,
                    'hospital_number': p.hospital_number,
                    'gender': p.gender,
                    'age_data': p.age_data,
                } for p in patients
            ],
        })
        
    elif role == 'PHARMACY':
        pending_orders = PharmacyOrder.objects.filter(dispensed=False)
        pending_patients = Patient.objects.filter(
            pharmacy_orders__dispensed=False
        ).distinct()
        
        # Build patient data with their orders
        patient_data = []
        for p in pending_patients:
            orders = p.pharmacy_orders.filter(dispensed=False)
            patient_data.append({
                'id': p.id,
                'full_name': p.full_name,
                'hospital_number': p.hospital_number,
                'phone': p.phone,
                'age_display': f"{p.age_data.years}y" if p.age_data and p.age_data.years > 0 else '—',
                'medications': [
                    {
                        'drug_name': o.drug_name,
                        'quantity': o.quantity,
                    } for o in orders
                ],
            })
        
        data.update({
            'pending_count': pending_orders.count(),
            'pending_patients_count': pending_patients.count(),
            'dispensed_today': PharmacyOrder.objects.filter(
                dispensed=True,
                dispensed_at__date=date.today()
            ).count(),
            'low_stock_count': Drug.objects.filter(
                quantity__lte=F('reorder_level')
            ).count(),
            'pending_patients': patient_data,
        })
        
    elif role == 'MLS':
        tests = LaboratoryTest.objects.filter(completed=False)
        data.update({
            'pending_count': tests.count(),
            'tests': [
                {
                    'id': t.id,
                    'patient_name': t.patient.full_name,
                    'malaria_parasite': t.malaria_parasite,
                    'random_blood_sugar': str(t.random_blood_sugar) if t.random_blood_sugar else None,
                    'hbsag': t.hbsag,
                } for t in tests
            ],
        })
        
    elif role == 'OPTOMETRIST':
        assessments = OpticalAssessment.objects.filter(completed=False)
        data.update({
            'pending_count': assessments.count(),
            'assessments': [
                {
                    'id': a.id,
                    'patient_id': a.patient.id,
                    'patient_name': a.patient.full_name,
                    'is_walk_in': a.is_walk_in,
                    'glasses_allocated': a.glasses_allocated,
                } for a in assessments
            ],
        })
    
    return JsonResponse(data)
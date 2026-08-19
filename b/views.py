# b/views


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
import random
import string
from .models import *
from .forms import *
from django.contrib.auth.models import User, Group
from django.template.loader import render_to_string

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
        })
    elif role == 'PHARMACY':
        orders = PharmacyOrder.objects.filter(dispensed=False)
        context.update({
            'pending_orders': orders.count(),
            'orders': orders,
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
    workflow = get_object_or_404(PatientWorkflow, patient=patient)
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
    workflow = get_object_or_404(PatientWorkflow, patient=patient)
    
    if request.method == 'POST':
        form = NursingAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.patient = patient
            assessment.created_by = request.user
            assessment.completed = True
            assessment.completed_at = timezone.now()
            assessment.save()
            
            # Update workflow
            workflow.nursing_completed = True
            workflow.nursing_completed_at = timezone.now()
            workflow.current_stage = 'NURSING'
            patient.current_stage = 'NURSING'
            patient.save()
            workflow.save()
            
            # Notification is sent via signal
            messages.success(request, f'Nursing assessment completed for {patient.full_name}')
            return redirect('b:nursing_dashboard')
    else:
        form = NursingAssessmentForm()
    
    context = {
        'patient': patient, 
        'form': form, 
        'page': 'nursing',
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
    workflow = get_object_or_404(PatientWorkflow, patient=patient)
    nursing = NursingAssessment.objects.filter(patient=patient).first()
    
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
            
            # Update workflow
            workflow.doctor_completed = True
            workflow.doctor_completed_at = timezone.now()
            
            # Determine next stage based on referrals
            if consultation.refer_to_pharmacy:
                workflow.current_stage = 'PHARMACY'
                patient.current_stage = 'PHARMACY'
                # Create pharmacy order
                PharmacyOrder.objects.create(
                    patient=patient,
                    consultation=consultation,
                    drug_name='Prescribed medication',
                    quantity=1,
                    created_by=request.user
                )
            elif consultation.refer_to_laboratory:
                workflow.current_stage = 'LABORATORY'
                patient.current_stage = 'LABORATORY'
                # Create lab test
                LaboratoryTest.objects.create(
                    patient=patient,
                    consultation=consultation,
                    created_by=request.user
                )
            elif consultation.refer_to_optician:
                workflow.current_stage = 'OPTICIAN'
                patient.current_stage = 'OPTICIAN'
                # Create optical assessment
                OpticalAssessment.objects.create(
                    patient=patient,
                    consultation=consultation,
                    created_by=request.user
                )
            else:
                workflow.current_stage = 'COMPLETED'
                patient.current_stage = 'COMPLETED'
                workflow.completed_at = timezone.now()
            
            patient.save()
            workflow.save()
            
            # Notification is sent via signal
            messages.success(request, f'Consultation completed for {patient.full_name}')
            return redirect('b:doctor_dashboard')
    else:
        form = MedicalConsultationForm()
    
    context = {
        'patient': patient,
        'form': form,
        'nursing': nursing,
        'page': 'doctor',
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
        physicianassignment__is_active=True,
        current_stage='NURSING'
    )
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'patients': assigned_patients,
        'page': 'doctor',
        'pending_count': assigned_patients.count(),
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
    orders = PharmacyOrder.objects.filter(dispensed=False)
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'orders': orders,
        'page': 'pharmacy',
        'pending_count': orders.count(),
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
    order = get_object_or_404(PharmacyOrder, id=order_id)
    
    if request.method == 'POST':
        order.dispensed = True
        order.dispensed_at = timezone.now()
        order.dispensed_by = request.user
        order.save()
        
        # Check if all pharmacy orders for this patient are dispensed
        patient_orders = PharmacyOrder.objects.filter(
            patient=order.patient, 
            dispensed=False
        )
        if not patient_orders.exists():
            workflow = PatientWorkflow.objects.get(patient=order.patient)
            workflow.pharmacy_completed = True
            workflow.pharmacy_completed_at = timezone.now()
            
            # Move to next stage or complete
            if workflow.current_stage == 'PHARMACY':
                # Check if there are other referrals
                consultation = MedicalConsultation.objects.filter(
                    patient=order.patient
                ).first()
                if consultation:
                    if consultation.refer_to_laboratory:
                        workflow.current_stage = 'LABORATORY'
                        order.patient.current_stage = 'LABORATORY'
                    elif consultation.refer_to_optician:
                        workflow.current_stage = 'OPTICIAN'
                        order.patient.current_stage = 'OPTICIAN'
                    else:
                        workflow.current_stage = 'COMPLETED'
                        order.patient.current_stage = 'COMPLETED'
                        workflow.completed_at = timezone.now()
                    order.patient.save()
                workflow.save()
        
        messages.success(request, f'Medication dispensed for {order.patient.full_name}')
        return redirect('b:pharmacy_dashboard')
    
    context = {
        'order': order, 
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
    return render(request, 'b/pharmacy/dispense.html', context)

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
            if consultation and consultation.refer_to_optician:
                workflow.current_stage = 'OPTICIAN'
                test.patient.current_stage = 'OPTICIAN'
            else:
                workflow.current_stage = 'COMPLETED'
                test.patient.current_stage = 'COMPLETED'
                workflow.completed_at = timezone.now()
            
            test.patient.save()
            workflow.save()
            
            # Notification is sent via signal
            messages.success(request, f'Lab test completed for {test.patient.full_name}')
            return redirect('b:laboratory_dashboard')
    else:
        form = LaboratoryTestForm(instance=test)
    
    context = {
        'test': test, 
        'form': form, 
        'page': 'lab',
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
            else:
                # Walk-in patient
                assessment.save()
                messages.success(request, 'Optical assessment completed for walk-in patient')
            
            return redirect('b:optician_dashboard')
    else:
        form = OpticalAssessmentForm()
    
    context = {
        'patient': patient,
        'form': form,
        'page': 'optician',
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
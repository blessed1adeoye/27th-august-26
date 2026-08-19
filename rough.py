# Add these imports at the top
from django.contrib.auth.models import User
from django.db.models import Q

# Add these new models if not already present
class NurseAssignment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_patients')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assignments_made')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('patient', 'nurse')

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:50]}"

# HIM: Assign Nurse View
@login_required
@role_required(['HIM'])
def assign_nurse(request):
    # Get patients that are registered but not yet assigned
    unassigned_patients = Patient.objects.filter(
        current_stage='REGISTERED'
    ).exclude(
        id__in=NurseAssignment.objects.filter(is_active=True).values_list('patient_id', flat=True)
    )
    
    # Get all nurses
    nurses = User.objects.filter(userprofile__role='NURSE')
    
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        nurse_id = request.POST.get('nurse_id')
        
        if patient_id and nurse_id:
            patient = get_object_or_404(Patient, id=patient_id)
            nurse = get_object_or_404(User, id=nurse_id)
            
            # Create assignment
            assignment = NurseAssignment.objects.create(
                patient=patient,
                nurse=nurse,
                assigned_by=request.user
            )
            
            # Create notification for nurse
            Notification.objects.create(
                recipient=nurse,
                message=f'You have been assigned to patient {patient.full_name} (ID: {patient.hospital_number})',
                link=f'/nursing/assessment/{patient.id}/'
            )
            
            messages.success(request, f'Patient {patient.full_name} assigned to {nurse.get_full_name()}')
            return redirect('b:assign_nurse')
    
    context = {
        'page': 'assign',
        'unassigned_patients': unassigned_patients,
        'nurses': nurses,
        'pending_assignments': unassigned_patients.count()
    }
    return render(request, 'b/him/assign_nurse.html', context)

# Update nursing_dashboard to show assigned patients
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
        'completed_today': assigned_patients.filter(
            current_stage='NURSING',
            updated_at__date=timezone.now().date()
        ).count()
    }
    return render(request, 'b/nurse/dashboard.html', context)

# Update patient_registration to redirect to assign page
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
    }
    return render(request, 'b/him/patient_registration.html', context)
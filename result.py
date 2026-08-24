forms.py

class NursingAssessmentForm(forms.ModelForm):
    class Meta:
        model = NursingAssessment
        fields = [
            'blood_pressure_systolic', 'blood_pressure_diastolic', 
            'pulse_rate', 'temperature', 'respiratory_rate', 'oxygen_saturation',
            'biohazard_risk', 'isolation_required', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'biohazard_risk': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields not required (optional for children)
        for field_name in self.fields:
            self.fields[field_name].required = False
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if isinstance(field, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            if isinstance(field, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'




class LaboratoryTestForm(forms.ModelForm):
    class Meta:
        model = LaboratoryTest
        fields = [
            'malaria_parasite', 'random_blood_sugar', 
            'hbsag', 'other_tests', 'notes'
        ]
        widgets = {
            'other_tests': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if isinstance(field, forms.Select):
                field.widget.attrs['class'] = 'form-select'


class OpticalAssessmentForm(forms.ModelForm):
    # Walk-in patient fields
    first_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    gender = forms.ChoiceField(choices=[('', 'Select Gender'), ('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')], required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}))
    
    class Meta:
        model = OpticalAssessment
        fields = [
            'is_walk_in', 'visual_acuity_left', 'visual_acuity_right',
            'refractive_error', 'eye_health_notes', 'glasses_allocated',
            'glasses_type', 'glasses_prescription'
        ]
        widgets = {
            'refractive_error': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'eye_health_notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'glasses_prescription': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if isinstance(field, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            if isinstance(field, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
    
    def clean(self):
        cleaned_data = super().clean()
        is_walk_in = cleaned_data.get('is_walk_in')
        
        # If walk-in, validate that we have basic patient info
        if is_walk_in:
            first_name = cleaned_data.get('first_name')
            last_name = cleaned_data.get('last_name')
            phone = cleaned_data.get('phone')
            
            if not first_name:
                self.add_error('first_name', 'First name is required for walk-in patients')
            if not last_name:
                self.add_error('last_name', 'Last name is required for walk-in patients')
            if not phone:
                self.add_error('phone', 'Phone number is required for walk-in patients')
        
        return cleaned_data



    


views.py

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




/models.py 

# ============= LABORATORY =============
class LaboratoryTest(AuditMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_tests')
    consultation = models.ForeignKey(
        MedicalConsultation, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='lab_tests'
    )
    
    # Tests (Only 3 tests now)
    malaria_parasite = models.CharField(
        max_length=20, 
        choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('PENDING', 'Pending')],
        default='PENDING'
    )
    random_blood_sugar = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Random Blood Sugar (mmol/L)"
    )
    hbsag = models.CharField(
        max_length=20,
        choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('PENDING', 'Pending')],
        default='PENDING'
    )
    
    # Additional tests
    other_tests = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Status
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='completed_lab_tests'
    )
    
    def __str__(self):
        return f"Lab Test - {self.patient.full_name}"


templates/b/optician/assessment.html

{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block title %}Optical Assessment{% endblock %}

{% block extra_css %}
<style>
    .walk-in-fields {
        display: none;
        background: #f8fafc;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        margin-bottom: 15px;
    }
    .walk-in-fields.show {
        display: block;
    }
</style>
{% endblock %}

{% block content %}
<div class="card card-custom">
    <div class="card-header">
        <h5 class="mb-0">
            <i class="fas fa-eye text-success me-2"></i>
            Optical Assessment
            {% if patient %}
                - {{ patient.full_name }}
            {% else %}
                - Walk-in Patient
            {% endif %}
        </h5>
    </div>
    <div class="card-body">
        {% if patient %}
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Performing optical assessment for <strong>{{ patient.full_name }}</strong>
                ({{ patient.hospital_number }})
            </div>
        {% else %}
            <div class="alert alert-warning">
                <i class="fas fa-user-plus me-2"></i>
                Registering a new walk-in patient. Please fill in all details.
            </div>
        {% endif %}
        
        <form method="post">
            {% csrf_token %}
            
            <!-- Walk-in Patient Fields -->
            <div class="walk-in-fields {% if not patient %}show{% endif %}" id="walkInFields">
                <h6 class="text-success border-bottom pb-2 mb-3"><i class="fas fa-user-plus me-2"></i>Walk-in Patient Information</h6>
                <div class="row">
                    <div class="col-md-6">{{ form.first_name|as_crispy_field }}</div>
                    <div class="col-md-6">{{ form.last_name|as_crispy_field }}</div>
                    <div class="col-md-4">{{ form.date_of_birth|as_crispy_field }}</div>
                    <div class="col-md-4">{{ form.gender|as_crispy_field }}</div>
                    <div class="col-md-4">{{ form.phone|as_crispy_field }}</div>
                </div>
            </div>
            
            <!-- Is Walk-in Checkbox -->
            <div class="form-check mb-3">
                <input type="checkbox" name="is_walk_in" id="id_is_walk_in" class="form-check-input" onchange="toggleWalkInFields()" {% if not patient %}checked{% endif %}>
                <label class="form-check-label" for="id_is_walk_in">
                    <strong>Walk-in Patient</strong>
                </label>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-success border-bottom pb-2"><i class="fas fa-eye me-2"></i>Visual Acuity</h6>
                    {{ form.visual_acuity_left|as_crispy_field }}
                    {{ form.visual_acuity_right|as_crispy_field }}
                </div>
                <div class="col-md-6">
                    <h6 class="text-success border-bottom pb-2"><i class="fas fa-glasses me-2"></i>Glasses Allocation</h6>
                    {{ form.glasses_allocated|as_crispy_field }}
                    {{ form.glasses_type|as_crispy_field }}
                </div>
            </div>
            
            {{ form.refractive_error|as_crispy_field }}
            {{ form.eye_health_notes|as_crispy_field }}
            {{ form.glasses_prescription|as_crispy_field }}
            
            <div class="mt-4 d-flex justify-content-between">
                <a href="{% url 'b:optician_dashboard' %}" class="btn btn-secondary">
                    <i class="fas fa-arrow-left me-2"></i> Back
                </a>
                <button type="submit" class="btn btn-success">
                    <i class="fas fa-save me-2"></i> Complete Assessment
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    function toggleWalkInFields() {
        const checkbox = document.getElementById('id_is_walk_in');
        const fields = document.getElementById('walkInFields');
        if (checkbox.checked) {
            fields.classList.add('show');
        } else {
            fields.classList.remove('show');
        }
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        toggleWalkInFields();
    });
</script>
{% endblock %}


b/urls.py


# Optician
path('optician/dashboard/', views.optician_dashboard, name='optician_dashboard'),
path('optician/assessment/', views.optician_assessment, name='optician_assessment_walkin'),
path('optician/assessment/<int:patient_id>/', views.optician_assessment, name='optician_assessment'),
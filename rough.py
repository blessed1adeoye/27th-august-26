with this form 

class NursingAssessmentForm(forms.ModelForm):
    class Meta:
        model = NursingAssessment
        fields = [
            'blood_pressure_systolic', 'blood_pressure_diastolic', 
            'pulse_rate', 'temperature', 'respiratory_rate', 'oxygen_saturation',
            'biohazard_risk', 'isolation_required', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'biohazard_risk': forms.Textarea(attrs={'rows': 2}),
        }


and this view 


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

SO i want the form not to be required because some children might be in the outreach
only this field are to be in the nursing_assessment

'blood_pressure_systolic', 'blood_pressure_diastolic', 'pulse_rate', 'temperature', 'respiratory_rate'




MLS 

with this form 

    class LaboratoryTestForm(forms.ModelForm):
    class Meta:
        model = LaboratoryTest
        fields = [
            'malaria_parasite', 'random_blood_sugar', 
            'hbsag', 'hcv', 'hiv', 'other_tests', 'notes'
        ]
        widgets = {
            'other_tests': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        } 

        and this view

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
but the test i want now is Malaria parasite, Random Blood Sugar and HBsAg

attending physiciian need to be notified when these tests are completed to see the result 

the referral of physician to the optician must not be more than 44 slot so here is the views and form
for optician 
class OpticalAssessmentForm(forms.ModelForm):
    class Meta:
        model = OpticalAssessment
        fields = [
            'is_walk_in', 'visual_acuity_left', 'visual_acuity_right',
            'refractive_error', 'eye_health_notes', 'glasses_allocated',
            'glasses_type', 'glasses_prescription'
        ]
        widgets = {
            'refractive_error': forms.Textarea(attrs={'rows': 2}),
            'eye_health_notes': forms.Textarea(attrs={'rows': 2}),
            'glasses_prescription': forms.Textarea(attrs={'rows': 2}),
        }
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
        'role': get_user_role(request.user),
        'page': 'optician_assessment',
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

and let there be a opportunity for walk in patient for optician 



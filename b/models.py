# b/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from datetime import date, timedelta
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
import json


class AuditMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='%(class)s_updated'
    )

    class Meta:
        abstract = True

class UserProfile(models.Model):
    USER_ROLES = [
        ('HIM', 'Health Information Manager'),
        ('NURSE', 'Nurse'),
        ('MLS', 'Medical Laboratory Scientist'),
        ('OPTOMETRIST', 'Optometrist'),
        ('PHYSICIAN', 'Physician'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=USER_ROLES)
    employee_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15)
    department = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"

class Patient(AuditMixin):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]
    
    hospital_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    
    # Status tracking
    is_admitted = models.BooleanField(default=False)
    current_stage = models.CharField(max_length=50, default='REGISTERED')
    
    def __str__(self):
        return f"{self.hospital_number} - {self.last_name}, {self.first_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name} {self.last_name}".strip()
    
    @property
    def age_data(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        dob = self.date_of_birth
        years = today.year - dob.year
        months = today.month - dob.month
        days = today.day - dob.day
        if days < 0:
            months -= 1
            prev_month = date(today.year, today.month, 1) - timedelta(days=1)
            days += prev_month.day
        if months < 0:
            years -= 1
            months += 12
        return {'years': years, 'months': months, 'days': days}

# ============= NURSING: Biohazard & Vitals =============
class NursingAssessment(AuditMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='nursing_assessments')
    
    # Vitals
    blood_pressure_systolic = models.IntegerField(help_text="Systolic BP (mmHg)")
    blood_pressure_diastolic = models.IntegerField(help_text="Diastolic BP (mmHg)")
    pulse_rate = models.IntegerField(help_text="Pulse rate (beats/min)")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    oxygen_saturation = models.IntegerField(null=True, blank=True, help_text="SpO2 %")
    
    # Biohazard assessment
    biohazard_risk = models.TextField(blank=True, help_text="Any biohazard risks identified")
    isolation_required = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    # Status
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Nursing Assessment - {self.patient.full_name}"


class NurseAssignment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_patients')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assignments_made')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('patient', 'nurse')


# ============= DOCTOR: Medical Consultation =============
class MedicalConsultation(AuditMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='consultations')
    nursing_assessment = models.ForeignKey(
        NursingAssessment, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='consultations'
    )
    
    # Consultation
    symptoms = models.TextField(help_text="Patient's symptoms (open-ended)")
    diagnosis = models.TextField(help_text="Doctor's diagnosis (open-ended)")
    treatment_plan = models.TextField(blank=True)
    referral_notes = models.TextField(blank=True)
    
    # Referrals
    refer_to_pharmacy = models.BooleanField(default=False)
    refer_to_laboratory = models.BooleanField(default=False)
    refer_to_optician = models.BooleanField(default=False)
    refer_to_specialist = models.BooleanField(default=False)
    
    # Status
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Consultation - {self.patient.full_name}"


class PhysicianAssignment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    physician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_patients_physician')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assignments_made_physician')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('patient', 'physician')
    
    def __str__(self):
        return f"{self.patient.full_name} -> Dr. {self.physician.get_full_name()}"

# ============= PHARMACY =============
class PharmacyOrder(AuditMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='pharmacy_orders')
    consultation = models.ForeignKey(
        MedicalConsultation, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='pharmacy_orders'
    )
    
    # Drug items
    drug_name = models.CharField(max_length=200)
    quantity = models.IntegerField()
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    instructions = models.TextField(blank=True)
    
    # Status
    dispensed = models.BooleanField(default=False)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    dispensed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='dispensed_medications'
    )
    
    def __str__(self):
        return f"Pharmacy Order - {self.patient.full_name} - {self.drug_name}"

# ============= LABORATORY =============
class LaboratoryTest(AuditMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_tests')
    consultation = models.ForeignKey(
        MedicalConsultation, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='lab_tests'
    )
    
    # Tests
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
    hcv = models.CharField(
        max_length=20,
        choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('PENDING', 'Pending')],
        default='PENDING'
    )
    hiv = models.CharField(
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

# ============= OPTICIAN =============
class OpticalAssessment(AuditMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='optical_assessments')
    consultation = models.ForeignKey(
        MedicalConsultation, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='optical_assessments'
    )
    
    # Direct optician registration (for walk-ins)
    is_walk_in = models.BooleanField(default=False)
    
    # Assessment
    visual_acuity_left = models.CharField(max_length=20, blank=True, help_text="e.g., 6/6, 6/9")
    visual_acuity_right = models.CharField(max_length=20, blank=True)
    refractive_error = models.TextField(blank=True)
    eye_health_notes = models.TextField(blank=True)
    
    # Glasses allocation
    glasses_allocated = models.IntegerField(default=0, help_text="Number of glasses allocated")
    glasses_type = models.CharField(max_length=100, blank=True)
    glasses_prescription = models.TextField(blank=True)
    
    # Status
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='completed_optical_assessments'
    )
    
    def __str__(self):
        return f"Optical Assessment - {self.patient.full_name}"

# ============= WORKFLOW TRACKING =============
class PatientWorkflow(AuditMixin):
    WORKFLOW_STAGES = [
        ('REGISTERED', 'Registered'),
        ('NURSING', 'Nursing Assessment'),
        ('DOCTOR', 'Doctor Consultation'),
        ('PHARMACY', 'Pharmacy'),
        ('LABORATORY', 'Laboratory'),
        ('OPTICIAN', 'Optician'),
        ('COMPLETED', 'Completed'),
    ]
    
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='workflow')
    current_stage = models.CharField(max_length=20, choices=WORKFLOW_STAGES, default='REGISTERED')
    
    # Stage completion flags
    nursing_completed = models.BooleanField(default=False)
    doctor_completed = models.BooleanField(default=False)
    pharmacy_completed = models.BooleanField(default=False)
    laboratory_completed = models.BooleanField(default=False)
    optician_completed = models.BooleanField(default=False)
    
    # Timestamps
    nursing_completed_at = models.DateTimeField(null=True, blank=True)
    doctor_completed_at = models.DateTimeField(null=True, blank=True)
    pharmacy_completed_at = models.DateTimeField(null=True, blank=True)
    laboratory_completed_at = models.DateTimeField(null=True, blank=True)
    optician_completed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Workflow - {self.patient.full_name}"
    
    def get_next_stage(self):
        stages = ['REGISTERED', 'NURSING', 'DOCTOR', 'PHARMACY', 'LABORATORY', 'OPTICIAN', 'COMPLETED']
        current_index = stages.index(self.current_stage)
        return stages[current_index + 1] if current_index < len(stages) - 1 else None





# =============================NOTIFICATION SYSTEM=============================


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:50]}"


# ========================= USER REGISTRATION SIGNALS =========================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when User is saved"""
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)



# =========================

@receiver(post_save, sender=NurseAssignment)
def nurse_assignment_created(sender, instance, created, **kwargs):
    if created:
        # Send notification to nurse via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{instance.nurse.id}',
            {
                'type': 'notification_message',
                'message': f'You have been assigned to patient {instance.patient.full_name} (ID: {instance.patient.hospital_number})',
                'link': f'/nursing/assessment/{instance.patient.id}/',
                'created_at': str(instance.assigned_at)
            }
        )
        
        # Send update to HIM that assignment was successful
        async_to_sync(channel_layer.group_send)(
            f'user_{instance.assigned_by.id}',
            {
                'type': 'assignment_update',
                'patient_id': instance.patient.id,
                'patient_name': instance.patient.full_name,
                'action': 'assigned_nurse',
                'role': 'Nurse'
            }
        )

@receiver(post_save, sender=PhysicianAssignment)
def physician_assignment_created(sender, instance, created, **kwargs):
    if created:
        # Send notification to physician via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{instance.physician.id}',
            {
                'type': 'notification_message',
                'message': f'You have been assigned to patient {instance.patient.full_name} (ID: {instance.patient.hospital_number}) for consultation',
                'link': f'/doctor/consultation/{instance.patient.id}/',
                'created_at': str(instance.assigned_at)
            }
        )

@receiver(post_save, sender=NursingAssessment)
def nursing_assessment_completed(sender, instance, **kwargs):
    if instance.completed:
        # Send notification to physician
        physician_assignment = PhysicianAssignment.objects.filter(
            patient=instance.patient,
            is_active=True
        ).first()
        
        if physician_assignment:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{physician_assignment.physician.id}',
                {
                    'type': 'notification_message',
                    'message': f'Nursing assessment completed for {instance.patient.full_name}. Ready for consultation.',
                    'link': f'/doctor/consultation/{instance.patient.id}/',
                    'created_at': str(instance.completed_at)
                }
            )

@receiver(post_save, sender=MedicalConsultation)
def medical_consultation_completed(sender, instance, **kwargs):
    if instance.completed:
        channel_layer = get_channel_layer()
        
        # Send notifications based on referrals
        if instance.refer_to_pharmacy:
            # Notify pharmacy staff
            pharmacy_users = User.objects.filter(userprofile__role='PHARMACY')
            for user in pharmacy_users:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'notification_message',
                        'message': f'Pharmacy order needed for patient {instance.patient.full_name}',
                        'link': f'/pharmacy/order/{instance.patient.id}/',
                        'created_at': str(instance.completed_at)
                    }
                )
        
        if instance.refer_to_laboratory:
            # Notify laboratory staff
            lab_users = User.objects.filter(userprofile__role='MLS')
            for user in lab_users:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'notification_message',
                        'message': f'Laboratory tests needed for patient {instance.patient.full_name}',
                        'link': f'/lab/test/{instance.patient.id}/',
                        'created_at': str(instance.completed_at)
                    }
                )
        
        if instance.refer_to_optician:
            # Notify optician
            optician_users = User.objects.filter(userprofile__role='OPTOMETRIST')
            for user in optician_users:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'notification_message',
                        'message': f'Optical assessment needed for patient {instance.patient.full_name}',
                        'link': f'/optician/assessment/{instance.patient.id}/',
                        'created_at': str(instance.completed_at)
                    }
                )

# =========================== END OF MODELS.PY ==========================#
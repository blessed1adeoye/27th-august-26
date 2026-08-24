# b/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from datetime import date, timedelta
from django.utils import timezone 
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer 
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
        ('PHARMACY', 'Pharmacy'),
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
        related_name='dispensed_pharmacy_orders'  # <-- CHANGED: unique related_name
    )
    
    def __str__(self):
        return f"Pharmacy Order - {self.patient.full_name} - {self.drug_name}"


# ============= PHARMACY DRUG INVENTORY =============
class Drug(models.Model):
    CATEGORY_CHOICES = [
        ('ANTIBIOTICS', 'Antibiotics'),
        ('ANALGESICS', 'Analgesics'),
        ('ANTIHYPERTENSIVE', 'Antihypertensive'),
        ('ANTIDIABETIC', 'Antidiabetic'),
        ('ANTIMALARIAL', 'Antimalarial'),
        ('ANTIVIRAL', 'Antiviral'),
        ('ANTIFUNGAL', 'Antifungal'),
        ('CARDIOVASCULAR', 'Cardiovascular'),
        ('RESPIRATORY', 'Respiratory'),
        ('GASTROINTESTINAL', 'Gastrointestinal'),
        ('NEUROLOGICAL', 'Neurological'),
        ('VITAMINS', 'Vitamins & Supplements'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='OTHER')
    dosage_form = models.CharField(max_length=100, blank=True, help_text="e.g., Tablet, Capsule, Syrup")
    strength = models.CharField(max_length=50, blank=True, help_text="e.g., 500mg, 10mg/ml")
    quantity = models.IntegerField(default=0, help_text="Available stock quantity")
    reorder_level = models.IntegerField(default=10, help_text="Alert when stock reaches this level")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    manufacturer = models.CharField(max_length=200, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.quantity} units)"
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]


# ============= PHARMACY DISPENSING =============
class PharmacyDispensing(AuditMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='dispensed_medications')
    prescription = models.ForeignKey(PharmacyOrder, on_delete=models.CASCADE, related_name='dispensing_records')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='dispensing_records')
    quantity_dispensed = models.IntegerField()
    dispensing_date = models.DateTimeField(default=timezone.now)
    dispensed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='dispensed_drugs'  # <-- CHANGED: unique related_name
    )
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.drug.name} - {self.quantity_dispensed} units for {self.patient.full_name}"




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
    
# class LaboratoryTest(AuditMixin):
#     patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_tests')
#     consultation = models.ForeignKey(
#         MedicalConsultation, on_delete=models.SET_NULL, 
#         null=True, blank=True, related_name='lab_tests'
#     )
    
#     # Tests
#     malaria_parasite = models.CharField(
#         max_length=20, 
#         choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('PENDING', 'Pending')],
#         default='PENDING'
#     )
#     random_blood_sugar = models.DecimalField(
#         max_digits=5, decimal_places=1, null=True, blank=True,
#         help_text="Random Blood Sugar (mmol/L)"
#     )
#     hbsag = models.CharField(
#         max_length=20,
#         choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('PENDING', 'Pending')],
#         default='PENDING'
#     )
#     hcv = models.CharField(
#         max_length=20,
#         choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('PENDING', 'Pending')],
#         default='PENDING'
#     )
#     hiv = models.CharField(
#         max_length=20,
#         choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('PENDING', 'Pending')],
#         default='PENDING'
#     )
    
#     # Additional tests
#     other_tests = models.TextField(blank=True)
#     notes = models.TextField(blank=True)
    
#     # Status
#     completed = models.BooleanField(default=False)
#     completed_at = models.DateTimeField(null=True, blank=True)
#     completed_by = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, 
#         related_name='completed_lab_tests'
#     )
    
#     def __str__(self):
#         return f"Lab Test - {self.patient.full_name}"

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
        import random
        import string
        role = 'USER'  # Default role
        employee_id = f"{role[:3].upper()}{''.join(random.choices(string.digits, k=6))}"
        
        # Make sure employee_id is unique
        while UserProfile.objects.filter(employee_id=employee_id).exists():
            employee_id = f"{role[:3].upper()}{''.join(random.choices(string.digits, k=6))}"
        
        UserProfile.objects.create(
            user=instance,
            role='USER',
            employee_id=employee_id,
            phone='08000000000',
            is_active=True
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when User is saved"""
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        import random
        import string
        role = 'USER'
        employee_id = f"{role[:3].upper()}{''.join(random.choices(string.digits, k=6))}"
        while UserProfile.objects.filter(employee_id=employee_id).exists():
            employee_id = f"{role[:3].upper()}{''.join(random.choices(string.digits, k=6))}"
        
        UserProfile.objects.create(
            user=instance,
            role='USER',
            employee_id=employee_id,
            phone='08000000000',
            is_active=True
        )

# ========================= NOTIFICATION SIGNALS =========================
# These signals create BOTH database notifications (for polling) AND WebSocket notifications (for real-time)

@receiver(post_save, sender=NurseAssignment)
def nurse_assignment_created(sender, instance, created, **kwargs):
    if created:
        # 1. CREATE DATABASE NOTIFICATION (for polling system)
        Notification.objects.create(
            recipient=instance.nurse,
            message=f'You have been assigned to patient {instance.patient.full_name} (ID: {instance.patient.hospital_number})',
            link=f'/nursing/assessment/{instance.patient.id}/',
            is_read=False
        )
        print(f"✅ DB NOTIFICATION: Nurse {instance.nurse.username} assigned to {instance.patient.full_name}")
        
        # 2. Send WebSocket notification (for real-time)
        try:
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
        except Exception as e:
            print(f"WebSocket error: {e}")

@receiver(post_save, sender=PhysicianAssignment)
def physician_assignment_created(sender, instance, created, **kwargs):
    if created:
        # 1. CREATE DATABASE NOTIFICATION (for polling system)
        Notification.objects.create(
            recipient=instance.physician,
            message=f'You have been assigned to patient {instance.patient.full_name} (ID: {instance.patient.hospital_number}) for consultation',
            link=f'/doctor/consultation/{instance.patient.id}/',
            is_read=False
        )
        print(f"✅ DB NOTIFICATION: Physician {instance.physician.username} assigned to {instance.patient.full_name}")
        
        # 2. Send WebSocket notification (for real-time)
        try:
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
        except Exception as e:
            print(f"WebSocket error: {e}")

@receiver(post_save, sender=NursingAssessment)
def nursing_assessment_completed(sender, instance, **kwargs):
    if instance.completed:
        # Send notification to physician
        physician_assignment = PhysicianAssignment.objects.filter(
            patient=instance.patient,
            is_active=True
        ).first()
        
        if physician_assignment:
            # 1. CREATE DATABASE NOTIFICATION (for polling system)
            Notification.objects.create(
                recipient=physician_assignment.physician,
                message=f'Nursing assessment completed for {instance.patient.full_name}. Ready for consultation.',
                link=f'/doctor/consultation/{instance.patient.id}/',
                is_read=False
            )
            print(f"✅ DB NOTIFICATION: Physician {physician_assignment.physician.username} - Nursing completed for {instance.patient.full_name}")
            
            # 2. Send WebSocket notification (for real-time)
            try:
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
            except Exception as e:
                print(f"WebSocket error: {e}")

@receiver(post_save, sender=MedicalConsultation)
def medical_consultation_completed(sender, instance, **kwargs):
    if instance.completed:
        channel_layer = get_channel_layer()
        
        # Send notifications based on referrals
        if instance.refer_to_pharmacy:
            pharmacy_users = User.objects.filter(userprofile__role='PHARMACY')
            for user in pharmacy_users:
                # 1. CREATE DATABASE NOTIFICATION (for polling system)
                Notification.objects.create(
                    recipient=user,
                    message=f'Pharmacy order needed for patient {instance.patient.full_name}',
                    link=f'/pharmacy/order/{instance.patient.id}/',
                    is_read=False
                )
                print(f"✅ DB NOTIFICATION: Pharmacy {user.username} - Order needed for {instance.patient.full_name}")
                
                # 2. Send WebSocket notification (for real-time)
                try:
                    async_to_sync(channel_layer.group_send)(
                        f'user_{user.id}',
                        {
                            'type': 'notification_message',
                            'message': f'Pharmacy order needed for patient {instance.patient.full_name}',
                            'link': f'/pharmacy/order/{instance.patient.id}/',
                            'created_at': str(instance.completed_at)
                        }
                    )
                except Exception as e:
                    print(f"WebSocket error: {e}")
        
        if instance.refer_to_laboratory:
            lab_users = User.objects.filter(userprofile__role='MLS')
            for user in lab_users:
                # 1. CREATE DATABASE NOTIFICATION (for polling system)
                Notification.objects.create(
                    recipient=user,
                    message=f'Laboratory tests needed for patient {instance.patient.full_name}',
                    link=f'/lab/test/{instance.patient.id}/',
                    is_read=False
                )
                print(f"✅ DB NOTIFICATION: Lab {user.username} - Tests needed for {instance.patient.full_name}")
                
                # 2. Send WebSocket notification (for real-time)
                try:
                    async_to_sync(channel_layer.group_send)(
                        f'user_{user.id}',
                        {
                            'type': 'notification_message',
                            'message': f'Laboratory tests needed for patient {instance.patient.full_name}',
                            'link': f'/lab/test/{instance.patient.id}/',
                            'created_at': str(instance.completed_at)
                        }
                    )
                except Exception as e:
                    print(f"WebSocket error: {e}")
        
        if instance.refer_to_optician:
            optician_users = User.objects.filter(userprofile__role='OPTOMETRIST')
            for user in optician_users:
                # 1. CREATE DATABASE NOTIFICATION (for polling system)
                Notification.objects.create(
                    recipient=user,
                    message=f'Optical assessment needed for patient {instance.patient.full_name}',
                    link=f'/optician/assessment/{instance.patient.id}/',
                    is_read=False
                )
                print(f"✅ DB NOTIFICATION: Optician {user.username} - Assessment needed for {instance.patient.full_name}")
                
                # 2. Send WebSocket notification (for real-time)
                try:
                    async_to_sync(channel_layer.group_send)(
                        f'user_{user.id}',
                        {
                            'type': 'notification_message',
                            'message': f'Optical assessment needed for patient {instance.patient.full_name}',
                            'link': f'/optician/assessment/{instance.patient.id}/',
                            'created_at': str(instance.completed_at)
                        }
                    )
                except Exception as e:
                    print(f"WebSocket error: {e}")

@receiver(post_save, sender=MedicalConsultation)
def medical_consultation_completed(sender, instance, **kwargs):
    if instance.completed:
        channel_layer = get_channel_layer()
        
        # ============= PHARMACY NOTIFICATIONS =============
        if instance.refer_to_pharmacy:
            # Get all pharmacy orders from this consultation that are not yet dispensed
            pharmacy_orders = PharmacyOrder.objects.filter(
                consultation=instance,
                dispensed=False
            )
            
            if pharmacy_orders.exists():
                # Create a summary of drugs
                drug_list = []
                for order in pharmacy_orders:
                    drug_list.append(f"{order.drug_name} (x{order.quantity})")
                drug_summary = ", ".join(drug_list)
                drug_count = pharmacy_orders.count()
                
                # Notify pharmacy staff
                pharmacy_users = User.objects.filter(userprofile__role='PHARMACY')
                for user in pharmacy_users:
                    # Create database notification
                    Notification.objects.create(
                        recipient=user,
                        message=f'💊 {drug_count} medication(s) for {instance.patient.full_name}: {drug_summary}',
                        link=f'/pharmacy/dispense-patient/{instance.patient.id}/',
                        is_read=False
                    )
                    print(f"✅ DB NOTIFICATION: Pharmacy {user.username} - {drug_count} drugs for {instance.patient.full_name}")
                    
                    # Send WebSocket notification (for real-time)
                    try:
                        async_to_sync(channel_layer.group_send)(
                            f'user_{user.id}',
                            {
                                'type': 'notification_message',
                                'message': f'💊 {drug_count} medication(s) for {instance.patient.full_name}: {drug_summary}',
                                'link': f'/pharmacy/dispense-patient/{instance.patient.id}/',
                                'created_at': str(instance.completed_at)
                            }
                        )
                    except Exception as e:
                        print(f"WebSocket error (Pharmacy): {e}")
        
        # ============= LABORATORY NOTIFICATIONS =============
        if instance.refer_to_laboratory:
            # Get the lab test created from this consultation
            lab_test = LaboratoryTest.objects.filter(
                consultation=instance,
                completed=False
            ).first()
            
            if lab_test:
                # Get list of tests requested
                tests_requested = []
                if lab_test.malaria_parasite == 'PENDING':
                    tests_requested.append('Malaria Parasite')
                if lab_test.hbsag == 'PENDING':
                    tests_requested.append('HBsAg')
                if lab_test.hcv == 'PENDING':
                    tests_requested.append('HCV')
                if lab_test.hiv == 'PENDING':
                    tests_requested.append('HIV')
                if lab_test.random_blood_sugar is None:
                    tests_requested.append('Random Blood Sugar')
                if lab_test.other_tests:
                    tests_requested.append(lab_test.other_tests)
                
                test_summary = ", ".join(tests_requested) if tests_requested else "Laboratory tests"
                test_count = len(tests_requested)
                
                # Notify laboratory staff
                lab_users = User.objects.filter(userprofile__role='MLS')
                for user in lab_users:
                    Notification.objects.create(
                        recipient=user,
                        message=f'🧪 {test_count} test(s) needed for {instance.patient.full_name}: {test_summary}',
                        link=f'/lab/test/{lab_test.id}/',
                        is_read=False
                    )
                    print(f"✅ DB NOTIFICATION: Lab {user.username} - Tests for {instance.patient.full_name}")
                    
                    try:
                        async_to_sync(channel_layer.group_send)(
                            f'user_{user.id}',
                            {
                                'type': 'notification_message',
                                'message': f'🧪 {test_count} test(s) needed for {instance.patient.full_name}: {test_summary}',
                                'link': f'/lab/test/{lab_test.id}/',
                                'created_at': str(instance.completed_at)
                            }
                        )
                    except Exception as e:
                        print(f"WebSocket error (Lab): {e}")
        
        # ============= OPTICIAN NOTIFICATIONS =============
        if instance.refer_to_optician:
            # Get the optical assessment created from this consultation
            optical_assessment = OpticalAssessment.objects.filter(
                consultation=instance,
                completed=False
            ).first()
            
            if optical_assessment:
                # Notify optician staff
                optician_users = User.objects.filter(userprofile__role='OPTOMETRIST')
                for user in optician_users:
                    Notification.objects.create(
                        recipient=user,
                        message=f'👁️ Optical assessment needed for {instance.patient.full_name}',
                        link=f'/optician/assessment/{instance.patient.id}/',
                        is_read=False
                    )
                    print(f"✅ DB NOTIFICATION: Optician {user.username} - Assessment for {instance.patient.full_name}")
                    
                    try:
                        async_to_sync(channel_layer.group_send)(
                            f'user_{user.id}',
                            {
                                'type': 'notification_message',
                                'message': f'👁️ Optical assessment needed for {instance.patient.full_name}',
                                'link': f'/optician/assessment/{instance.patient.id}/',
                                'created_at': str(instance.completed_at)
                            }
                        )
                    except Exception as e:
                        print(f"WebSocket error (Optician): {e}")
        
        # ============= SPECIALIST NOTIFICATIONS =============
        if instance.refer_to_specialist:
            # Notify specialist (you might want to customize this based on your needs)
            specialist_users = User.objects.filter(userprofile__role='PHYSICIAN')
            for user in specialist_users:
                Notification.objects.create(
                    recipient=user,
                    message=f'🩺 Specialist referral needed for {instance.patient.full_name}',
                    link=f'/doctor/consultation/{instance.patient.id}/',
                    is_read=False
                )
                print(f"✅ DB NOTIFICATION: Specialist {user.username} - Referral for {instance.patient.full_name}")
                
                try:
                    async_to_sync(channel_layer.group_send)(
                        f'user_{user.id}',
                        {
                            'type': 'notification_message',
                            'message': f'🩺 Specialist referral needed for {instance.patient.full_name}',
                            'link': f'/doctor/consultation/{instance.patient.id}/',
                            'created_at': str(instance.completed_at)
                        }
                    )
                except Exception as e:
                    print(f"WebSocket error (Specialist): {e}")



    

# =========================== END OF MODELS.PY ==========================#

"""
    # Add this model to b/models.py if you want dynamic lab tests
class LabTestType(models.Model):
    CATEGORY_CHOICES = [
        ('HEMATOLOGY', 'Hematology'),
        ('BIOCHEMISTRY', 'Biochemistry'),
        ('MICROBIOLOGY', 'Microbiology'),
        ('IMMUNOLOGY', 'Immunology'),
        ('PARASITOLOGY', 'Parasitology'),
        ('SEROLOGY', 'Serology'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='OTHER')
    normal_range = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']



    views.py
    # Get available lab tests from the database
lab_tests = LabTestType.objects.filter(is_active=True).order_by('name')
"""


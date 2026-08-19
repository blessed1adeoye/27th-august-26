# b/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import (
    Patient, NursingAssessment, MedicalConsultation, 
    PharmacyOrder, LaboratoryTest, OpticalAssessment,
    UserProfile
)
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'hospital_number', 'first_name', 'last_name', 'middle_name',
            'date_of_birth', 'gender', 'phone', 'email', 'address'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

# ============= NURSING FORM =============
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

# ============= DOCTOR FORM =============
class MedicalConsultationForm(forms.ModelForm):
    class Meta:
        model = MedicalConsultation
        fields = [
            'symptoms', 'diagnosis', 'treatment_plan', 'referral_notes',
            'refer_to_pharmacy', 'refer_to_laboratory', 'refer_to_optician',
            'refer_to_specialist'
        ]
        widgets = {
            'symptoms': forms.Textarea(attrs={'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'referral_notes': forms.Textarea(attrs={'rows': 2}),
        }

# ============= PHARMACY FORM =============
class PharmacyOrderForm(forms.ModelForm):
    class Meta:
        model = PharmacyOrder
        fields = ['drug_name', 'quantity', 'dosage', 'frequency', 'duration', 'instructions']
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 2}),
        }

# ============= LABORATORY FORM =============
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

# ============= OPTICIAN FORM =============
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

# ================= User Management ============================

class UserRegistrationForm(forms.ModelForm):
    """Form for creating new users with role assignment"""
    
    DEFAULT_PASSWORD = '123'  # Default password for new users
    
    role = forms.ChoiceField(
        choices=UserProfile.USER_ROLES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    employee_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., EMP001'})
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 08012345678'})
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Nursing Department'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'employee_id', 'phone', 'department']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        }
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username
    
    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        if UserProfile.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError('This employee ID is already in use.')
        return employee_id
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Set default password
        user.set_password(self.DEFAULT_PASSWORD)
        
        if commit:
            user.save()
            # Create or update user profile
            user_profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': self.cleaned_data['role'],
                    'employee_id': self.cleaned_data['employee_id'],
                    'phone': self.cleaned_data['phone'],
                    'department': self.cleaned_data.get('department', ''),
                }
            )
            if not created:
                user_profile.role = self.cleaned_data['role']
                user_profile.employee_id = self.cleaned_data['employee_id']
                user_profile.phone = self.cleaned_data['phone']
                user_profile.department = self.cleaned_data.get('department', '')
                user_profile.save()
        
        return user
# b/forms.py

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import *
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter patient address'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default value for address field
        self.fields['email'].initial = 'bgie@corepoutreach.com'
        self.fields['address'].initial = 'COREP'
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if isinstance(field, forms.Select):
                field.widget.attrs['class'] = 'form-select'
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > timezone.now().date():
            raise ValidationError('Date of birth cannot be in the future')
        return dob
    
    def clean_hospital_number(self):
        number = self.cleaned_data.get('hospital_number')
        if Patient.objects.filter(hospital_number=number).exists():
            if not self.instance.pk or self.instance.hospital_number != number:
                raise ValidationError('This hospital number is already in use')
        return number

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

# ============= OPTICIAN FORM =============
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



# =============================== DRUG Form ==========================

class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = [
            'name', 'category', 'quantity', 'reorder_level', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Ibuprofen 200mg, Paracetamol 500mg'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'form-control'
            if isinstance(self.fields[field], forms.Select):
                self.fields[field].widget.attrs['class'] = 'form-select'
            if isinstance(self.fields[field], forms.CheckboxInput):
                self.fields[field].widget.attrs['class'] = 'form-check-input'
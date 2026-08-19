from django.contrib import admin
from .models import (
    UserProfile, Patient, NursingAssessment, MedicalConsultation,
    PharmacyOrder, LaboratoryTest, OpticalAssessment, PatientWorkflow,
    NurseAssignment, PhysicianAssignment, Notification
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'employee_id', 'phone', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'employee_id']
    readonly_fields = ['user']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Profile Information', {
            'fields': ('role', 'employee_id', 'phone', 'department', 'is_active')
        }),
    )

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['hospital_number', 'full_name', 'gender', 'phone', 'current_stage', 'created_at']
    list_filter = ['gender', 'current_stage', 'is_admitted']
    search_fields = ['hospital_number', 'first_name', 'last_name', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('hospital_number', 'first_name', 'last_name', 'middle_name', 
                      'date_of_birth', 'gender', 'phone', 'email', 'address')
        }),
        ('Status', {
            'fields': ('current_stage', 'is_admitted')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(NursingAssessment)
class NursingAssessmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'blood_pressure_systolic', 'blood_pressure_diastolic', 
                    'pulse_rate', 'temperature', 'completed']
    list_filter = ['completed', 'isolation_required']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__hospital_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient',)
        }),
        ('Vital Signs', {
            'fields': ('blood_pressure_systolic', 'blood_pressure_diastolic', 
                      'pulse_rate', 'temperature', 'respiratory_rate', 'oxygen_saturation')
        }),
        ('Biohazard Assessment', {
            'fields': ('biohazard_risk', 'isolation_required', 'notes')
        }),
        ('Status', {
            'fields': ('completed', 'completed_at')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
@admin.register(PhysicianAssignment)
class PhysicianAssignmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'physician', 'assigned_by', 'assigned_at', 'is_active']
    list_filter = ['is_active']
    search_fields = ['patient__first_name', 'patient__last_name', 
                     'physician__username', 'physician__first_name', 'physician__last_name']
    readonly_fields = ['assigned_at']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('patient', 'physician', 'assigned_by', 'assigned_at', 'is_active')
        }),
    )

@admin.register(MedicalConsultation)
class MedicalConsultationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'diagnosis_summary', 'refer_to_pharmacy', 
                    'refer_to_laboratory', 'refer_to_optician', 'completed']
    list_filter = ['refer_to_pharmacy', 'refer_to_laboratory', 'refer_to_optician', 
                   'refer_to_specialist', 'completed']
    search_fields = ['patient__first_name', 'patient__last_name', 'diagnosis', 'symptoms']
    readonly_fields = ['created_at', 'updated_at']
    
    def diagnosis_summary(self, obj):
        return obj.diagnosis[:50] + '...' if len(obj.diagnosis) > 50 else obj.diagnosis
    diagnosis_summary.short_description = 'Diagnosis'
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient', 'nursing_assessment')
        }),
        ('Consultation', {
            'fields': ('symptoms', 'diagnosis', 'treatment_plan')
        }),
        ('Referrals', {
            'fields': ('refer_to_pharmacy', 'refer_to_laboratory', 
                      'refer_to_optician', 'refer_to_specialist', 'referral_notes')
        }),
        ('Status', {
            'fields': ('completed', 'completed_at')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PharmacyOrder)
class PharmacyOrderAdmin(admin.ModelAdmin):
    list_display = ['patient', 'drug_name', 'quantity', 'dosage', 'dispensed', 'dispensed_at']
    list_filter = ['dispensed']
    search_fields = ['patient__first_name', 'patient__last_name', 'drug_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient', 'consultation')
        }),
        ('Medication', {
            'fields': ('drug_name', 'quantity', 'dosage', 'frequency', 'duration', 'instructions')
        }),
        ('Status', {
            'fields': ('dispensed', 'dispensed_at', 'dispensed_by')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(LaboratoryTest)
class LaboratoryTestAdmin(admin.ModelAdmin):
    list_display = ['patient', 'malaria_parasite', 'random_blood_sugar', 
                    'hbsag', 'hcv', 'hiv', 'completed']
    list_filter = ['malaria_parasite', 'hbsag', 'hcv', 'hiv', 'completed']
    search_fields = ['patient__first_name', 'patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient', 'consultation')
        }),
        ('Parasitology', {
            'fields': ('malaria_parasite', 'random_blood_sugar')
        }),
        ('Serology', {
            'fields': ('hbsag', 'hcv', 'hiv')
        }),
        ('Additional', {
            'fields': ('other_tests', 'notes')
        }),
        ('Status', {
            'fields': ('completed', 'completed_at', 'completed_by')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(OpticalAssessment)
class OpticalAssessmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'is_walk_in', 'glasses_allocated', 'glasses_type', 'completed']
    list_filter = ['is_walk_in', 'completed']
    search_fields = ['patient__first_name', 'patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient', 'consultation', 'is_walk_in')
        }),
        ('Assessment', {
            'fields': ('visual_acuity_left', 'visual_acuity_right', 
                      'refractive_error', 'eye_health_notes')
        }),
        ('Glasses', {
            'fields': ('glasses_allocated', 'glasses_type', 'glasses_prescription')
        }),
        ('Status', {
            'fields': ('completed', 'completed_at', 'completed_by')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PatientWorkflow)
class PatientWorkflowAdmin(admin.ModelAdmin):
    list_display = ['patient', 'current_stage', 'nursing_completed', 'doctor_completed', 
                    'pharmacy_completed', 'laboratory_completed', 'optician_completed']
    list_filter = ['current_stage', 'nursing_completed', 'doctor_completed', 
                   'pharmacy_completed', 'laboratory_completed', 'optician_completed']
    search_fields = ['patient__first_name', 'patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient', 'current_stage')
        }),
        ('Stage Completion', {
            'fields': ('nursing_completed', 'nursing_completed_at',
                      'doctor_completed', 'doctor_completed_at',
                      'pharmacy_completed', 'pharmacy_completed_at',
                      'laboratory_completed', 'laboratory_completed_at',
                      'optician_completed', 'optician_completed_at',
                      'completed_at')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(NurseAssignment)
class NurseAssignmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'nurse', 'assigned_by', 'assigned_at', 'is_active']
    list_filter = ['is_active']
    search_fields = ['patient__first_name', 'patient__last_name', 
                     'nurse__username', 'nurse__first_name', 'nurse__last_name']
    readonly_fields = ['assigned_at']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('patient', 'nurse', 'assigned_by', 'assigned_at', 'is_active')
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'message_summary', 'is_read', 'created_at']
    list_filter = ['is_read']
    search_fields = ['recipient__username', 'recipient__first_name', 'recipient__last_name', 'message']
    readonly_fields = ['created_at']
    
    def message_summary(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_summary.short_description = 'Message'
    
    fieldsets = (
        ('Notification', {
            'fields': ('recipient', 'message', 'link', 'is_read', 'created_at')
        }),
    )

# Custom admin site configuration
admin.site.site_header = 'HIM - Health Information Management'
admin.site.site_title = 'HIM Admin'
admin.site.index_title = 'Medical Outreach Administration'
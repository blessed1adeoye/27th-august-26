# b/management/commands/export_to_excel.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import pandas as pd
from b.models import *
import os

class Command(BaseCommand):
    help = 'Export all data to Excel for analysis'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 EXPORTING DATA TO EXCEL'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Create output directory
        output_dir = 'data_exports'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export each model
        self.export_patients(output_dir, timestamp)
        self.export_nursing_assessments(output_dir, timestamp)
        self.export_consultations(output_dir, timestamp)
        self.export_lab_tests(output_dir, timestamp)
        self.export_optical_assessments(output_dir, timestamp)
        self.export_pharmacy_orders(output_dir, timestamp)
        self.export_dispensing(output_dir, timestamp)
        self.export_drugs(output_dir, timestamp)
        self.export_notifications(output_dir, timestamp)
        
        self.stdout.write(self.style.SUCCESS('\n✅ All data exported successfully!'))
        self.stdout.write(f'📁 Files saved in: {output_dir}/')

    def export_patients(self, output_dir, timestamp):
        """Export patients"""
        self.stdout.write('📤 Exporting patients...')
        patients = Patient.objects.all().values(
            'id', 'hospital_number', 'first_name', 'last_name', 'middle_name',
            'date_of_birth', 'gender', 'phone', 'email', 'address',
            'is_admitted', 'current_stage', 'created_at'
        )
        
        df = pd.DataFrame(list(patients))
        # Calculate age
        df['age'] = df['date_of_birth'].apply(lambda x: (timezone.now().date() - x).days // 365 if x else None)
        filename = f'{output_dir}/patients_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Patients: {len(df)} records')

    def export_nursing_assessments(self, output_dir, timestamp):
        """Export nursing assessments"""
        self.stdout.write('📤 Exporting nursing assessments...')
        assessments = NursingAssessment.objects.select_related('patient').values(
            'id', 'patient__hospital_number', 'patient__first_name', 'patient__last_name',
            'blood_pressure_systolic', 'blood_pressure_diastolic', 'pulse_rate',
            'temperature', 'respiratory_rate', 'oxygen_saturation',
            'biohazard_risk', 'isolation_required', 'completed', 'completed_at',
            'created_at'
        )
        
        df = pd.DataFrame(list(assessments))
        filename = f'{output_dir}/nursing_assessments_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Nursing Assessments: {len(df)} records')

    def export_consultations(self, output_dir, timestamp):
        """Export consultations"""
        self.stdout.write('📤 Exporting consultations...')
        consultations = MedicalConsultation.objects.select_related('patient').values(
            'id', 'patient__hospital_number', 'patient__first_name', 'patient__last_name',
            'symptoms', 'diagnosis', 'treatment_plan', 'referral_notes',
            'refer_to_pharmacy', 'refer_to_laboratory', 'refer_to_optician',
            'refer_to_specialist', 'completed', 'completed_at', 'created_at'
        )
        
        df = pd.DataFrame(list(consultations))
        filename = f'{output_dir}/consultations_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Consultations: {len(df)} records')

    def export_lab_tests(self, output_dir, timestamp):
        """Export lab tests"""
        self.stdout.write('📤 Exporting lab tests...')
        lab_tests = LaboratoryTest.objects.select_related('patient').values(
            'id', 'patient__hospital_number', 'patient__first_name', 'patient__last_name',
            'malaria_parasite', 'random_blood_sugar', 'hbsag',
            'other_tests', 'notes', 'completed', 'completed_at', 'created_at'
        )
        
        df = pd.DataFrame(list(lab_tests))
        filename = f'{output_dir}/lab_tests_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Lab Tests: {len(df)} records')

    def export_optical_assessments(self, output_dir, timestamp):
        """Export optical assessments"""
        self.stdout.write('📤 Exporting optical assessments...')
        optical = OpticalAssessment.objects.select_related('patient').values(
            'id', 'patient__hospital_number', 'patient__first_name', 'patient__last_name',
            'is_walk_in', 'visual_acuity_left', 'visual_acuity_right',
            'refractive_error', 'eye_health_notes', 'glasses_allocated',
            'glasses_type', 'glasses_prescription', 'completed', 'completed_at',
            'viewed_by_optician', 'viewed_by_physician', 'created_at'
        )
        
        df = pd.DataFrame(list(optical))
        filename = f'{output_dir}/optical_assessments_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Optical Assessments: {len(df)} records')

    def export_pharmacy_orders(self, output_dir, timestamp):
        """Export pharmacy orders"""
        self.stdout.write('📤 Exporting pharmacy orders...')
        orders = PharmacyOrder.objects.select_related('patient').values(
            'id', 'patient__hospital_number', 'patient__first_name', 'patient__last_name',
            'drug_name', 'quantity', 'dosage', 'frequency', 'duration',
            'instructions', 'dispensed', 'dispensed_at', 'created_at'
        )
        
        df = pd.DataFrame(list(orders))
        filename = f'{output_dir}/pharmacy_orders_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Pharmacy Orders: {len(df)} records')

    def export_dispensing(self, output_dir, timestamp):
        """Export dispensing records"""
        self.stdout.write('📤 Exporting dispensing records...')
        dispensing = PharmacyDispensing.objects.select_related('patient', 'drug').values(
            'id', 'patient__hospital_number', 'patient__first_name', 'patient__last_name',
            'drug__name', 'quantity_dispensed', 'dispensing_date', 'notes',
            'created_at'
        )
        
        df = pd.DataFrame(list(dispensing))
        filename = f'{output_dir}/dispensing_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Dispensing: {len(df)} records')

    def export_drugs(self, output_dir, timestamp):
        """Export drugs"""
        self.stdout.write('📤 Exporting drugs...')
        drugs = Drug.objects.all().values(
            'id', 'name', 'category', 'quantity', 'reorder_level',
            'is_active', 'created_at', 'updated_at'
        )
        
        df = pd.DataFrame(list(drugs))
        filename = f'{output_dir}/drugs_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Drugs: {len(df)} records')

    def export_notifications(self, output_dir, timestamp):
        """Export notifications"""
        self.stdout.write('📤 Exporting notifications...')
        notifications = Notification.objects.select_related('recipient').values(
            'id', 'recipient__username', 'message', 'is_read', 'created_at', 'link'
        )
        
        df = pd.DataFrame(list(notifications))
        filename = f'{output_dir}/notifications_{timestamp}.xlsx'
        df.to_excel(filename, index=False)
        self.stdout.write(f'  ✅ Notifications: {len(df)} records')
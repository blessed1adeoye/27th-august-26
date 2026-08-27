# b/management/commands/populate_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import random
import string
from b.models import *

class Command(BaseCommand):
    help = 'Populate database with test data for analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--patients',
            type=int,
            default=50,
            help='Number of patients to create (default: 50)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days of historical data (default: 90)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating'
        )

    def handle(self, *args, **options):
        patient_count = options['patients']
        days_back = options['days']
        clear = options['clear']
        
        if clear:
            self.clear_data()
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 DATA POPULATION FOR ANALYSIS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Create users if they don't exist
        users = self.create_users()
        
        # Create patients
        patients = self.create_patients(patient_count)
        
        # Create patient workflow
        workflows = self.create_workflows(patients)
        
        # Create nursing assessments
        nursing = self.create_nursing_assessments(patients, users, days_back)
        
        # Create consultations
        consultations = self.create_consultations(patients, users, nursing, days_back)
        
        # Create lab tests
        lab_tests = self.create_lab_tests(patients, consultations, users, days_back)
        
        # Create optician assessments
        optical = self.create_optical_assessments(patients, consultations, users, days_back)
        
        # Create pharmacy orders
        pharmacy_orders = self.create_pharmacy_orders(patients, consultations, users, days_back)
        
        # Create drugs
        drugs = self.create_drugs()
        
        # Create pharmacy dispensing
        dispensing = self.create_pharmacy_dispensing(patients, pharmacy_orders, drugs, users, days_back)
        
        # Create notifications
        notifications = self.create_notifications(users, patients, days_back)
        
        # Create super admin if not exists
        self.create_super_admin()
        
        self.print_summary(patients, nursing, consultations, lab_tests, optical, pharmacy_orders, dispensing, notifications)

    def clear_data(self):
        """Clear existing data"""
        self.stdout.write('🧹 Clearing existing data...')
        Notification.objects.all().delete()
        PharmacyDispensing.objects.all().delete()
        PharmacyOrder.objects.all().delete()
        OpticalAssessment.objects.all().delete()
        LaboratoryTest.objects.all().delete()
        MedicalConsultation.objects.all().delete()
        NursingAssessment.objects.all().delete()
        PatientWorkflow.objects.all().delete()
        Patient.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✅ Data cleared!'))

    def create_users(self):
        """Create users for each role"""
        self.stdout.write('\n👥 Creating users...')
        
        users = {
            'HIM': [],
            'NURSE': [],
            'PHYSICIAN': [],
            'PHARMACY': [],
            'MLS': [],
            'OPTOMETRIST': []
        }
        
        for role in users.keys():
            for i in range(3):
                username = f"{role.lower()}_{i+1}"
                
                # Check if user exists
                user = User.objects.filter(username=username).first()
                
                if user:
                    # ===== FIX: Check if profile exists before creating =====
                    profile = UserProfile.objects.filter(user=user).first()
                    if not profile:
                        # Only create profile if it doesn't exist
                        try:
                            profile = UserProfile.objects.create(
                                user=user,
                                role=role,
                                employee_id=f"{role[:3].upper()}{random.randint(100, 999)}",
                                phone=f"080{''.join(random.choices(string.digits, k=8))}",
                                is_active=True
                            )
                            self.stdout.write(f'  ✅ Created profile for existing user: {username}')
                        except Exception as e:
                            self.stdout.write(f'  ❌ Error creating profile for {username}: {e}')
                    else:
                        self.stdout.write(f'  ⚠️ User already exists: {username}')
                else:
                    # Create new user
                    try:
                        user = User.objects.create_user(
                            username=username,
                            password='password123',
                            email=f"{username}@corep.com",
                            first_name=f"{role.title()}{i+1}",
                            last_name="User"
                        )
                        
                        # Create profile
                        UserProfile.objects.create(
                            user=user,
                            role=role,
                            employee_id=f"{role[:3].upper()}{random.randint(100, 999)}",
                            phone=f"080{''.join(random.choices(string.digits, k=8))}",
                            is_active=True
                        )
                        self.stdout.write(f'  ✅ Created {role}: {username}')
                    except Exception as e:
                        self.stdout.write(f'  ❌ Error creating {role}: {username} - {e}')
                
                users[role].append(user)
        
        return users

    def create_super_admin(self):
        """Create super admin user"""
        self.stdout.write('\n👑 Creating super admin...')
        
        admin = User.objects.filter(username='admin').first()
        
        if not admin:
            try:
                admin = User.objects.create_user(
                    username='admin',
                    password='admin123',
                    email='admin@corep.com',
                    first_name='Super',
                    last_name='Admin',
                    is_superuser=True,
                    is_staff=True
                )
                
                # Create profile for admin
                UserProfile.objects.create(
                    user=admin,
                    role='HIM',
                    employee_id='ADMIN001',
                    phone='08000000000',
                    is_active=True
                )
                self.stdout.write(self.style.SUCCESS(f'  ✅ Super admin created: admin / admin123'))
            except Exception as e:
                self.stdout.write(f'  ❌ Error creating admin: {e}')
        else:
            # Make sure admin is superuser
            if not admin.is_superuser:
                admin.is_superuser = True
                admin.is_staff = True
                admin.save()
            
            # ===== FIX: Check if profile exists before creating =====
            profile = UserProfile.objects.filter(user=admin).first()
            if not profile:
                try:
                    UserProfile.objects.create(
                        user=admin,
                        role='HIM',
                        employee_id='ADMIN001',
                        phone='08000000000',
                        is_active=True
                    )
                    self.stdout.write(f'  ✅ Created profile for admin')
                except Exception as e:
                    self.stdout.write(f'  ❌ Error creating admin profile: {e}')
            else:
                self.stdout.write(f'  ⚠️ Super admin already exists: admin')

    def create_patients(self, count):
        """Create test patients"""
        self.stdout.write(f'\n🏥 Creating {count} patients...')
        
        first_names = [
            'Ade', 'Bola', 'Chidi', 'Damilola', 'Emeka', 'Funke', 'Gbenga',
            'Hauwa', 'Ikenna', 'Joy', 'Kemi', 'Lola', 'Musa', 'Ngozi',
            'Olu', 'Peter', 'Queen', 'Ruth', 'Segun', 'Tunde', 'Uche',
            'Victor', 'Wale', 'Yemi', 'Zainab', 'Abiola', 'Bisi', 'Chinwe',
            'Dayo', 'Efe', 'Femi', 'Gift', 'Hope', 'Ifeanyi', 'Jide',
            'Kayode', 'Lekan', 'Moyo', 'Nkechi', 'Obi', 'Precious'
        ]
        
        last_names = [
            'Adebayo', 'Okonkwo', 'Eze', 'Nwosu', 'Igwe', 'Obi', 'Nnamdi',
            'Ogunleye', 'Bello', 'Adeyemi', 'Okafor', 'Okoro', 'Onyeka',
            'Chukwu', 'Oluwaseun', 'Akinwale', 'Balogun', 'Fashola',
            'Gbadegesin', 'Ibrahim', 'Jolayemi', 'Kolawole', 'Lawal',
            'Majekodunmi', 'Nwachukwu', 'Ogunbiyi', 'Oladapo', 'Oluwole'
        ]
        
        patients = []
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            gender = random.choice(['MALE', 'FEMALE'])
            
            year = random.randint(1953, 2015)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            dob = date(year, month, day)
            
            hospital_number = f"HIM{''.join(random.choices(string.digits, k=6))}"
            while Patient.objects.filter(hospital_number=hospital_number).exists():
                hospital_number = f"HIM{''.join(random.choices(string.digits, k=6))}"
            
            phone = f"080{''.join(random.choices(string.digits, k=8))}"
            
            patient = Patient.objects.create(
                hospital_number=hospital_number,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                gender=gender,
                phone=phone,
                email=f"{first_name.lower()}.{last_name.lower()}@gmail.com",
                address=f"{random.randint(1, 200)} {random.choice(['Main St', 'Lane', 'Road', 'Drive'])}, Ibadan",
                current_stage='COMPLETED'
            )
            patients.append(patient)
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'  ✅ Created {i + 1} patients...')
        
        return patients

    def create_workflows(self, patients):
        """Create workflows for patients"""
        self.stdout.write('\n📋 Creating workflows...')
        workflows = []
        for patient in patients:
            stages = ['REGISTERED', 'NURSING', 'DOCTOR', 'PHARMACY', 'LABORATORY', 'OPTICIAN', 'COMPLETED']
            current_stage = random.choice(stages)
            workflow = PatientWorkflow.objects.create(
                patient=patient,
                current_stage=current_stage,
                nursing_completed=random.choice([True, False]),
                doctor_completed=random.choice([True, False]),
                pharmacy_completed=random.choice([True, False]),
                laboratory_completed=random.choice([True, False]),
                optician_completed=random.choice([True, False])
            )
            workflows.append(workflow)
        return workflows

    def create_nursing_assessments(self, patients, users, days_back):
        """Create nursing assessments"""
        self.stdout.write('\n🩺 Creating nursing assessments...')
        nursing_assessments = []
        nurses = users['NURSE']
        
        for patient in patients:
            if random.random() > 0.3:
                nurse = random.choice(nurses) if nurses else None
                completed_at = timezone.now() - timedelta(days=random.randint(1, days_back))
                
                assessment = NursingAssessment.objects.create(
                    patient=patient,
                    blood_pressure_systolic=random.randint(100, 160),
                    blood_pressure_diastolic=random.randint(60, 100),
                    pulse_rate=random.randint(60, 100),
                    temperature=round(random.uniform(36.0, 38.5), 1),
                    respiratory_rate=random.randint(12, 20),
                    oxygen_saturation=random.randint(95, 100),
                    biohazard_risk=random.choice(['None', 'Low', 'Medium', 'High']),
                    isolation_required=random.choice([True, False]),
                    notes=f"Routine nursing assessment for {patient.full_name}",
                    completed=True,
                    completed_at=completed_at,
                    created_by=nurse,
                    updated_by=nurse
                )
                nursing_assessments.append(assessment)
        
        self.stdout.write(f'  ✅ Created {len(nursing_assessments)} nursing assessments')
        return nursing_assessments

    def create_consultations(self, patients, users, nursing_assessments, days_back):
        """Create medical consultations"""
        self.stdout.write('\n👨‍⚕️ Creating consultations...')
        consultations = []
        physicians = users['PHYSICIAN']
        
        symptoms = [
            'Fever, headache, body pain',
            'Chest pain, shortness of breath',
            'Abdominal pain, nausea, vomiting',
            'Joint pain, swelling, stiffness',
            'Cough, fever, difficulty breathing',
            'Dizziness, headache, blurred vision',
            'Skin rash, itching, redness',
            'Frequent urination, thirst, fatigue'
        ]
        diagnoses = [
            'Malaria',
            'Hypertension',
            'Diabetes Type 2',
            'Respiratory Infection',
            'Gastroenteritis',
            'Arthritis',
            'Allergic Reaction',
            'Urinary Tract Infection'
        ]
        treatment_plans = [
            'Prescribed medication, follow up in 2 weeks',
            'Lifestyle changes, medication, review in 1 month',
            'Antibiotics, rest, hydration',
            'Pain management, physiotherapy referral',
            'Inhalers, steroids, follow up in 1 week',
            'Dietary changes, exercise, medication'
        ]
        
        for i, patient in enumerate(patients):
            if random.random() > 0.4:
                physician = random.choice(physicians) if physicians else None
                nursing = nursing_assessments[i] if i < len(nursing_assessments) else None
                completed_at = timezone.now() - timedelta(days=random.randint(1, days_back))
                
                consultation = MedicalConsultation.objects.create(
                    patient=patient,
                    nursing_assessment=nursing,
                    symptoms=random.choice(symptoms),
                    diagnosis=random.choice(diagnoses),
                    treatment_plan=random.choice(treatment_plans),
                    refer_to_pharmacy=random.choice([True, False]),
                    refer_to_laboratory=random.choice([True, False]),
                    refer_to_optician=random.choice([True, False]),
                    refer_to_specialist=random.choice([True, False]),
                    completed=True,
                    completed_at=completed_at,
                    created_by=physician,
                    updated_by=physician
                )
                consultations.append(consultation)
        
        self.stdout.write(f'  ✅ Created {len(consultations)} consultations')
        return consultations

    def create_lab_tests(self, patients, consultations, users, days_back):
        """Create laboratory tests"""
        self.stdout.write('\n🧪 Creating laboratory tests...')
        lab_tests = []
        lab_techs = users['MLS']
        
        for consultation in consultations:
            if consultation.refer_to_laboratory or random.random() > 0.5:
                lab_tech = random.choice(lab_techs) if lab_techs else None
                completed_at = consultation.completed_at + timedelta(days=random.randint(1, 3))
                
                lab_test = LaboratoryTest.objects.create(
                    patient=consultation.patient,
                    consultation=consultation,
                    malaria_parasite=random.choice(['POSITIVE', 'NEGATIVE', 'PENDING']),
                    random_blood_sugar=round(random.uniform(4.0, 12.0), 1),
                    hbsag=random.choice(['POSITIVE', 'NEGATIVE', 'PENDING']),
                    other_tests=random.choice(['', 'Liver Function Test', 'Kidney Function Test', 'Full Blood Count']),
                    notes=f"Lab tests for {consultation.patient.full_name}",
                    completed=random.choice([True, False]),
                    completed_at=completed_at if random.random() > 0.3 else None,
                    completed_by=lab_tech,
                    created_by=lab_tech,
                    updated_by=lab_tech
                )
                lab_tests.append(lab_test)
        
        self.stdout.write(f'  ✅ Created {len(lab_tests)} lab tests')
        return lab_tests

    def create_optical_assessments(self, patients, consultations, users, days_back):
        """Create optical assessments"""
        self.stdout.write('\n👁️ Creating optical assessments...')
        optical_assessments = []
        opticians = users['OPTOMETRIST']
        
        for consultation in consultations:
            if consultation.refer_to_optician or random.random() > 0.7:
                optician = random.choice(opticians) if opticians else None
                completed_at = consultation.completed_at + timedelta(days=random.randint(1, 5))
                
                assessment = OpticalAssessment.objects.create(
                    patient=consultation.patient,
                    consultation=consultation,
                    is_walk_in=random.choice([True, False]),
                    visual_acuity_left=random.choice(['6/6', '6/9', '6/12', '6/18']),
                    visual_acuity_right=random.choice(['6/6', '6/9', '6/12', '6/18']),
                    refractive_error=random.choice(['', 'Myopia', 'Hyperopia', 'Astigmatism']),
                    eye_health_notes=random.choice(['', 'Normal', 'Cataract detected', 'Glaucoma suspect']),
                    glasses_allocated=random.randint(0, 2),
                    glasses_type=random.choice(['', 'Reading', 'Distance', 'Bifocal', 'Progressive']),
                    glasses_prescription=f"OD: -{random.uniform(0.5, 3.0):.1f}, OS: -{random.uniform(0.5, 3.0):.1f}",
                    completed=True,
                    completed_at=completed_at,
                    completed_by=optician,
                    viewed_by_optician=True,
                    viewed_at=completed_at,
                    viewed_by_physician=False,
                    created_by=optician,
                    updated_by=optician
                )
                optical_assessments.append(assessment)
        
        self.stdout.write(f'  ✅ Created {len(optical_assessments)} optical assessments')
        return optical_assessments

    def create_pharmacy_orders(self, patients, consultations, users, days_back):
        """Create pharmacy orders"""
        self.stdout.write('\n💊 Creating pharmacy orders...')
        pharmacy_orders = []
        pharmacists = users['PHARMACY']
        
        drug_names = [
            'Paracetamol 500mg', 'Amoxicillin 500mg', 'Ciprofloxacin 500mg',
            'Omeprazole 20mg', 'Metformin 500mg', 'Lisinopril 10mg',
            'Amlodipine 10mg', 'Ibuprofen 200mg', 'Vitamin C 100mg',
            'Diclofenac 50mg', 'Hyoscine 10mg', 'Piriton 4mg'
        ]
        
        for consultation in consultations:
            if consultation.refer_to_pharmacy or random.random() > 0.6:
                pharmacist = random.choice(pharmacists) if pharmacists else None
                created_at = consultation.completed_at + timedelta(days=random.randint(0, 2))
                
                for _ in range(random.randint(1, 3)):
                    order = PharmacyOrder.objects.create(
                        patient=consultation.patient,
                        consultation=consultation,
                        drug_name=random.choice(drug_names),
                        quantity=random.randint(1, 10),
                        dosage=f"{random.randint(1, 3)} tablet(s) per day",
                        frequency=random.choice(['Once daily', 'Twice daily', 'Three times daily']),
                        duration=f"{random.randint(3, 14)} days",
                        instructions=f"Take as prescribed for {consultation.patient.full_name}",
                        dispensed=random.choice([True, False]),
                        dispensed_at=timezone.now() - timedelta(days=random.randint(0, 5)) if random.random() > 0.3 else None,
                        dispensed_by=pharmacist if random.random() > 0.3 else None,
                        created_by=consultation.created_by,
                        updated_by=consultation.created_by
                    )
                    pharmacy_orders.append(order)
        
        self.stdout.write(f'  ✅ Created {len(pharmacy_orders)} pharmacy orders')
        return pharmacy_orders

    def create_drugs(self):
        """Create drug inventory"""
        self.stdout.write('\n💊 Creating drug inventory...')
        
        drugs_data = [
            {'name': 'Paracetamol 500mg', 'category': 'ANALGESICS', 'quantity': 1000},
            {'name': 'Amoxicillin 500mg', 'category': 'ANTIBIOTICS', 'quantity': 500},
            {'name': 'Ciprofloxacin 500mg', 'category': 'ANTIBIOTICS', 'quantity': 200},
            {'name': 'Omeprazole 20mg', 'category': 'GASTROINTESTINAL', 'quantity': 300},
            {'name': 'Metformin 500mg', 'category': 'ANTIDIABETIC', 'quantity': 150},
            {'name': 'Lisinopril 10mg', 'category': 'ANTIHYPERTENSIVE', 'quantity': 200},
            {'name': 'Amlodipine 10mg', 'category': 'ANTIHYPERTENSIVE', 'quantity': 180},
            {'name': 'Ibuprofen 200mg', 'category': 'ANALGESICS', 'quantity': 800},
            {'name': 'Vitamin C 100mg', 'category': 'VITAMINS', 'quantity': 1200},
            {'name': 'Diclofenac 50mg', 'category': 'ANALGESICS', 'quantity': 300},
            {'name': 'Hyoscine 10mg', 'category': 'GASTROINTESTINAL', 'quantity': 100},
            {'name': 'Piriton 4mg', 'category': 'OTHER', 'quantity': 200},
            {'name': 'Vitamin B complex', 'category': 'VITAMINS', 'quantity': 500},
            {'name': 'Ferrous sulphate 200mg', 'category': 'VITAMINS', 'quantity': 400},
            {'name': 'Folic Acid 5mg', 'category': 'VITAMINS', 'quantity': 300},
        ]
        
        drugs = []
        for drug_data in drugs_data:
            drug, created = Drug.objects.get_or_create(
                name=drug_data['name'],
                defaults={
                    'category': drug_data['category'],
                    'quantity': drug_data['quantity'],
                    'reorder_level': random.randint(10, 50),
                    'is_active': True
                }
            )
            drugs.append(drug)
        
        self.stdout.write(f'  ✅ Created/Updated {len(drugs)} drugs')
        return drugs

    def create_pharmacy_dispensing(self, patients, pharmacy_orders, drugs, users, days_back):
        """Create pharmacy dispensing records"""
        self.stdout.write('\n💊 Creating pharmacy dispensing records...')
        dispensing = []
        pharmacists = users['PHARMACY']
        
        for order in pharmacy_orders:
            if order.dispensed and random.random() > 0.3:
                pharmacist = random.choice(pharmacists) if pharmacists else None
                drug = random.choice(drugs) if drugs else None
                
                dispense = PharmacyDispensing.objects.create(
                    patient=order.patient,
                    prescription=order,
                    drug=drug,
                    quantity_dispensed=order.quantity,
                    dispensing_date=order.dispensed_at or timezone.now(),
                    dispensed_by=pharmacist,
                    notes=f"Dispensed {order.quantity} units of {order.drug_name}"
                )
                dispensing.append(dispense)
        
        self.stdout.write(f'  ✅ Created {len(dispensing)} dispensing records')
        return dispensing

    def create_notifications(self, users, patients, days_back):
        """Create notifications for users"""
        self.stdout.write('\n🔔 Creating notifications...')
        notifications = []
        
        notification_messages = [
            'New patient registered: {patient}',
            'Lab results ready for {patient}',
            'Optical assessment completed for {patient}',
            'Prescription ready for dispensing: {patient}',
            'Nursing assessment completed for {patient}',
            'Consultation scheduled for {patient}',
            'Pharmacy order pending for {patient}',
            'Lab test results available for {patient}'
        ]
        
        for role, user_list in users.items():
            for user in user_list:
                for _ in range(random.randint(2, 5)):
                    patient = random.choice(patients) if patients else None
                    if patient:
                        message = random.choice(notification_messages).format(patient=patient.full_name)
                        created_at = timezone.now() - timedelta(days=random.randint(0, days_back))
                        
                        notification = Notification.objects.create(
                            recipient=user,
                            message=message,
                            is_read=random.choice([True, False]),
                            created_at=created_at,
                            link=f'/dashboard/'
                        )
                        notifications.append(notification)
        
        self.stdout.write(f'  ✅ Created {len(notifications)} notifications')
        return notifications

    def print_summary(self, patients, nursing, consultations, lab_tests, optical, pharmacy_orders, dispensing, notifications):
        """Print summary statistics"""
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 DATA SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'👥 Patients: {len(patients)}')
        self.stdout.write(f'🩺 Nursing Assessments: {len(nursing)}')
        self.stdout.write(f'👨‍⚕️ Consultations: {len(consultations)}')
        self.stdout.write(f'🧪 Lab Tests: {len(lab_tests)}')
        self.stdout.write(f'👁️ Optical Assessments: {len(optical)}')
        self.stdout.write(f'💊 Pharmacy Orders: {len(pharmacy_orders)}')
        self.stdout.write(f'💊 Dispensing Records: {len(dispensing)}')
        self.stdout.write(f'🔔 Notifications: {len(notifications)}')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ Data population complete!'))
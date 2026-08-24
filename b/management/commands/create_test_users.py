# b/management/commands/create_test_users.py


from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import date, timedelta
import random
import string
from b.models import UserProfile, Patient, PatientWorkflow

class Command(BaseCommand):
    help = 'Create test users and patients for the medical outreach system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=3,
            help='Number of users to create per role (default: 3)',
        )
        parser.add_argument(
            '--patients',
            type=int,
            default=50,
            help='Number of patients to create (default: 50)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='123',
            help='Default password for all test users (default: 123)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate users even if they exist',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing users and patients before creating',
        )

    def handle(self, *args, **options):
        user_count = options['users']
        patient_count = options['patients']
        default_password = options['password']
        force = options['force']
        clear = options['clear']
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write('🏥 MEDICAL OUTREACH SYSTEM - TEST DATA CREATION')
        self.stdout.write('📍 Location: Ibadan, Oyo State, Nigeria')
        self.stdout.write('='*70 + '\n')
        
        # Clear existing data if requested
        if clear:
            self.clear_data()
        
        # Create users
        self.create_users(user_count, default_password, force)
        
        # Create patients
        self.create_patients(patient_count)
        
        # Create superuser if none exists
        self.create_superuser(default_password)
        
        # Summary
        self.print_summary(default_password)

    def clear_data(self):
        """Clear all existing users and patients"""
        self.stdout.write('🧹 Clearing existing data...')
        
        # Delete patients first (due to foreign keys)
        PatientWorkflow.objects.all().delete()
        Patient.objects.all().delete()
        
        # Delete user profiles
        UserProfile.objects.all().delete()
        
        # Delete users except superuser
        User.objects.exclude(is_superuser=True).delete()
        
        self.stdout.write(self.style.SUCCESS('✅ Data cleared successfully!\n'))

    def create_users(self, count, default_password, force):
        """Create test users for all roles"""
        
        roles = [
            {
                'role': 'HIM',
                'first_names': ['John', 'Mary', 'David', 'Sarah', 'Michael', 'Jennifer', 'Robert', 'Lisa', 'James', 'Patricia'],
                'last_names': ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'],
                'departments': ['Health Information Management', 'Medical Records', 'Data Management', 'Quality Assurance']
            },
            {
                'role': 'NURSE',
                'first_names': ['Alice', 'Carol', 'Eve', 'Grace', 'Heidi', 'Ivy', 'Judy', 'Kate', 'Laura', 'Megan'],
                'last_names': ['Nightingale', 'Florence', 'Clara', 'Edith', 'Mary', 'Linda', 'Patricia', 'Barbara', 'Elizabeth', 'Susan'],
                'departments': ['Emergency', 'General Ward', 'ICU', 'Pediatrics', 'Maternity', 'Surgical', 'Oncology']
            },
            {
                'role': 'PHYSICIAN',
                'first_names': ['James', 'Robert', 'William', 'Charles', 'Thomas', 'Henry', 'Edward', 'Frank', 'David', 'Richard'],
                'last_names': ['Okafor', 'Adebayo', 'Okonkwo', 'Eze', 'Nwosu', 'Igwe', 'Obi', 'Nnamdi', 'Ogunleye', 'Bello'],
                'departments': ['Internal Medicine', 'Pediatrics', 'Surgery', 'Cardiology', 'Neurology', 'Orthopedics', 'Ophthalmology']
            },
            {
                'role': 'PHARMACY',
                'first_names': ['Pharma', 'Dispense', 'Medi', 'Cure', 'Heal', 'Vital', 'Care', 'Health', 'Remedy', 'Relief'],
                'last_names': ['Wick', 'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez'],
                'departments': ['Pharmacy', 'Clinical Pharmacy', 'Dispensary', 'Hospital Pharmacy']
            },
            {
                'role': 'MLS',
                'first_names': ['Scientist', 'Lab', 'Micro', 'Bio', 'Chem', 'Patho', 'Serum', 'Virus', 'Cell', 'Gene'],
                'last_names': ['White', 'Black', 'Green', 'Blue', 'Red', 'Yellow', 'Purple', 'Orange', 'Gray', 'Brown'],
                'departments': ['Microbiology', 'Hematology', 'Clinical Chemistry', 'Immunology', 'Pathology', 'Blood Bank']
            },
            {
                'role': 'OPTOMETRIST',
                'first_names': ['Vision', 'Eye', 'Sight', 'Clear', 'Focus', 'Lens', 'Retina', 'Cornea', 'Iris', 'Pupil'],
                'last_names': ['Spectrum', 'Vision', 'Optics', 'Clearview', 'Eyecare', 'Sightline', 'Focuspoint', 'Lenscraft'],
                'departments': ['Optometry', 'Optical', 'Eye Clinic', 'Vision Center']
            }
        ]

        self.stdout.write('👥 Creating test users...')
        self.stdout.write('-' * 50)

        # Create users for each role
        for role_data in roles:
            role = role_data['role']
            first_names = role_data['first_names']
            last_names = role_data['last_names']
            departments = role_data['departments']
            
            # Get or create group
            group, created = Group.objects.get_or_create(name=role)
            
            created_count = 0
            for i in range(count):
                # Generate unique username
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                username = f"{role.lower()}_{first_name.lower()}{i+1}"
                email = f"{username}@medicaloutreach.com"
                
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    if force:
                        # Delete existing user and profile
                        user = User.objects.get(username=username)
                        UserProfile.objects.filter(user=user).delete()
                        user.delete()
                        self.stdout.write(self.style.WARNING(f'  🔄 Recreating {username}...'))
                    else:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  {username} already exists, skipping...'))
                        continue
                
                # Create user
                user = User.objects.create_user(
                    username=username,
                    password=default_password,
                    email=email,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Add to group
                user.groups.add(group)
                
                # Get or create profile (signal may have created one)
                profile, profile_created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'role': role,
                        'employee_id': f"{role[:3].upper()}{''.join(random.choices(string.digits, k=6))}",
                        'phone': f"080{''.join(random.choices(string.digits, k=8))}",
                        'department': random.choice(departments),
                        'is_active': True
                    }
                )
                
                # If profile already exists, update it
                if not profile_created:
                    profile.role = role
                    profile.employee_id = f"{role[:3].upper()}{''.join(random.choices(string.digits, k=6))}"
                    profile.phone = f"080{''.join(random.choices(string.digits, k=8))}"
                    profile.department = random.choice(departments)
                    profile.is_active = True
                    profile.save()
                
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ {role}: {username} ({first_name} {last_name})'))
                self.stdout.write(f'     👤 Employee ID: {profile.employee_id}')
                self.stdout.write(f'     🔑 Password: {default_password}')
                self.stdout.write(f'     🏢 Department: {profile.department}')
                self.stdout.write(f'     📱 Phone: {profile.phone}\n')
            
            if created_count == 0:
                self.stdout.write(self.style.WARNING(f'  ⚠️  No new {role} users created (all exist)\n'))

    def create_patients(self, count):
        """Create test patients - all from Ibadan, Nigeria"""
        
        # Yoruba names (common in Ibadan)
        first_names = [
            'Ade', 'Bola', 'Chidi', 'Damilola', 'Emeka', 'Funke', 'Gbenga', 
            'Hauwa', 'Ikenna', 'Joy', 'Kemi', 'Lola', 'Musa', 'Ngozi', 
            'Olu', 'Peter', 'Queen', 'Ruth', 'Segun', 'Tunde', 'Uche', 
            'Victor', 'Wale', 'Yemi', 'Zainab', 'Abiola', 'Bisi', 'Chinwe',
            'Dayo', 'Efe', 'Femi', 'Gift', 'Hope', 'Ifeanyi', 'Jide',
            'Kayode', 'Lekan', 'Moyo', 'Nkechi', 'Obi', 'Precious',
            'Tayo', 'Ugo', 'Vivian', 'Wura', 'Yinka', 'Zara', 'Adeola',
            'Bukunmi', 'Chuka', 'Dara', 'Ebi', 'Folake', 'Goke', 'Hakeem'
        ]
        
        last_names = [
            'Adebayo', 'Okonkwo', 'Eze', 'Nwosu', 'Igwe', 'Obi', 'Nnamdi',
            'Ogunleye', 'Bello', 'Adeyemi', 'Okafor', 'Okoro', 'Onyeka',
            'Chukwu', 'Oluwaseun', 'Akinwale', 'Balogun', 'Fashola',
            'Gbadegesin', 'Ibrahim', 'Jolayemi', 'Kolawole', 'Lawal',
            'Majekodunmi', 'Nwachukwu', 'Ogunbiyi', 'Oladapo', 'Oluwole',
            'Oyedele', 'Oyewole', 'Salami', 'Shittu', 'Suleiman', 'Umar',
            'Afolabi', 'Akinola', 'Alabi', 'Bamidele', 'Durojaiye', 'Falola',
            'Ilori', 'Jolaoso', 'Kunle', 'Ogunyemi', 'Olanrewaju', 'Oyelade'
        ]
        
        # Ibadan locations (streets and areas)
        ibadan_areas = [
            'Bodija', 'Mokola', 'Agodi', 'Oke-Ado', 'Ring Road', 
            'Aleshinloye', 'Oluyole', 'Challenge', 'Dugbe', 'Gbagi',
            'Oke Bola', 'Iwo Road', 'Apata', 'Orita', 'Moniya',
            'Akobo', 'Odo-Ona', 'Kolawole', 'Orogun', 'Sango',
            'UI Campus', 'Poly Road', 'Ojoo', 'Awa', 'Ataoja'
        ]
        
        ibadan_streets = [
            'Awolowo Avenue', 'Queen Elizabeth Road', 'Mokola Road',
            'Oyo Road', 'Oba Adebimpe Road', 'Alesinloye Road',
            'Old Ife Road', 'New Ife Road', 'Iwo Road', 'Ring Road',
            'Liberty Road', 'Onireke Street', 'Oke Bola Road',
            'Ogunpa Road', 'Eleyele Road', 'Ajeigbe Street',
            'Agodi Road', 'Ososami Road', 'Oke Ado Road',
            'Olorunsogo Street', 'Oranyan Street', 'Ajibade Street'
        ]
        
        genders = ['MALE', 'FEMALE']
        
        self.stdout.write('\n🏥 Creating test patients...')
        self.stdout.write('📍 All patients from Ibadan, Oyo State, Nigeria')
        self.stdout.write('-' * 50)

        created_count = 0
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            gender = random.choice(genders)
            
            # Generate date of birth (18-70 years old)
            year = random.randint(1953, 2005)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            dob = date(year, month, day)
            
            # Generate unique hospital number
            hospital_number = f"HIM{''.join(random.choices(string.digits, k=6))}"
            while Patient.objects.filter(hospital_number=hospital_number).exists():
                hospital_number = f"HIM{''.join(random.choices(string.digits, k=6))}"
            
            # Generate phone (Ibadan/Nigeria numbers)
            phone_prefixes = ['080', '081', '090', '070', '091']
            phone = f"{random.choice(phone_prefixes)}{''.join(random.choices(string.digits, k=8))}"
            
            # Generate Ibadan address
            area = random.choice(ibadan_areas)
            street = random.choice(ibadan_streets)
            house_number = random.randint(1, 200)
            address = f"{house_number} {street}, {area}, Ibadan, Oyo State"
            
            # Create patient
            patient = Patient.objects.create(
                hospital_number=hospital_number,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                gender=gender,
                phone=phone,
                email=f"{first_name.lower()}.{last_name.lower()}@gmail.com",
                address=address,
                current_stage='REGISTERED'
            )
            
            # Create workflow
            PatientWorkflow.objects.create(
                patient=patient,
                current_stage='REGISTERED'
            )
            
            created_count += 1
            age = patient.age_data
            age_display = f"{age['years']} years, {age['months']} months" if age else "Unknown"
            
            self.stdout.write(self.style.SUCCESS(f'  ✅ Patient {i+1}: {hospital_number} - {first_name} {last_name}'))
            self.stdout.write(f'     🎂 DOB: {dob} ({age_display})')
            self.stdout.write(f'     ⚧️ Gender: {gender}')
            self.stdout.write(f'     📱 Phone: {phone}')
            self.stdout.write(f'     📍 Address: {address}')
            self.stdout.write(f'     📋 Status: REGISTERED\n')
        
        if created_count == 0:
            self.stdout.write(self.style.WARNING('  ⚠️  No new patients created\n'))

    def create_superuser(self, default_password):
        """Create superuser if none exists"""
        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write('\n👑 Creating superuser...')
            User.objects.create_superuser(
                username='admin',
                email='admin@medicaloutreach.com',
                password=default_password
            )
            self.stdout.write(self.style.SUCCESS(f'  ✅ Superuser created: admin / {default_password}'))

    def print_summary(self, default_password):
        """Print summary of created data"""
        
        total_users = User.objects.count()
        total_profiles = UserProfile.objects.count()
        total_patients = Patient.objects.count()
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('✅ TEST DATA CREATED SUCCESSFULLY!'))
        self.stdout.write('='*70)
        self.stdout.write(f'👥 Total Users: {total_users}')
        self.stdout.write(f'👤 Total Profiles: {total_profiles}')
        self.stdout.write(f'🏥 Total Patients: {total_patients}')
        self.stdout.write(f'📍 Location: Ibadan, Oyo State, Nigeria')
        self.stdout.write(f'🔑 Default Password: {default_password}')
        
        self.stdout.write('\n📋 LOGIN CREDENTIALS:')
        self.stdout.write('-' * 50)
        
        # Show sample users for each role
        roles = ['HIM', 'NURSE', 'PHYSICIAN', 'PHARMACY', 'MLS', 'OPTOMETRIST']
        for role in roles:
            users = User.objects.filter(userprofile__role=role)[:3]
            if users:
                self.stdout.write(f'\n  {role}:')
                for user in users:
                    self.stdout.write(f'    • {user.username} / {default_password}')
            else:
                self.stdout.write(f'\n  {role}: No users found')
        
        self.stdout.write('\n' + '-' * 50)
        self.stdout.write(f'  Admin: admin / {default_password}')
        self.stdout.write('='*70)
        
        self.stdout.write('\n📝 QUICK TEST SCENARIOS:')
        self.stdout.write('-' * 50)
        self.stdout.write('1️⃣ HIM registers patients and assigns nurses/physicians')
        self.stdout.write('2️⃣ Nurses perform assessments (vitals)')
        self.stdout.write('3️⃣ Physicians conduct consultations')
        self.stdout.write('4️⃣ Pharmacy dispenses medications')
        self.stdout.write('5️⃣ Laboratory runs tests')
        self.stdout.write('6️⃣ Opticians perform optical assessments')
        self.stdout.write('='*70 + '\n')
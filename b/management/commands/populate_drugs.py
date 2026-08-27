# b/management/commands/populate_drugs.py

from django.core.management.base import BaseCommand
from b.models import Drug

class Command(BaseCommand):
    help = 'Populate drugs from the provided list'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('💊 POPULATING DRUG INVENTORY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Drug list with categories
        drugs_data = [
            # ANTIHYPERTENSIVE
            {'name': 'Amlodipine 10mg', 'category': 'ANTIHYPERTENSIVE', 'quantity': 532},
            {'name': 'Amlodipine 5mg', 'category': 'ANTIHYPERTENSIVE', 'quantity': 84},
            {'name': 'Lisinopril 10mg', 'category': 'ANTIHYPERTENSIVE', 'quantity': 508},
            {'name': 'Lisinopril 5mg', 'category': 'ANTIHYPERTENSIVE', 'quantity': 28},
            {'name': 'Nifedipine 20mg', 'category': 'ANTIHYPERTENSIVE', 'quantity': 270},
            
            # ANTIMALARIAL
            {'name': 'ACT 80/480mg', 'category': 'ANTIMALARIAL', 'quantity': 360},
            {'name': 'ACT 20/120mg', 'category': 'ANTIMALARIAL', 'quantity': 480},
            {'name': 'Artemether Injection 80mg', 'category': 'ANTIMALARIAL', 'quantity': 6},
            
            # ANALGESICS
            {'name': 'Paracetamol 500mg', 'category': 'ANALGESICS', 'quantity': 1000},
            {'name': 'Paracetamol Injection 300mg', 'category': 'ANALGESICS', 'quantity': 10},
            {'name': 'Paracetamol syrup', 'category': 'ANALGESICS', 'quantity': 10},
            {'name': 'Diclofenac Injection 75mg', 'category': 'ANALGESICS', 'quantity': 10},
            {'name': 'Diclofenac potassium 50mg', 'category': 'ANALGESICS', 'quantity': 600},
            {'name': 'Diclofenac Sodium 100mg', 'category': 'ANALGESICS', 'quantity': 280},
            {'name': 'Diclofenanc gel', 'category': 'ANALGESICS', 'quantity': 10},
            {'name': 'Ibuprofen 200mg', 'category': 'ANALGESICS', 'quantity': 1000},
            {'name': 'Ibuprofen suspension', 'category': 'ANALGESICS', 'quantity': 2},
            
            # ANTIBIOTICS
            {'name': 'Amoxicillin 500mg', 'category': 'ANTIBIOTICS', 'quantity': 500},
            {'name': 'Amoxicillin 250mg', 'category': 'ANTIBIOTICS', 'quantity': 200},
            {'name': 'Amoxicillin suspension', 'category': 'ANTIBIOTICS', 'quantity': 11},
            {'name': 'Amoxiclav 625mg', 'category': 'ANTIBIOTICS', 'quantity': 56},
            {'name': 'Ampiclox 500mg', 'category': 'ANTIBIOTICS', 'quantity': 70},
            {'name': 'Azithromycin 500mg', 'category': 'ANTIBIOTICS', 'quantity': 20},
            {'name': 'Cefixime 400mg', 'category': 'ANTIBIOTICS', 'quantity': 60},
            {'name': 'Ciprofloxacin 500mg', 'category': 'ANTIBIOTICS', 'quantity': 90},
            {'name': 'Doxycycline 100mg', 'category': 'ANTIBIOTICS', 'quantity': 200},
            {'name': 'Flagyl 200mg', 'category': 'ANTIBIOTICS', 'quantity': 500},
            {'name': 'Flagyl syrup', 'category': 'ANTIBIOTICS', 'quantity': 6},
            {'name': 'Mectizan 3mg', 'category': 'ANTIBIOTICS', 'quantity': 500},
            {'name': 'Metronidazole 400mg', 'category': 'ANTIBIOTICS', 'quantity': 100},
            
            # ANTIFUNGAL
            {'name': 'Whitefield ointment', 'category': 'ANTIFUNGAL', 'quantity': 6},
            
            # GASTROINTESTINAL
            {'name': 'Gelusil', 'category': 'GASTROINTESTINAL', 'quantity': 500},
            {'name': 'Omeprazole 20mg', 'category': 'GASTROINTESTINAL', 'quantity': 480},
            {'name': 'Hyoscine 10mg', 'category': 'GASTROINTESTINAL', 'quantity': 100},
            
            # VITAMINS & SUPPLEMENTS
            {'name': 'Vitamin C 100mg', 'category': 'VITAMINS', 'quantity': 1000},
            {'name': 'Vitamin C syrup', 'category': 'VITAMINS', 'quantity': 11},
            {'name': 'Vitamin B complex', 'category': 'VITAMINS', 'quantity': 1200},
            {'name': 'Calcium 300mg', 'category': 'VITAMINS', 'quantity': 1000},
            {'name': 'Yeast 300mg', 'category': 'VITAMINS', 'quantity': 1000},
            {'name': 'Zinc 20mg', 'category': 'VITAMINS', 'quantity': 160},
            {'name': 'Ferrous sulphate 200mg', 'category': 'VITAMINS', 'quantity': 1000},
            {'name': 'Folic Acid 5mg', 'category': 'VITAMINS', 'quantity': 500},
            {'name': 'Multivite', 'category': 'VITAMINS', 'quantity': 1000},
            
            # RESPIRATORY
            {'name': 'Broncholyte syrup', 'category': 'RESPIRATORY', 'quantity': 4},
            {'name': 'Cough syrup adult', 'category': 'RESPIRATORY', 'quantity': 2},
            {'name': 'Cough syrup children', 'category': 'RESPIRATORY', 'quantity': 4},
            
            # OTHER
            {'name': 'Avomine 25mg', 'category': 'OTHER', 'quantity': 100},
            {'name': 'Hydrex 25mg', 'category': 'OTHER', 'quantity': 170},
            {'name': 'Piriton 4mg', 'category': 'OTHER', 'quantity': 1000},
            {'name': 'Loratadine 10mg', 'category': 'OTHER', 'quantity': 300},
            {'name': 'Vasoprin 75mg', 'category': 'OTHER', 'quantity': 600},
            {'name': 'Prednesolone', 'category': 'OTHER', 'quantity': 100},
            {'name': 'Metformin 500mg', 'category': 'OTHER', 'quantity': 7},
            {'name': 'Glibemcalmide 5mg', 'category': 'OTHER', 'quantity': 20},
            {'name': 'Albendazole', 'category': 'OTHER', 'quantity': 60},
            {'name': 'ORS', 'category': 'OTHER', 'quantity': 10},
            
            # OPHTHALMIC
            {'name': 'Ofloxacin eye drop', 'category': 'OPHTHALMIC', 'quantity': 1},
            {'name': 'Antallerge eye drop', 'category': 'OPHTHALMIC', 'quantity': 10},
            {'name': 'Chloramphenicol eye drop', 'category': 'OPHTHALMIC', 'quantity': 2},
            {'name': 'Gentamicine eye drop', 'category': 'OPHTHALMIC', 'quantity': 4},
            
            # INJECTABLES
            {'name': 'Hydrocortisone Injection 100mg', 'category': 'INJECTABLES', 'quantity': 4},
        ]

        added_count = 0
        skipped_count = 0

        for drug_data in drugs_data:
            name = drug_data['name']
            category = drug_data['category']
            quantity = drug_data['quantity']

            # Check if drug already exists
            if Drug.objects.filter(name__iexact=name).exists():
                self.stdout.write(self.style.WARNING(f'⚠️ Skipping "{name}" - already exists'))
                skipped_count += 1
                continue

            # Create the drug
            Drug.objects.create(
                name=name,
                category=category,
                quantity=quantity,
                reorder_level=10,
                is_active=True
            )
            added_count += 1
            self.stdout.write(self.style.SUCCESS(f'✅ Added: {name} ({quantity} units) - {category}'))

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'📊 SUMMARY:'))
        self.stdout.write(self.style.SUCCESS(f'   ✅ Added: {added_count} drugs'))
        self.stdout.write(self.style.WARNING(f'   ⚠️ Skipped: {skipped_count} drugs (already exist)'))
        self.stdout.write(self.style.SUCCESS(f'   📦 Total drugs in inventory: {Drug.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
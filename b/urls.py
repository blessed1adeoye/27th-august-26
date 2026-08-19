# b/urls.py


from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'b'

urlpatterns = [
    # Home & Auth
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='b/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # HIM (Patient Management)
    path('patients/register/', views.patient_registration, name='patient_registration'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patient/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('assign-nurse/', views.assign_nurse, name='assign_nurse'),
    
    # Nursing
    path('nursing/dashboard/', views.nursing_dashboard, name='nursing_dashboard'),
    path('nursing/assessment/<int:patient_id>/', views.nursing_assessment, name='nursing_assessment'),
    
    # Doctor
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/consultation/<int:patient_id>/', views.doctor_consultation, name='doctor_consultation'),
    
    # Pharmacy
    path('pharmacy/dashboard/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('pharmacy/dispense/<int:order_id>/', views.pharmacy_dispense, name='pharmacy_dispense'),
    path('pharmacy/order/<int:patient_id>/', views.pharmacy_create_order, name='pharmacy_create_order'),
    
    # Laboratory
    path('lab/dashboard/', views.laboratory_dashboard, name='laboratory_dashboard'),
    path('lab/test/<int:test_id>/', views.laboratory_test, name='laboratory_test'),
    
    # Optician
    path('optician/dashboard/', views.optician_dashboard, name='optician_dashboard'),
    path('optician/assessment/', views.optician_assessment, name='optician_assessment_walkin'),
    path('optician/assessment/<int:patient_id>/', views.optician_assessment, name='optician_assessment'),
    
    # User Management
    path('users/register/', views.user_registration, name='user_registration'),
    path('users/', views.user_list, name='user_list'),
    path('user/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('user/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('user/<int:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    
    # API
    path('api/age/', views.get_age_from_dob, name='get_age'),
]
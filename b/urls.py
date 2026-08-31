# b/urls.py


from django.urls import path
from . import views
from . import views_admin

app_name = 'b'

urlpatterns = [
    # Home & Auth
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),  
    path('logout/', views.logout_view, name='logout'),
    
    # HIM (Patient Management)
    path('patients/register/', views.patient_registration, name='patient_registration'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patient/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('assign-nurse/', views.assign_nurse, name='assign_nurse'),
    
    # Nursing
    path('nursing/dashboard/', views.nursing_dashboard, name='nursing_dashboard'),
    path('nursing/assessment/<int:patient_id>/', views.nursing_assessment, name='nursing_assessment'),
    path('api/nurse/assignments/debug/', views.nurse_assignment_debug, name='nurse_assignment_debug'),
    
    
    # Doctor
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/consultation/<int:patient_id>/', views.doctor_consultation, name='doctor_consultation'),
    path('api/doctor/dashboard-data/', views.doctor_dashboard_data_api, name='doctor_dashboard_data_api'),
     # Physician - Lab Results
    path('physician/lab-results/', views.physician_lab_results, name='physician_lab_results'),
    path('physician/lab-result/<int:test_id>/', views.physician_lab_result_detail, name='physician_lab_result_detail'),
    
    # Physician - Optician Results
    path('physician/optician-results/', views.physician_optician_results, name='physician_optician_results'),
    path('physician/optician-result/<int:assessment_id>/', views.physician_optician_result_detail, name='physician_optician_result_detail'),
    
    # Pharmacy
    path('pharmacy/dashboard/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('pharmacy/dispense/<int:order_id>/', views.pharmacy_dispense, name='pharmacy_dispense'),
    # path('pharmacy/order/<int:patient_id>/', views.pharmacy_create_order, name='pharmacy_create_order'),


    # Pharmacy Drug Management
    path('pharmacy/drugs/', views.pharmacy_drug_list, name='pharmacy_drug_list'),
    path('pharmacy/drug/add/', views.pharmacy_drug_add, name='pharmacy_drug_add'),
    path('pharmacy/drug/<int:drug_id>/edit/', views.pharmacy_drug_edit, name='pharmacy_drug_edit'),
    path('pharmacy/drug/<int:drug_id>/delete/', views.pharmacy_drug_delete, name='pharmacy_drug_delete'),
    path('pharmacy/dispense-patient/<int:patient_id>/', views.pharmacy_dispense_patient, name='pharmacy_dispense_patient'),
    path('pharmacy/drug/bulk-add/', views.pharmacy_drug_bulk_add, name='pharmacy_drug_bulk_add'),
    
    # Laboratory
    path('lab/dashboard/', views.laboratory_dashboard, name='laboratory_dashboard'),
    path('lab/test/<int:test_id>/', views.laboratory_test, name='laboratory_test'),
    path('api/mls/notification-check/', views.mls_notification_check, name='mls_notification_check'),
    
    
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
    path('api/notification-count/', views.notification_count, name='notification_count'),
    path('api/notifications/latest/', views.notifications_latest, name='notifications_latest'),
    path('api/pharmacy/pending-count/', views.pharmacy_pending_count, name='pharmacy_pending_count'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notifications/hard-reset/', views.hard_reset_notifications, name='hard_reset_notifications'), 
    path('api/nurse/assignments/check/', views.nurse_assignment_check, name='nurse_assignment_check'),
    path('api/dashboard-data/', views.dashboard_data_api, name='dashboard_data_api'),
    path('api/pharmacy/notification-check/', views.pharmacy_notification_check, name='pharmacy_notification_check'),
    path('api/physician/mark-lab-results-read/', views.mark_lab_results_read, name='mark_lab_results_read'),
    path('api/optician/notification-check/', views.optician_notification_check, name='optician_notification_check'),
    path('api/nursing/dashboard-data/', views.nursing_dashboard_data_api, name='nursing_dashboard_data_api'),

    # # Admin Dashboard
    # path('admin/dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    # path('api/admin/dashboard-data/', views_admin.admin_dashboard_data, name='admin_dashboard_data'),
    # path('api/admin/export-data/', views_admin.admin_export_data, name='admin_export_data'),

    # ===== FIX: Super Admin Dashboard - Use /dashboard-admin/ instead =====
    path('dashboard-admin/', views_admin.admin_dashboard, name='admin_dashboard'),
    
    # ===== FIX: Admin Dashboard Data API =====
    path('api/admin/dashboard-data/', views_admin.admin_dashboard_data, name='admin_dashboard_data'),
    
    # ===== FIX: Admin Export Data API =====
    path('api/admin/export-data/', views_admin.admin_export_data, name='admin_export_data'),
    


#     # Debug URLs
#     path('debug/notifications/', views.debug_notification_count, name='debug_notification_count'),
#     path('debug/pharmacy-orders/', views.debug_pharmacy_orders, name='debug_pharmacy_orders'),
#     path('debug/mark-read/', views.debug_mark_notifications_read, name='debug_mark_notifications_read'),
]
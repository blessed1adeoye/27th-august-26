# b/views.py

@login_required
@role_required(['PHYSICIAN'])
def doctor_dashboard(request):
    # ... your code ...
    context = {
        # ... your context ...
        'page': 'doctor',  # This activates the consultations link
    }
    return render(request, 'b/doctor/dashboard.html', context)

@login_required
@role_required(['PHYSICIAN'])
def physician_lab_results(request):
    # ... your code ...
    context = {
        # ... your context ...
        'page': 'lab_results',  # This activates the Lab Results link
    }
    return render(request, 'b/doctor/lab_results.html', context)

@login_required
@role_required(['PHYSICIAN'])
def physician_lab_result_detail(request, test_id):
    # ... your code ...
    context = {
        # ... your context ...
        'page': 'lab_result_detail',  # This activates the Lab Results link
    }
    return render(request, 'b/doctor/lab_result_detail.html', context)

@login_required
@role_required(['PHYSICIAN'])
def physician_optician_results(request):
    # ... your code ...
    context = {
        # ... your context ...
        'page': 'optician_results',  # This activates the Optician Results link
    }
    return render(request, 'b/doctor/optician_results.html', context)

@login_required
@role_required(['PHYSICIAN'])
def physician_optician_result_detail(request, assessment_id):
    # ... your code ...
    context = {
        # ... your context ...
        'page': 'optician_result_detail',  # This activates the Optician Results link
    }
    return render(request, 'b/doctor/optician_result_detail.html', context)
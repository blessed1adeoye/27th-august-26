// static/js/consultation_form.js - UPDATED VERSION WITH FIXES

// Utility function to get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Consultation form loaded');
    console.log('Consultation ID:', window.consultationId);
    console.log('CSRF Token:', window.CSRF_TOKEN ? 'Present' : 'Missing');
    
    // Initialize complaint form
    setupComplaints();
    
    // Setup save buttons
    setupSaveButtons();
    
    // Setup ECG/EEG radio buttons
    setupRadioButtons();
    
    // Validate critical data on load
    validateCriticalData();
});

function validateCriticalData() {
    // Get CSRF token from multiple sources
    const csrfFromWindow = window.CSRF_TOKEN;
    const csrfFromCookie = getCookie('csrftoken');
    
    // Use the most reliable CSRF token
    if (!csrfFromWindow || csrfFromWindow.length < 10) {
        if (csrfFromCookie && csrfFromCookie.length > 10) {
            window.CSRF_TOKEN = csrfFromCookie;
            console.log('Using CSRF token from cookie');
        } else {
            console.error('No valid CSRF token found');
        }
    }
    
    // Validate consultation ID
    if (!window.consultationId || window.consultationId === '0' || window.consultationId === 'undefined') {
        console.error('Invalid consultation ID:', window.consultationId);
        
        // Try to get it from hidden input
        const hiddenId = document.getElementById('consultation-id');
        if (hiddenId && hiddenId.value) {
            window.consultationId = hiddenId.value;
            console.log('Got consultation ID from hidden input:', window.consultationId);
        } else {
            alert('⚠️ Error: Invalid consultation ID. Please refresh the page.');
        }
    }
}

function setupComplaints() {
    // Add initial complaint row if none exists
    const container = document.getElementById('complaints-container');
    if (container && container.children.length === 0) {
        addComplaintRow();
    }
    
    // Update complaints data on input
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('complaint-input') || 
            e.target.classList.contains('duration-input') ||
            (e.target.tagName === 'SELECT' && e.target.classList.contains('duration-unit'))) {
            updateComplaintsData();
        }
    });
}

function setupSaveButtons() {
    const saveDraftBtn = document.getElementById('saveDraftBtn');
    const completeBtn = document.getElementById('completeBtn');
    
    if (saveDraftBtn) {
        saveDraftBtn.addEventListener('click', function(e) {
            e.preventDefault();
            saveConsultation(false);
        });
    }
    
    if (completeBtn) {
        completeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            saveConsultation(true);
        });
    }
}

function setupRadioButtons() {
    // ECG
    const ecgRadios = document.querySelectorAll('input[name="ecg_required"]');
    ecgRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const details = document.getElementById('ecg-details');
            if (details) {
                details.style.display = this.value === 'yes' ? 'block' : 'none';
            }
        });
        
        // Set default to "no"
        if (!document.querySelector('input[name="ecg_required"]:checked') && radio.value === 'no') {
            radio.checked = true;
        }
    });
    
    // EEG
    const eegRadios = document.querySelectorAll('input[name="eeg_required"]');
    eegRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const details = document.getElementById('eeg-details');
            if (details) {
                details.style.display = this.value === 'yes' ? 'block' : 'none';
            }
        });
        
        // Set default to "no"
        if (!document.querySelector('input[name="eeg_required"]:checked') && radio.value === 'no') {
            radio.checked = true;
        }
    });
}

// Complaint functions
function addComplaintRow() {
    const container = document.getElementById('complaints-container');
    if (!container) return;
    
    const rowId = Date.now();
    const row = document.createElement('div');
    row.className = 'complaint-row';
    row.innerHTML = `
        <div class="row g-3">
            <div class="col-md-7">
                <label class="form-label">Complaint</label>
                <input type="text" class="form-control complaint-input" 
                       placeholder="e.g., Headache, Fever...">
            </div>
            <div class="col-md-3">
                <label class="form-label">Duration</label>
                <input type="number" class="form-control duration-input" 
                       placeholder="1" min="1" max="365" value="1">
            </div>
            <div class="col-md-2">
                <label class="form-label">Unit</label>
                <select class="form-select duration-unit">
                    <option value="day(s)">Day(s)</option>
                    <option value="week(s)">Week(s)</option>
                    <option value="month(s)">Month(s)</option>
                    <option value="year(s)">Year(s)</option>
                </select>
            </div>
        </div>
        <div class="mt-2 text-end">
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.complaint-row').remove(); updateComplaintsData()">
                <i class="fas fa-trash"></i> Remove
            </button>
        </div>
    `;
    
    container.appendChild(row);
    updateComplaintsData();
}

function updateComplaintsData() {
    const complaints = [];
    const rows = document.querySelectorAll('.complaint-row');
    
    rows.forEach(row => {
        const complaintInput = row.querySelector('.complaint-input');
        const durationInput = row.querySelector('.duration-input');
        const durationUnit = row.querySelector('.duration-unit');
        
        if (complaintInput && durationInput && durationUnit) {
            const complaint = complaintInput.value.trim();
            if (complaint) {
                complaints.push({
                    complaint: complaint,
                    duration_value: durationInput.value || "1",
                    duration_unit: durationUnit.value
                });
            }
        }
    });
    
    // Update hidden input
    const hiddenInput = document.getElementById('complaints-data');
    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(complaints);
    }
    
    console.log('Complaints updated:', complaints);
}

// Main save function - UPDATED WITH VALIDATION
async function saveConsultation(complete = false) {
    console.log(`Saving consultation (complete=${complete})`);
    
    // Validate consultation ID
    const consultationId = window.consultationId;
    if (!consultationId || consultationId === 'undefined' || consultationId === '0') {
        alert('❌ Error: Consultation ID is missing or invalid. Please refresh the page.');
        console.error('Missing or invalid consultation ID:', consultationId);
        
        // Show debug info
        console.log('Debug info - Available IDs:');
        console.log('- Window.consultationId:', window.consultationId);
        console.log('- Hidden input value:', document.getElementById('consultation-id')?.value);
        
        return;
    }
    
    // Validate CSRF token
    let csrfToken = window.CSRF_TOKEN;
    if (!csrfToken || csrfToken.length < 10) {
        csrfToken = getCookie('csrftoken');
        if (!csrfToken || csrfToken.length < 10) {
            alert('❌ Error: Security token is missing. Please refresh the page.');
            console.error('Invalid CSRF token length:', csrfToken ? csrfToken.length : 'undefined');
            return;
        }
        window.CSRF_TOKEN = csrfToken;
    }
    
    // Validate if completing
    if (complete) {
        const familyHistory = document.getElementById('family_history')?.value.trim();
        const treatmentPlan = document.getElementById('treatment_plan')?.value.trim();
        
        if (!familyHistory || !treatmentPlan) {
            alert('Please fill in Family History and Treatment Plan before completing.');
            return;
        }
        
        if (!confirm('Are you sure you want to complete this consultation?')) {
            return;
        }
    }
    
    // Show loading
    showLoading(complete ? 'Completing...' : 'Saving...');
    
    // Disable buttons
    const saveBtn = document.getElementById('saveDraftBtn');
    const completeBtn = document.getElementById('completeBtn');
    if (saveBtn) saveBtn.disabled = true;
    if (completeBtn) completeBtn.disabled = true;
    
    try {
        // Gather form data
        const formData = gatherFormData(complete);
        console.log('Form data to send:', formData);
        console.log('Saving to URL:', `/physician/consultation/save/${consultationId}/`);
        console.log('CSRF Token length:', csrfToken.length);
        
        // Send to server
        const response = await fetch(`/physician/consultation/save/${consultationId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(formData)
        });
        
        console.log('Response status:', response.status);
        
        // Handle 403 Forbidden (CSRF error)
        if (response.status === 403) {
            const errorText = await response.text();
            console.error('CSRF Error response:', errorText);
            throw new Error('CSRF verification failed. Please refresh the page and try again.');
        }
        
        // Handle other error statuses
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Response data:', result);
        
        hideLoading();
        
        if (result.success) {
            if (complete) {
                alert('✅ Consultation completed successfully!');
                setTimeout(() => {
                    window.location.href = window.DASHBOARD_URL;
                }, 1000);
            } else {
                alert('💾 Draft saved successfully!');
            }
        } else {
            alert(`❌ Error: ${result.error || 'Failed to save consultation'}`);
        }
        
    } catch (error) {
        console.error('Save error:', error);
        hideLoading();
        
        if (error.message.includes('CSRF')) {
            alert('❌ Security error: Please refresh the page and try again.');
        } else if (error.message.includes('Network')) {
            alert('❌ Network error. Please check your connection and try again.');
        } else {
            alert(`❌ Error: ${error.message}`);
        }
    } finally {
        // Re-enable buttons
        if (saveBtn) saveBtn.disabled = false;
        if (completeBtn) completeBtn.disabled = false;
    }
}

function gatherFormData(complete) {
    const formData = {
        complete: complete
    };
    
    // Get complaints
    const complaintsData = document.getElementById('complaints-data');
    if (complaintsData && complaintsData.value) {
        try {
            formData.complaints = JSON.parse(complaintsData.value);
        } catch (e) {
            console.error('Error parsing complaints:', e);
            formData.complaints = [];
        }
    } else {
        formData.complaints = [];
    }
    
    // Get diagnosis (if exists)
    const diagnosisData = document.getElementById('diagnosis-data');
    if (diagnosisData && diagnosisData.value) {
        try {
            formData.diagnosis = JSON.parse(diagnosisData.value);
        } catch (e) {
            console.error('Error parsing diagnosis:', e);
            formData.diagnosis = [];
        }
    } else {
        formData.diagnosis = [];
    }
    
    // Get text fields
    const textFields = [
        'family_history', 'allergy', 'treatment_plan', 
        'prescription', 'clinical_notes', 'ecg_notes',
        'eeg_notes', 'follow_up_notes'
    ];
    
    textFields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            formData[field] = element.value;
        }
    });
    
    // Get ECG/EEG radio values
    const ecgRadio = document.querySelector('input[name="ecg_required"]:checked');
    formData.ecg_required = ecgRadio ? ecgRadio.value === 'yes' : false;
    
    const eegRadio = document.querySelector('input[name="eeg_required"]:checked');
    formData.eeg_required = eegRadio ? eegRadio.value === 'yes' : false;
    
    // Get follow-up date
    const followUpDate = document.getElementById('follow_up_date');
    if (followUpDate && followUpDate.value) {
        formData.follow_up_date = followUpDate.value;
    }
    
    // Get checkbox values (simplified)
    formData.laboratory_tests = getCheckboxValues('lab-tests-container');
    formData.medications = getCheckboxValues('medications-container');
    formData.injections = getCheckboxValues('injections-container');
    
    return formData;
}

function getCheckboxValues(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];
    
    const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
    const values = [];
    checkboxes.forEach(cb => {
        values.push(cb.value);
    });
    return values;
}

// Helper functions
function showLoading(message) {
    const overlay = document.getElementById('loadingOverlay');
    const messageElement = document.getElementById('loadingMessage');
    
    if (overlay) {
        if (messageElement) {
            messageElement.textContent = message;
        }
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function toggleCompleteButton() {
    const checkbox = document.getElementById('markComplete');
    const button = document.getElementById('completeBtn');
    
    if (checkbox && button) {
        button.disabled = !checkbox.checked;
    }
}

// For debug panel
function getComplaintsData() {
    const input = document.getElementById('complaints-data');
    if (input && input.value) {
        try {
            return JSON.parse(input.value);
        } catch (e) {
            return [];
        }
    }
    return [];
}

// Exposing functions to global scope
window.addComplaintRow = addComplaintRow;
window.saveConsultation = saveConsultation;
window.toggleCompleteButton = toggleCompleteButton;
window.gatherFormData = gatherFormData;
window.getComplaintsData = getComplaintsData;
window.updateComplaintsData = updateComplaintsData;
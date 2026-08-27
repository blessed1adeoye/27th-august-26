this is my present script

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // ============================================
    // MOBILE SIDEBAR TOGGLE
    // ============================================
    
    function toggleMobileSidebar() {
        const sidebar = document.getElementById('mobileSidebar');
        const overlay = document.getElementById('mobileOverlay');
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
        document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
    }
    
    function checkScreenSize() {
        const hamburger = document.querySelector('.hamburger-btn');
        if (window.innerWidth < 768) {
            hamburger.style.display = 'block';
        } else {
            hamburger.style.display = 'none';
            document.getElementById('mobileSidebar').classList.remove('active');
            document.getElementById('mobileOverlay').classList.remove('active');
            document.body.style.overflow = '';
            document.getElementById('doctorPatientSidebar')?.classList.remove('mobile-show');
        }
    }
    
    window.addEventListener('resize', checkScreenSize);
    window.addEventListener('load', checkScreenSize);

    // ============================================
    // DOCTOR PATIENT SIDEBAR
    // ============================================
    
    function filterDoctorPatients() {
        const query = document.getElementById('doctorPatientSearch').value.toLowerCase();
        const items = document.querySelectorAll('#doctorPatientList .patient-item');
        items.forEach(item => {
            const name = item.dataset.name || '';
            const hospital = item.dataset.hospital || '';
            const matches = name.includes(query) || hospital.includes(query);
            item.style.display = matches ? '' : 'none';
        });
    }

    function toggleDoctorPatientSidebar() {
        const sidebar = document.getElementById('doctorPatientSidebar');
        sidebar.classList.toggle('mobile-show');
    }

    document.addEventListener('DOMContentLoaded', function() {
        const currentPath = window.location.pathname;
        const items = document.querySelectorAll('#doctorPatientList .patient-item');
        items.forEach(item => {
            if (item.getAttribute('href') === currentPath) {
                item.classList.add('active');
            }
        });
    });

    // ============================================
    // AUTO-DISMISS ALERTS
    // ============================================
    
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(function(alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    });

    // ============================================
    // GET CSRF TOKEN
    // ============================================
    
    function getCSRFToken() {
        const name = 'csrftoken';
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

    // ============================================
    // MARK ALL NOTIFICATIONS AS READ
    // ============================================
    
    function markAllNotificationsRead() {
        if (!confirm('Mark all notifications as read?')) return;
        
        const btn = document.querySelector('.dropdown-header .btn-link');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Loading...';
        }
        
        fetch('/api/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                lastNotificationCount = 0;
                updateNotificationBadge(0);
                clearNotificationList();
                showToast('✅ All notifications marked as read', 'success');
                console.log('✅ All notifications marked as read');
            }
        })
        .catch(error => console.error('Error marking notifications as read:', error))
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Mark all as read';
            }
        });
    }

    // ============================================
    // ADD NOTIFICATION TO LIST
    // ============================================
    
    function addNotificationToList(message, link, notificationId) {
        const list = document.getElementById('notificationList');
        if (!list) return;
        
        const emptyMsg = list.querySelector('.text-muted.text-center');
        if (emptyMsg) emptyMsg.remove();
        
        if (notificationId && list.querySelector(`[data-id="${notificationId}"]`)) {
            return;
        }
        
        const item = document.createElement('div');
        item.className = 'notification-item unread';
        item.dataset.id = notificationId || 'notif-' + Date.now();
        const time = new Date().toLocaleTimeString();
        
        let viewLink = link || '';
        if (viewLink && viewLink.includes('/pharmacy/order/')) {
            const patientId = viewLink.split('/')[3];
            viewLink = `/pharmacy/dispense-patient/${patientId}/`;
        }
        
        item.innerHTML = `
            <div class="d-flex justify-content-between">
                <span>${message}</span>
                <small class="time">just now</small>
            </div>
            ${viewLink ? `<a href="${viewLink}" class="small text-success">View</a>` : ''}
        `;
        list.prepend(item);
        
        while (list.children.length > 20) {
            list.removeChild(list.lastChild);
        }
        
        const badge = document.querySelector('.notification-count');
        if (badge) {
            let current = parseInt(badge.textContent) || 0;
            current += 1;
            badge.textContent = current;
            badge.style.display = current > 0 ? 'inline' : 'none';
            lastNotificationCount = current;
        }
    }

    function clearNotificationList() {
        const list = document.getElementById('notificationList');
        if (list) {
            list.innerHTML = '<div class="dropdown-item text-muted text-center">No notifications</div>';
        }
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('notificationToastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `notification-toast ${type}`;
        toast.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    <span>${message}</span>
                </div>
                <button type="button" class="btn-close btn-close-sm" onclick="this.closest('.notification-toast').remove()"></button>
            </div>
        `;
        container.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOut 0.5s ease';
                setTimeout(() => toast.remove(), 500);
            }
        }, 5000);
    }

    // ============================================
    // REFRESH NOTIFICATION BADGE
    // ============================================
    
    function refreshNotificationBadge() {
        console.log('🔄 Refreshing notification badge...');
        fetch('/api/notification-count/')
            .then(response => response.json())
            .then(data => {
                const count = data.count || 0;
                lastNotificationCount = count;
                updateNotificationBadge(count);
                console.log('🔔 Notification badge refreshed to:', count);
                
                // Also refresh the list
                refreshNotificationList();
                
                // Always check nurse assignments if nurse role
                if (isNurseUser) {
                    console.log('👩‍⚕️ Nurse: Checking assignments after badge refresh');
                    checkNurseAssignments();
                }
            })
            .catch(error => console.error('Error refreshing badge:', error));
    }

    // ============================================
    // NURSE ASSIGNMENT CHECK - FIXED (NO DUPLICATE TOASTS)
    // ============================================
    
    let lastAssignmentCheck = null;
    let hasCheckedAssignments = false;
    let isNurseUser = {% if role == 'NURSE' %}true{% else %}false{% endif %};
    let isMainDashboard = window.location.pathname === '/dashboard/' || window.location.pathname === '/dashboard' || window.location.pathname === '/';
    let assignmentCheckCount = 0;
    let knownAssignmentIds = new Set();
    let isInitialCheck = true;
    let initialCheckDone = false;
    let alertShown = false;

    function checkNurseAssignments() {
        // Only run for nurse users
        if (!isNurseUser) {
            return;
        }
        
        assignmentCheckCount++;
        console.log(`👩‍⚕️ Assignment check #${assignmentCheckCount} - Initial: ${isInitialCheck}, Done: ${initialCheckDone}`);
        
        // Build URL - always get ALL assignments
        let url = '/api/nurse/assignments/check/';
        
        console.log(`👩‍⚕️ Fetching: ${url}`);
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                console.log(`👩‍⚕️ Response count: ${data.count}`);
                
                let hasNewAssignments = false;
                let newAssignments = [];
                let allAssignmentIds = new Set();
                
                if (data.count > 0) {
                    data.assignments.forEach(assignment => {
                        allAssignmentIds.add(String(assignment.id));
                    });
                    
                    data.assignments.forEach(assignment => {
                        const idStr = String(assignment.id);
                        if (!knownAssignmentIds.has(idStr)) {
                            hasNewAssignments = true;
                            newAssignments.push(assignment);
                            knownAssignmentIds.add(idStr);
                            console.log(`👩‍⚕️ NEW assignment detected: ${assignment.patient_name} (ID: ${assignment.id})`);
                        }
                    });
                }
                
                // ===== Initial check - show ONCE =====
                if (isInitialCheck && data.count > 0 && !initialCheckDone) {
                    console.log(`👩‍⚕️ INITIAL CHECK (ONCE): Showing ${data.count} assignment(s)`);
                    
                    initialCheckDone = true;
                    isInitialCheck = false;
                    
                    if (knownAssignmentIds.size === data.count) {
                        const assignmentCount = data.count;
                        const patientNames = data.assignments.map(a => a.patient_name).join(', ');
                        const message = `You have ${assignmentCount} patient assignment(s): ${patientNames}`;
                        const link = '/nursing/dashboard/';
                        
                        addNotificationToList(message, link, 'initial-' + Date.now());
                        showToast(message, 'info');
                        playNotificationSound();
                        
                        fetch('/api/notification-count/')
                            .then(res => res.json())
                            .then(countData => {
                                const count = countData.count || 0;
                                lastNotificationCount = count;
                                updateNotificationBadge(count);
                                console.log(`🔔 Badge force updated to ${count}`);
                            })
                            .catch(err => console.error('Error updating badge:', err));
                        
                        refreshNotificationList();
                        
                        if (isMainDashboard) {
                            showNurseAssignmentAlert(data.assignments);
                        }
                    }
                    
                    hasCheckedAssignments = true;
                    return;
                }
                
                // ===== Handle NEW assignments after initial check =====
                if (hasNewAssignments && !isInitialCheck) {
                    console.log(`👩‍⚕️ ${newAssignments.length} NEW assignment(s) detected!`);
                    
                    newAssignments.forEach(assignment => {
                        const message = `You have been assigned to patient ${assignment.patient_name} (ID: ${assignment.hospital_number})`;
                        const link = `/nursing/assessment/${assignment.patient_id}/`;
                        
                        addNotificationToList(message, link, 'nurse-' + assignment.id);
                        showToast(message, 'info');
                        playNotificationSound();
                    });
                    
                    fetch('/api/notification-count/')
                        .then(res => res.json())
                        .then(countData => {
                            const count = countData.count || 0;
                            lastNotificationCount = count;
                            updateNotificationBadge(count);
                            console.log(`🔔 Badge force updated to ${count}`);
                        })
                        .catch(err => console.error('Error updating badge:', err));
                    
                    refreshNotificationList();
                    
                    if (isMainDashboard) {
                        showNurseAssignmentAlert(newAssignments);
                    }
                    
                    if (window.location.pathname.includes('/nursing/')) {
                        setTimeout(() => {
                            window.location.reload();
                        }, 3000);
                    }
                } else {
                    console.log('👩‍⚕️ No NEW assignments');
                    
                    if (knownAssignmentIds.size > 0) {
                        fetch('/api/notification-count/')
                            .then(res => res.json())
                            .then(countData => {
                                const count = countData.count || 0;
                                if (count > 0) {
                                    lastNotificationCount = count;
                                    updateNotificationBadge(count);
                                    console.log(`🔔 Badge updated to ${count} from known assignments`);
                                }
                            })
                            .catch(err => console.error('Error updating badge:', err));
                    }
                }
                
                if (!lastAssignmentCheck) {
                    lastAssignmentCheck = new Date().toISOString();
                    console.log(`👩‍⚕️ Initial last check set to: ${lastAssignmentCheck}`);
                }
                
                if (!initialCheckDone) {
                    initialCheckDone = true;
                    isInitialCheck = false;
                }
                
                hasCheckedAssignments = true;
            })
            .catch(error => console.error('Error checking nurse assignments:', error));
    }

    // ============================================
    // SHOW NURSE ASSIGNMENT ALERT
    // ============================================

    function showNurseAssignmentAlert(assignments) {
        if (alertShown) {
            console.log('👩‍⚕️ Alert already shown, skipping duplicate');
            return;
        }
        
        const existingAlert = document.getElementById('nurseAssignmentAlert');
        if (existingAlert) {
            console.log('👩‍⚕️ Alert already exists in DOM, skipping duplicate');
            return;
        }
        
        alertShown = true;
        
        const alertDiv = document.createElement('div');
        alertDiv.id = 'nurseAssignmentAlert';
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '70px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.maxWidth = '500px';
        alertDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        alertDiv.style.borderLeft = '4px solid #28a745';
        alertDiv.style.animation = 'slideIn 0.5s ease';
        
        let patientList = assignments.map(a => 
            `<li><strong>${a.patient_name}</strong> (${a.hospital_number})</li>`
        ).join('');
        
        alertDiv.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="flex-grow-1">
                    <h6 class="alert-heading mb-1">
                        <i class="fas fa-user-nurse me-2"></i>
                        New Patient Assignments!
                    </h6>
                    <p class="mb-1 small">You have been assigned ${assignments.length} new patient(s):</p>
                    <ul class="mb-1 small" style="padding-left: 20px;">
                        ${patientList}
                    </ul>
                    <a href="/nursing/dashboard/" class="btn btn-sm btn-success mt-1">
                        <i class="fas fa-arrow-right me-1"></i>Go to Nursing Dashboard
                    </a>
                    <button class="btn btn-sm btn-outline-secondary ms-1 mt-1" onclick="this.closest('.alert').remove(); alertShown = false;">
                        Dismiss
                    </button>
                </div>
                <button type="button" class="btn-close" onclick="this.closest('.alert').remove(); alertShown = false;"></button>
            </div>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.style.animation = 'slideOut 0.5s ease';
                setTimeout(() => {
                    alertDiv.remove();
                    alertShown = false;
                }, 500);
            }
        }, 30000);
    }

    // ============================================
    // PHARMACY NOTIFICATION CHECK
    // ============================================
    
    let isPharmacyUser = {% if role == 'PHARMACY' %}true{% else %}false{% endif %};
    let lastPharmacyCheck = null;
    let pharmacyCheckCount = 0;

    function checkPharmacyNotifications() {
        if (!isPharmacyUser) {
            return;
        }
        
        pharmacyCheckCount++;
        console.log(`💊 Pharmacy check #${pharmacyCheckCount}`);
        
        fetch('/api/pharmacy/notification-check/')
            .then(response => response.json())
            .then(data => {
                console.log(`💊 Pharmacy check result: ${data.recent_count} new, ${data.count} total`);
                
                if (data.has_new && data.recent_count > 0) {
                    console.log(`💊 ${data.recent_count} new prescription(s) detected!`);
                    
                    // Show toast notification
                    const message = `💊 ${data.recent_count} new prescription(s) waiting for dispensing`;
                    showToast(message, 'info');
                    
                    // Play sound
                    playNotificationSound();
                    
                    // Update the badge
                    const badge = document.querySelector('.notification-count');
                    if (badge) {
                        let current = parseInt(badge.textContent) || 0;
                        current += data.recent_count;
                        badge.textContent = current;
                        badge.style.display = current > 0 ? 'inline' : 'none';
                        lastNotificationCount = current;
                    }
                    
                    // Refresh the notification list
                    refreshNotificationList();
                    
                    // Update pharmacy badge
                    updatePharmacyBadge(data.count);
                }
                
                lastPharmacyCheck = new Date().toISOString();
            })
            .catch(error => console.error('Error checking pharmacy notifications:', error));
    }

    // ============================================
    // PHARMACY BADGE UPDATE
    // ============================================
    
    function updatePharmacyBadge(count) {
        const dispensaryBadge = document.getElementById('dispensaryBadge');
        if (dispensaryBadge) {
            dispensaryBadge.textContent = count;
            dispensaryBadge.style.display = count > 0 ? 'inline' : 'none';
        }
        
        const mobilePharmacyBadge = document.getElementById('mobilePharmacyBadge');
        if (mobilePharmacyBadge) {
            mobilePharmacyBadge.textContent = count;
            mobilePharmacyBadge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    // ============================================
    // HARD RESET NOTIFICATIONS
    // ============================================
    
    function hardResetNotifications() {
        console.log('💥 Hard resetting notifications...');
        knownAssignmentIds = new Set();
        isInitialCheck = true;
        initialCheckDone = false;
        alertShown = false;
        lastAssignmentCheck = null;
        
        fetch('/api/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                lastNotificationCount = 0;
                updateNotificationBadge(0);
                clearNotificationList();
                showToast('✅ Notifications reset successfully!', 'success');
                console.log('✅ Hard reset successful!');
                setTimeout(checkNurseAssignments, 500);
            }
        })
        .catch(error => console.error('Error in hard reset:', error));
    }

    // ============================================
    // REAL-TIME NOTIFICATION SYSTEM (POLLING ONLY)
    // ============================================
    
    let lastNotificationCount = {{ notification_count|default:0 }};
    let notificationPollingInterval = null;
    let isNotificationPolling = false;
    let hasInitialized = false;
    let notificationSoundEnabled = true;
    let notificationCheckCounter = 0;
    
    function initializeNotificationSystem() {
        if (hasInitialized) return;
        hasInitialized = true;
        
        console.log('🔔 Initializing notification system...');
        console.log('🔔 Initial count from server:', lastNotificationCount);
        console.log('👩‍⚕️ Is nurse user:', isNurseUser);
        console.log('💊 Is pharmacy user:', isPharmacyUser);
        console.log('📍 Is main dashboard:', isMainDashboard);
        
        fetch('/api/notification-count/')
            .then(response => response.json())
            .then(data => {
                const count = data.count || 0;
                lastNotificationCount = count;
                updateNotificationBadge(count);
                console.log('🔔 Badge initialized to:', count);
            })
            .catch(error => console.error('Error getting initial notification count:', error));
        
        if (isNurseUser) {
            setTimeout(function() {
                console.log('👩‍⚕️ Initial nurse assignment check...');
                isInitialCheck = true;
                initialCheckDone = false;
                alertShown = false;
                lastAssignmentCheck = new Date().toISOString();
                checkNurseAssignments();
            }, 1000);
        }
        
        if (isPharmacyUser) {
            setTimeout(function() {
                console.log('💊 Initial pharmacy check...');
                checkPharmacyNotifications();
            }, 1500);
        }
        
        // Start polling after 2 seconds
        setTimeout(function() {
            startNotificationPolling();
        }, 2000);
    }
    
    function startNotificationPolling() {
        if (notificationPollingInterval) {
            clearInterval(notificationPollingInterval);
        }
        
        notificationPollingInterval = setInterval(function() {
            checkForNewNotifications();
        }, 3000);
        
        console.log('📡 Notification polling started (every 3 seconds)');
    }
    
    function checkForNewNotifications() {
        if (isNotificationPolling) return;
        isNotificationPolling = true;
        notificationCheckCounter++;
        
        fetch('/api/notification-count/')
            .then(response => response.json())
            .then(data => {
                const currentCount = data.count || 0;
                console.log(`📊 Poll ${notificationCheckCounter}: Current: ${currentCount}, Last: ${lastNotificationCount}`);
                
                updateNotificationBadge(currentCount);
                
                if (currentCount > lastNotificationCount) {
                    const newCount = currentCount - lastNotificationCount;
                    console.log(`🔔 ${newCount} NEW notification(s) detected!`);
                    
                    fetch('/api/notifications/latest/')
                        .then(response => response.json())
                        .then(notifData => {
                            if (notifData.notifications && notifData.notifications.length > 0) {
                                const unread = notifData.notifications.filter(n => !n.is_read);
                                if (unread.length > 0) {
                                    const list = document.getElementById('notificationList');
                                    if (list) {
                                        const emptyMsg = list.querySelector('.text-muted.text-center');
                                        if (emptyMsg) emptyMsg.remove();
                                    }
                                    
                                    const latestUnread = unread.slice(0, newCount);
                                    latestUnread.forEach(notif => {
                                        const list = document.getElementById('notificationList');
                                        const existing = list ? list.querySelector(`[data-id="${notif.id}"]`) : null;
                                        if (!existing) {
                                            showNotificationToast(notif.message, notif.link);
                                            addNotificationToList(notif.message, notif.link, notif.id);
                                            if (notificationSoundEnabled) {
                                                playNotificationSound();
                                            }
                                        }
                                    });
                                }
                            }
                            lastNotificationCount = currentCount;
                            console.log('📊 Last count updated to:', lastNotificationCount);
                        })
                        .catch(error => console.error('Error fetching notifications:', error));
                        
                } else if (currentCount < lastNotificationCount) {
                    console.log(`📉 Count decreased: ${lastNotificationCount} → ${currentCount}`);
                    lastNotificationCount = currentCount;
                    refreshNotificationList();
                } else {
                    console.log('✅ No new notifications');
                }
                
                // ===== Check nurse assignments =====
                if (isNurseUser) {
                    const checkFrequency = isMainDashboard ? 1 : 2;
                    if (notificationCheckCounter % checkFrequency === 0) {
                        checkNurseAssignments();
                    }
                }
                
                // ===== Check pharmacy notifications =====
                if (isPharmacyUser) {
                    if (notificationCheckCounter % 2 === 0) {
                        checkPharmacyNotifications();
                    }
                }
                
                isNotificationPolling = false;
            })
            .catch(error => {
                console.error('Error checking notification count:', error);
                isNotificationPolling = false;
            });
    }
    
    // ============================================
    // REFRESH NOTIFICATION LIST
    // ============================================
    
    function refreshNotificationList() {
        console.log('🔄 Refreshing notification list...');
        fetch('/api/notifications/latest/')
            .then(response => response.json())
            .then(notifData => {
                const list = document.getElementById('notificationList');
                if (!list) return;
                
                list.innerHTML = '';
                
                if (notifData.notifications && notifData.notifications.length > 0) {
                    const unread = notifData.notifications.filter(n => !n.is_read);
                    if (unread.length === 0) {
                        list.innerHTML = '<div class="dropdown-item text-muted text-center">No notifications</div>';
                    } else {
                        unread.forEach(notif => {
                            const item = document.createElement('div');
                            item.className = 'notification-item unread';
                            item.dataset.id = notif.id;
                            const time = new Date(notif.created_at).toLocaleTimeString();
                            
                            let viewLink = notif.link || '';
                            if (viewLink && viewLink.includes('/pharmacy/order/')) {
                                const patientId = viewLink.split('/')[3];
                                viewLink = `/pharmacy/dispense-patient/${patientId}/`;
                            }
                            
                            item.innerHTML = `
                                <div class="d-flex justify-content-between">
                                    <span>${notif.message}</span>
                                    <small class="time">${time}</small>
                                </div>
                                ${viewLink ? `<a href="${viewLink}" class="small text-success">View</a>` : ''}
                            `;
                            list.appendChild(item);
                        });
                    }
                } else {
                    list.innerHTML = '<div class="dropdown-item text-muted text-center">No notifications</div>';
                }
                
                console.log('✅ Notification list refreshed');
            })
            .catch(error => console.error('Error refreshing notification list:', error));
    }
    
    // ============================================
    // NOTIFICATION UI FUNCTIONS
    // ============================================
    
    function updateNotificationBadge(count) {
        const badge = document.querySelector('.notification-count');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
            console.log('🔔 Badge updated to:', count);
        }
    }
    
    function playNotificationSound() {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
            
            oscillator.start(audioCtx.currentTime);
            oscillator.stop(audioCtx.currentTime + 0.3);
        } catch (e) {
            // Silently fail if audio not supported
        }
    }
    
    function showNotificationToast(message, link, type = 'info') {
        const container = document.getElementById('notificationToastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `notification-toast ${type}`;
        toast.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <i class="fas fa-bell text-info me-2"></i>
                    <span>${message}</span>
                    ${link ? `<br><a href="${link}" class="toast-link mt-1 d-inline-block" onclick="this.closest('.notification-toast').remove()">View Details →</a>` : ''}
                </div>
                <button type="button" class="btn-close btn-close-sm" onclick="this.closest('.notification-toast').remove()"></button>
            </div>
        `;
        container.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOut 0.5s ease';
                setTimeout(() => toast.remove(), 500);
            }
        }, 8000);
    }

    // ============================================
    // EXPOSE FUNCTIONS GLOBALLY
    // ============================================
    
    window.hardResetNotifications = hardResetNotifications;
    window.markAllNotificationsRead = markAllNotificationsRead;
    window.refreshNotificationBadge = refreshNotificationBadge;
    window.refreshNotificationList = refreshNotificationList;
    window.filterDoctorPatients = filterDoctorPatients;
    window.toggleDoctorPatientSidebar = toggleDoctorPatientSidebar;
    window.checkNurseAssignments = checkNurseAssignments;
    window.checkPharmacyNotifications = checkPharmacyNotifications;
    window.toggleNotificationSound = function() {
        notificationSoundEnabled = !notificationSoundEnabled;
        console.log('🔊 Notification sound:', notificationSoundEnabled ? 'ON' : 'OFF');
        return notificationSoundEnabled;
    };

    // ============================================
    // INITIALIZE
    // ============================================
    
    document.addEventListener('DOMContentLoaded', function() {
        {% if user.is_authenticated %}
            console.log('🔔 User authenticated, initializing notification system');
            console.log('👤 User role: {{ role }}');
            console.log('👩‍⚕️ Is nurse user (JS):', isNurseUser);
            console.log('💊 Is pharmacy user (JS):', isPharmacyUser);
            console.log('📍 Is main dashboard:', isMainDashboard);
            
            initializeNotificationSystem();
            
            console.log('🔌 WebSocket disabled - using polling only');
            
            if (isNurseUser) {
                console.log('👩‍⚕️ Nurse role detected - checking assignments immediately');
                isInitialCheck = true;
                initialCheckDone = false;
                alertShown = false;
                setTimeout(function() {
                    lastAssignmentCheck = new Date().toISOString();
                    checkNurseAssignments();
                }, 500);
                
                if (isMainDashboard) {
                    setInterval(function() {
                        console.log('👩‍⚕️ Periodic nurse assignment check (main dashboard fallback)');
                        checkNurseAssignments();
                    }, 5000);
                }
            }
            
            if (isPharmacyUser) {
                console.log('💊 Pharmacy role detected - checking prescriptions immediately');
                setTimeout(function() {
                    checkPharmacyNotifications();
                }, 800);
            }
            
            console.log('='.repeat(60));
            console.log('🔍 AVAILABLE COMMANDS:');
            console.log('  hardResetNotifications() - Force reset all notifications');
            console.log('  refreshNotificationBadge() - Refresh the notification badge');
            console.log('  refreshNotificationList() - Refresh the notification list');
            console.log('  markAllNotificationsRead() - Mark all as read');
            console.log('  checkNurseAssignments() - Manually check for nurse assignments');
            console.log('  checkPharmacyNotifications() - Manually check for pharmacy prescriptions');
            console.log('='.repeat(60));
        {% endif %}
    });
</script>

can you fully completely updated 
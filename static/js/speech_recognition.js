// static/js/speech_recognition.js

class SpeechRecognitionManager {
    constructor() {
        this.isRecording = false;
        this.currentTarget = null;
        this.recognition = null;
        this.transcript = '';
        this.finalTranscript = '';
        this.availableCommands = {
            'diagnosis': ['start diagnosis', 'begin diagnosis', 'diagnose'],
            'allergy': ['add allergy', 'record allergy', 'patient allergy'],
            'prescription': ['write prescription', 'prescribe', 'medication'],
            'notes': ['clinical notes', 'doctor notes', 'patient notes'],
            'treatment': ['treatment plan', 'plan treatment', 'treatment'],
            'stop': ['stop recording', 'end recording', 'finish recording'],
            'clear': ['clear transcript', 'erase transcript'],
            'save': ['save draft', 'save consultation']
        };
        
        this.initializeRecognition();
        this.bindEvents();
    }
    
    initializeRecognition() {
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
        } else if ('SpeechRecognition' in window) {
            this.recognition = new SpeechRecognition();
        } else {
            this.showError('Speech recognition not supported in this browser');
            return;
        }
        
        // Configure recognition
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = document.getElementById('languageSelect').value;
        this.recognition.maxAlternatives = 1;
        
        // Event handlers
        this.recognition.onstart = () => this.onRecognitionStart();
        this.recognition.onresult = (event) => this.onRecognitionResult(event);
        this.recognition.onerror = (event) => this.onRecognitionError(event);
        this.recognition.onend = () => this.onRecognitionEnd();
    }
    
    bindEvents() {
        // Microphone button
        document.getElementById('micButton').addEventListener('click', () => {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        });
        
        // Language selector
        document.getElementById('languageSelect').addEventListener('change', (e) => {
            if (this.recognition) {
                this.recognition.lang = e.target.value;
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+Shift+M to toggle recording
            if (e.ctrlKey && e.shiftKey && e.key === 'M') {
                e.preventDefault();
                document.getElementById('micButton').click();
            }
            
            // Ctrl+Shift+S to save draft
            if (e.ctrlKey && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                saveConsultation(false);
            }
        });
    }
    
    startRecording() {
        if (!this.recognition) {
            this.initializeRecognition();
        }
        
        try {
            this.recognition.start();
            this.isRecording = true;
            this.updateUI();
            this.showTranscript();
        } catch (error) {
            console.error('Error starting recognition:', error);
            this.showError('Cannot start voice recognition. Please check microphone permissions.');
        }
    }
    
    stopRecording() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
            this.isRecording = false;
            this.updateUI();
        }
    }
    
    onRecognitionStart() {
        this.updateStatus('active', 'Listening...');
        this.showNotification('🎤 Voice recognition started. Speak now.', 'info');
    }
    
    onRecognitionResult(event) {
        this.transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                this.finalTranscript += transcript + ' ';
                this.processFinalTranscript(transcript);
            } else {
                this.transcript += transcript;
            }
        }
        
        this.updateTranscript();
        this.processCommands(this.transcript);
    }
    
    onRecognitionError(event) {
        console.error('Speech recognition error:', event.error);
        
        switch(event.error) {
            case 'no-speech':
                this.showNotification('No speech detected. Please speak louder.', 'warning');
                break;
            case 'audio-capture':
                this.showError('No microphone found. Please check your microphone.');
                break;
            case 'not-allowed':
                this.showError('Microphone access denied. Please allow microphone access.');
                break;
            default:
                this.showError(`Speech recognition error: ${event.error}`);
        }
        
        this.stopRecording();
    }
    
    onRecognitionEnd() {
        this.isRecording = false;
        this.updateUI();
        this.updateStatus('inactive', 'Ready');
        
        if (this.finalTranscript.trim()) {
            this.showInsertButtons();
        }
    }
    
    processFinalTranscript(transcript) {
        // Add to current target if specified
        if (this.currentTarget) {
            this.insertToField(this.currentTarget, transcript);
        }
        
        // Log for debugging
        console.log('Final transcript:', transcript);
    }
    
    processCommands(transcript) {
        const lowerTranscript = transcript.toLowerCase().trim();
        
        // Check for command phrases
        for (const [command, phrases] of Object.entries(this.availableCommands)) {
            for (const phrase of phrases) {
                if (lowerTranscript.includes(phrase)) {
                    this.executeCommand(command);
                    return;
                }
            }
        }
    }
    
    executeCommand(command) {
        switch(command) {
            case 'diagnosis':
                this.setTarget('diagnosis', '🎯 Now recording for Diagnosis');
                break;
            case 'allergy':
                this.setTarget('allergy', '🎯 Now recording for Allergy');
                break;
            case 'prescription':
                this.setTarget('prescription', '🎯 Now recording for Prescription');
                break;
            case 'notes':
                this.setTarget('clinical_notes', '🎯 Now recording for Clinical Notes');
                break;
            case 'treatment':
                this.setTarget('treatment_plan', '🎯 Now recording for Treatment Plan');
                break;
            case 'stop':
                this.stopRecording();
                this.showNotification('🛑 Recording stopped', 'info');
                break;
            case 'clear':
                this.clearTranscript();
                break;
            case 'save':
                saveConsultation(false);
                break;
        }
    }
    
    setTarget(targetId, message) {
        this.currentTarget = targetId;
        this.showNotification(message, 'success');
        
        // Highlight the target field
        const field = document.getElementById(targetId);
        if (field) {
            field.focus();
            field.style.border = '2px solid #4CAF50';
            setTimeout(() => {
                field.style.border = '';
            }, 2000);
        }
    }
    
    insertToField(fieldId, text) {
        const field = document.getElementById(fieldId);
        if (field) {
            const currentText = field.value;
            field.value = currentText + (currentText ? '\n' : '') + text;
            
            // Trigger any change events
            field.dispatchEvent(new Event('input', { bubbles: true }));
            field.dispatchEvent(new Event('change', { bubbles: true }));
            
            this.showNotification(`✓ Text added to ${fieldId.replace('_', ' ')}`, 'success');
        }
    }
    
    updateUI() {
        const micBtn = document.getElementById('micButton');
        const micIcon = micBtn.querySelector('i');
        
        if (this.isRecording) {
            micBtn.classList.add('recording');
            micIcon.className = 'fas fa-microphone-slash';
            micBtn.title = 'Click to stop recording';
        } else {
            micBtn.classList.remove('recording');
            micIcon.className = 'fas fa-microphone';
            micBtn.title = 'Click to start recording';
        }
    }
    
    updateStatus(status, text) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        indicator.className = 'status-indicator';
        if (status === 'active') {
            indicator.classList.add('active');
        }
        
        statusText.textContent = text;
    }
    
    updateTranscript() {
        const transcriptText = document.getElementById('transcriptText');
        if (transcriptText) {
            const displayText = this.finalTranscript + 
                              (this.transcript ? `<span class="text-muted">${this.transcript}</span>` : '');
            transcriptText.innerHTML = displayText;
            
            // Auto-scroll to bottom
            transcriptText.scrollTop = transcriptText.scrollHeight;
        }
    }
    
    showTranscript() {
        const transcriptBox = document.getElementById('transcriptBox');
        transcriptBox.style.display = 'block';
    }
    
    hideTranscript() {
        const transcriptBox = document.getElementById('transcriptBox');
        transcriptBox.style.display = 'none';
    }
    
    showInsertButtons() {
        const insertButtons = document.getElementById('insertButtons');
        insertButtons.style.display = 'flex';
    }
    
    hideInsertButtons() {
        const insertButtons = document.getElementById('insertButtons');
        insertButtons.style.display = 'none';
    }
    
    clearTranscript() {
        this.transcript = '';
        this.finalTranscript = '';
        this.updateTranscript();
        this.hideInsertButtons();
        this.showNotification('Transcript cleared', 'info');
    }
    
    insertToDiagnosis() {
        if (this.finalTranscript.trim()) {
            const diagnosisField = document.getElementById('diagnosis');
            if (diagnosisField) {
                this.insertToField('diagnosis', this.finalTranscript);
                this.clearTranscript();
            }
        }
    }
    
    insertToAllergy() {
        if (this.finalTranscript.trim()) {
            const allergyField = document.getElementById('allergy');
            if (allergyField) {
                this.insertToField('allergy', this.finalTranscript);
                this.clearTranscript();
            }
        }
    }
    
    insertToPrescription() {
        if (this.finalTranscript.trim()) {
            const prescriptionField = document.getElementById('prescription');
            if (prescriptionField) {
                this.insertToField('prescription', this.finalTranscript);
                this.clearTranscript();
            }
        }
    }
    
    insertToClinicalNotes() {
        if (this.finalTranscript.trim()) {
            const notesField = document.getElementById('clinical_notes');
            if (notesField) {
                this.insertToField('clinical_notes', this.finalTranscript);
                this.clearTranscript();
            }
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            max-width: 400px;
            animation: slideIn 0.3s ease;
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    showError(message) {
        this.showNotification(`❌ ${message}`, 'error');
    }
    
    showCommands() {
        document.getElementById('commandsOverlay').style.display = 'flex';
    }
    
    hideCommands() {
        document.getElementById('commandsOverlay').style.display = 'none';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.speechManager = new SpeechRecognitionManager();
    
    // Add CSS for slide-in animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
});
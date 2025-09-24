/**
 * TLS Visa Monitor Dashboard JavaScript
 * Handles all frontend interactions and real-time updates
 */

class TLSMonitorDashboard {
    constructor() {
        this.socket = null;
        this.isMonitoring = false;
        this.autoScroll = true;
        this.nextCheckTimer = null;
        this.lastTotalChecks = 0;
        this.lastErrorCount = 0;
        
        this.init();
    }
    
    init() {
        console.log('TLS Monitor Dashboard initializing...');
        console.log('Current environment:', window.location.hostname);
        
        this.setupSocketConnection();
        this.setupEventListeners();
        this.loadConfiguration();
        this.updateStatus();
        
        // Initialize interface
        this.showToast('System ready', 'info');
        this.addLogEntry('info', 'Dashboard initialized successfully');
        
        // Add debugging info
        console.log('Dashboard initialization complete');
        console.log('Socket.IO available:', typeof io !== 'undefined');
        console.log('Environment detection:', window.location.protocol, window.location.hostname);
    }
    
    setupSocketConnection() {
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            timeout: 5000,
            forceNew: true,
            transports: ['polling', 'websocket']
        });
        
        this.socket.on('connect', () => {
            console.log('Socket.IO connected successfully');
            this.addLogEntry('info', 'Socket.IO connection established');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Socket.IO disconnected:', reason);
            this.addLogEntry('warning', `Socket.IO disconnected: ${reason}`);
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
            this.addLogEntry('error', `Socket.IO connection error: ${error.message}`);
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log('Socket.IO reconnected after', attemptNumber, 'attempts');
            this.addLogEntry('info', `Socket.IO reconnected (attempt ${attemptNumber})`);
        });
        
        this.socket.on('reconnect_error', (error) => {
            console.error('Socket.IO reconnection failed:', error);
            this.addLogEntry('error', `Socket.IO reconnection failed: ${error.message}`);
        });
        
        // Socket.IO event listeners for monitoring
        this.socket.on('log_message', (data) => {
            // Only show important messages to the user
            if (this.shouldShowLogMessage(data.message, data.level)) {
                this.addLogEntry(data.level, data.message, data.timestamp);
            }
        });
        
        this.socket.on('status_update', (data) => {
            // Debug: Always log status updates for debugging
            console.log('Received status_update event:', data);
            this.updateMonitoringStatus(data);
            this.updateConnectionStatus(true); // Update connection when receiving events
        });
        
        // Fallback status polling when Socket.IO is unreliable
        setInterval(() => {
            if (!this.socket.connected) {
                console.log('Socket disconnected, polling status manually...');
                this.updateStatus();
            }
        }, 5000); // Check every 5 seconds if disconnected
        
        this.socket.on('slots_found', (data) => {
            this.handleSlotsFound(data);
        });
        
        this.socket.on('monitoring_error', (data) => {
            this.handleMonitoringError(data);
        });
        
        this.socket.on('monitoring_failed', (data) => {
            console.log('monitoring_failed event received:', data);
            this.handleMonitoringFailed(data);
        });
        
        // Handle connection issues
        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
            this.addLogEntry('error', `Socket.IO connection error: ${error.message}`);
            // Show fallback notification for connection issues
            this.showPopupNotification({
                type: 'warning',
                title: 'Connection Issue',
                message: 'Lost connection to server. Some notifications may not appear. Please refresh if issues persist.',
                duration: 10000
            });
        });
        
        // New event handlers for enhanced notifications
        this.socket.on('show_popup_notification', (data) => {
            this.showPopupNotification(data);
        });
        
        this.socket.on('check_started', (data) => {
            this.addLogEntry('info', `🔍 Check #${data.check_number} started at ${new Date(data.timestamp).toLocaleTimeString()}`);
        });
        
        this.socket.on('check_completed', (data) => {
            const duration = data.duration.toFixed(1);
            if (data.slots_found > 0) {
                this.addLogEntry('warning', `✅ Check #${data.check_number} completed in ${duration}s - ${data.slots_found} SLOTS FOUND!`);
            } else {
                this.addLogEntry('info', `✅ Check #${data.check_number} completed in ${duration}s - No slots found`);
            }
        });
    }
    
    setupEventListeners() {
        // Ensure DOM is ready and elements exist before adding listeners
        const waitForElement = (selector, callback) => {
            const element = document.getElementById(selector);
            if (element) {
                callback(element);
            } else {
                console.warn(`Element ${selector} not found, retrying...`);
                setTimeout(() => waitForElement(selector, callback), 100);
            }
        };

        // Configuration buttons
        waitForElement('save-config-btn', (el) => {
            el.addEventListener('click', () => this.saveConfiguration());
        });
        
        waitForElement('test-notifications-btn', (el) => {
            el.addEventListener('click', () => this.testNotifications());
        });
        
        // Email notifications toggle
        waitForElement('email-notifications', (el) => {
            el.addEventListener('change', (e) => {
                const emailConfig = document.getElementById('email-config');
                if (emailConfig) {
                    emailConfig.style.display = e.target.checked ? 'block' : 'none';
                }
            });
        });
        
        // Monitoring controls
        waitForElement('start-monitoring-btn', (el) => {
            el.addEventListener('click', () => this.startMonitoring());
        });
        
        waitForElement('stop-monitoring-btn', (el) => {
            el.addEventListener('click', () => this.stopMonitoring());
        });
        
        // Logs controls
        waitForElement('clear-logs-btn', (el) => {
            el.addEventListener('click', () => this.clearLogs());
        });
        
        waitForElement('auto-scroll-btn', (el) => {
            el.addEventListener('click', () => this.toggleAutoScroll());
        });
        
        // Toast notification
        waitForElement('toast-close', (el) => {
            el.addEventListener('click', () => this.hideToast());
        });
        
        // Popup notification
        waitForElement('popup-close', (el) => {
            el.addEventListener('click', () => this.hidePopupNotification());
        });
        
        // Modal controls
        waitForElement('slots-modal-close', (el) => {
            el.addEventListener('click', () => this.hideModal('slots-modal'));
        });
        
        // Click outside modal to close
        waitForElement('slots-modal', (el) => {
            el.addEventListener('click', (e) => {
                if (e.target.id === 'slots-modal') {
                    this.hideModal('slots-modal');
                }
            });
        });
    }
    
    async loadConfiguration() {
        try {
            const response = await fetch('/api/config');
            const result = await response.json();
            
            if (result.success) {
                this.populateConfigurationForm(result.config);
            } else {
                this.showToast('Failed to load configuration', 'error');
            }
        } catch (error) {
            this.showToast('Error loading configuration', 'error');
            console.error('Load config error:', error);
        }
    }
    
    populateConfigurationForm(config) {
        // Helper function to safely set element values
        const safeSetValue = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.value = value || '';
            } else {
                console.warn(`Element ${id} not found when setting value`);
            }
        };

        const safeSetChecked = (id, checked) => {
            const element = document.getElementById(id);
            if (element) {
                element.checked = Boolean(checked);
            } else {
                console.warn(`Element ${id} not found when setting checked state`);
            }
        };

        // TLS Credentials
        safeSetValue('tls-email', config.login_credentials?.email);
        safeSetValue('tls-password', config.login_credentials?.password);
        
        // Monitoring Settings
        safeSetValue('check-interval', config.check_interval_minutes || 15);
        safeSetValue('months-to-check', config.months_to_check || 3);
        
        // Notification Settings
        safeSetChecked('desktop-notifications', config.notification?.desktop?.enabled);
        safeSetChecked('email-notifications', config.notification?.email?.enabled);
        
        // Browser Settings - handle forced headless mode
        const headlessCheckbox = document.getElementById('headless-mode');
        if (headlessCheckbox) {
            safeSetChecked('headless-mode', config.headless_mode !== false); // Default to true
            
            // Force headless mode in cloud environments
            if (config.force_headless) {
                headlessCheckbox.checked = true;
                headlessCheckbox.disabled = true;
                
                // Add visual indicator and explanation
                const headlessLabel = headlessCheckbox.closest('.checkbox-label');
                if (headlessLabel) {
                    headlessLabel.title = 'Headless mode is required in cloud deployment environments';
                    headlessLabel.style.opacity = '0.7';
                    
                    // Add cloud indicator
                    let cloudIndicator = headlessLabel.querySelector('.cloud-indicator');
                    if (!cloudIndicator) {
                        cloudIndicator = document.createElement('span');
                        cloudIndicator.className = 'cloud-indicator';
                        cloudIndicator.innerHTML = ' <i class="fas fa-cloud" style="color: #3b82f6; margin-left: 5px;" title="Required for cloud deployment"></i>';
                        headlessLabel.appendChild(cloudIndicator);
                    }
                }
                
                // Update the config note
                const configNote = headlessCheckbox.closest('.config-group').querySelector('.config-note');
                if (configNote && config.environment === 'cloud') {
                    configNote.innerHTML = `
                        <i class="fas fa-cloud"></i>
                        <strong>Cloud Deployment:</strong> Headless mode is required and automatically enabled. 
                        The browser runs invisibly in the background on the server.
                    `;
                    configNote.style.color = '#3b82f6';
                }
            }
        }
        
        // Email Configuration
        if (config.notification?.email) {
            safeSetValue('receiver-email', config.notification.email.receiver_email);
        }
        
        // Show/hide email config
        const emailConfig = document.getElementById('email-config');
        const emailNotifications = document.getElementById('email-notifications');
        if (emailConfig && emailNotifications) {
            emailConfig.style.display = emailNotifications.checked ? 'block' : 'none';
        }
    }
    
    async saveConfiguration() {
        // Helper function to safely get element values
        const safeGetValue = (id, defaultValue = '') => {
            const element = document.getElementById(id);
            return element ? element.value : defaultValue;
        };

        const safeGetChecked = (id, defaultValue = false) => {
            const element = document.getElementById(id);
            return element ? element.checked : defaultValue;
        };

        const config = {
            login_credentials: {
                email: safeGetValue('tls-email'),
                password: safeGetValue('tls-password')
            },
            check_interval_minutes: parseInt(safeGetValue('check-interval', '15')),
            months_to_check: parseInt(safeGetValue('months-to-check', '3')),
            notification: {
                desktop: {
                    enabled: safeGetChecked('desktop-notifications')
                },
                email: {
                    enabled: safeGetChecked('email-notifications'),
                    receiver_email: safeGetValue('receiver-email')
                }
            },
            headless_mode: safeGetChecked('headless-mode', true)
        };
        
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Configuration saved successfully', 'success');
                this.addLogEntry('info', 'Configuration updated');
            } else {
                this.showToast(`Failed to save configuration: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showToast('Error saving configuration', 'error');
            console.error('Save config error:', error);
        } finally {
            this.showLoading(false);
        }
    }
    
    async testNotifications() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/test-notifications', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ type: 'both' })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Test notification sent successfully', 'success');
                this.addLogEntry('info', 'Test notification sent');
            } else {
                this.showToast(`Failed to send test notification: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showToast('Error sending test notification', 'error');
            console.error('Test notification error:', error);
        } finally {
            this.showLoading(false);
        }
    }
    
    async startMonitoring() {
        try {
            // Debounce: if already monitoring or a start request in-flight, ignore
            if (this.isMonitoring) {
                this.showToast('Monitoring already running', 'warning');
                return;
            }
            if (this._startingRequest) {
                this.showToast('Start request already in progress...', 'info');
                return;
            }
            this._startingRequest = true;
            const startBtn = document.getElementById('start-monitoring-btn');
            if (startBtn) {
                startBtn.disabled = true;
                startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
            }
            // Validate TLS credentials before starting
            const tlsEmail = document.getElementById('tls-email').value.trim();
            const tlsPassword = document.getElementById('tls-password').value.trim();
            
            if (!tlsEmail || !tlsPassword) {
                this.showToast('Please enter your TLS email and password before starting monitoring', 'error');
                this.addLogEntry('error', 'Cannot start monitoring: TLS credentials are required');
                
                // Focus on the first empty field
                if (!tlsEmail) {
                    document.getElementById('tls-email').focus();
                } else {
                    document.getElementById('tls-password').focus();
                }
                return;
            }
            
            // Save configuration first to ensure credentials are stored
            await this.saveConfiguration();
            
            this.showLoading(true);
            
            const response = await fetch('/api/start-monitoring', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.isMonitoring = true;
                this.updateMonitoringButtons();
                this.showToast('Monitoring started successfully', 'success');
                this.addLogEntry('info', `Monitoring started for TLS account: ${tlsEmail}`);
                
                // Immediately start a test countdown for 15 minutes
                const testNextCheck = Date.now() + (15 * 60 * 1000); // 15 minutes from now
                this.updateNextCheckCountdown(testNextCheck);
            } else {
                this.showToast(`Failed to start monitoring: ${result.error}`, 'error');
                this.addLogEntry('error', `Failed to start monitoring: ${result.error}`);
            }
        } catch (error) {
            this.showToast('Error starting monitoring', 'error');
            this.addLogEntry('error', `Start monitoring error: ${error.message}`);
            console.error('Start monitoring error:', error);
        } finally {
            this.showLoading(false);
            // Restore start button state if monitoring failed
            if (!this.isMonitoring) {
                const btn = document.getElementById('start-monitoring-btn');
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-play"></i> Start Monitoring';
                }
            }
            this._startingRequest = false;
        }
    }
    
    async stopMonitoring() {
        try {
            this.showLoading(true);
            this.addLogEntry('info', '🛑 Stopping monitoring...');
            
            // Disable stop button to prevent multiple clicks
            const stopBtn = document.getElementById('stop-monitoring-btn');
            if (stopBtn) {
                stopBtn.disabled = true;
                stopBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Stopping...';
            }
            
            const response = await fetch('/api/stop-monitoring', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.isMonitoring = false;
                this.updateMonitoringButtons();
                this.showToast('Monitoring stopped successfully', 'success');
                this.addLogEntry('success', '✅ Monitoring stopped successfully');
                
                // Stop countdown timer
                document.getElementById('countdown-display').textContent = '--:--:--';
                if (this.nextCheckTimer) {
                    clearInterval(this.nextCheckTimer);
                    this.nextCheckTimer = null;
                    console.log('Countdown timer cleared - monitoring manually stopped');
                }
            } else {
                this.showToast(`Failed to stop monitoring: ${result.error}`, 'error');
                this.addLogEntry('error', `❌ Failed to stop monitoring: ${result.error}`);
            }
        } catch (error) {
            this.showToast('Error stopping monitoring', 'error');
            this.addLogEntry('error', `❌ Error stopping monitoring: ${error.message}`);
            console.error('Stop monitoring error:', error);
        } finally {
            this.showLoading(false);
            // Re-enable stop button if it still exists
            const stopBtn = document.getElementById('stop-monitoring-btn');
            if (stopBtn) {
                stopBtn.disabled = false;
                stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Monitoring';
            }
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const result = await response.json();
            
            if (result.success) {
                this.updateMonitoringStatus(result.status);
            }
        } catch (error) {
            console.error('Status update error:', error);
        }
    }
    
    updateMonitoringStatus(status) {
        console.log('updateMonitoringStatus called with:', status);
        
        this.isMonitoring = status.is_running;
        this.updateMonitoringButtons();
        
        // Update countdown - always stop timer if monitoring is not running
        if (status.is_running && status.next_check) {
            this.updateNextCheckCountdown(status.next_check);
        } else {
            // Monitoring stopped or no next check scheduled - clear countdown
            document.getElementById('countdown-display').textContent = '--:--:--';
            if (this.nextCheckTimer) {
                clearInterval(this.nextCheckTimer);
                this.nextCheckTimer = null;
                console.log('Countdown timer cleared - monitoring stopped');
            }
        }
        
        // Update status indicator
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');
        
        if (status.is_running) {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'Monitoring';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Stopped';
        }
    }
    
    updateMonitoringButtons() {
        document.getElementById('start-monitoring-btn').disabled = this.isMonitoring;
        document.getElementById('stop-monitoring-btn').disabled = !this.isMonitoring;
    }
    
    updateConnectionStatus(connected) {
        // This could be used to show connection status
        if (!connected) {
            this.showToast('Connection lost. Reconnecting...', 'warning');
        }
    }
    
    updateNextCheckCountdown(nextCheckTimestamp) {
        // Clear existing timer
        if (this.nextCheckTimer) {
            clearInterval(this.nextCheckTimer);
        }
        
        const updateCountdown = () => {
            const now = Date.now();
            const timeLeft = nextCheckTimestamp - now;
            
            if (timeLeft <= 0) {
                document.getElementById('countdown-display').textContent = '00:00:00';
                clearInterval(this.nextCheckTimer);
                return;
            }
            
            // Calculate time components
            const hours = Math.floor(timeLeft / 3600000);
            const minutes = Math.floor((timeLeft % 3600000) / 60000);
            const seconds = Math.floor((timeLeft % 60000) / 1000);
            
            // Update countdown display only
            const countdownText = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            document.getElementById('countdown-display').textContent = countdownText;
        };
        
        // Update immediately
        updateCountdown();
        
        // Then update every second
        this.nextCheckTimer = setInterval(updateCountdown, 1000);
    }
    
    handleSlotsFound(data) {
        this.showToast('Potential slots found! Check manually.', 'warning');
        this.addLogEntry('warning', `Found ${data.slots.length} potential slots`);
        
        // Show modal with slot details
        this.showSlotsModal(data.slots);
        
        // Play notification sound if available
        this.playNotificationSound();
    }
    
    handleMonitoringError(data) {
        this.showToast(data.message, 'error');
        this.addLogEntry('error', data.message);
        this.isMonitoring = false;
        this.updateMonitoringButtons();
        
        // Stop countdown timer when monitoring fails
        document.getElementById('countdown-display').textContent = '--:--:--';
        if (this.nextCheckTimer) {
            clearInterval(this.nextCheckTimer);
            this.nextCheckTimer = null;
            console.log('Countdown timer cleared due to monitoring error');
        }
    }
    
    handleMonitoringFailed(data) {
        console.log('Monitoring failed event received:', data);
        
        // Stop monitoring state
        this.isMonitoring = false;
        this.updateMonitoringButtons();
        
        // Stop countdown timer
        document.getElementById('countdown-display').textContent = '--:--:--';
        if (this.nextCheckTimer) {
            clearInterval(this.nextCheckTimer);
            this.nextCheckTimer = null;
            console.log('Countdown timer cleared due to monitoring failure');
        }
        
        // Show monitoring failed modal
        this.showMonitoringFailedModal(data);
        
        // Also add to logs
        this.addLogEntry('error', data.message);
    }
    
    showMonitoringFailedModal(data) {
        // Populate modal content
        document.getElementById('failed-modal-title').textContent = data.title || 'Monitoring Failed';
        document.getElementById('failed-modal-message').textContent = data.message || 'Monitoring has stopped unexpectedly.';
        
        // Show error details if provided
        const detailsElement = document.getElementById('failed-modal-details');
        if (data.error_details) {
            detailsElement.style.display = 'block';
            detailsElement.textContent = data.error_details;
        } else {
            detailsElement.style.display = 'none';
        }
        
        // Show restart button if requested
        const restartBtn = document.getElementById('restart-monitoring-btn');
        if (data.show_restart_option) {
            restartBtn.style.display = 'inline-block';
        } else {
            restartBtn.style.display = 'none';
        }
        
        // Show the modal
        document.getElementById('monitoring-failed-modal').style.display = 'flex';
    }
    
    closeMonitoringFailedModal() {
        document.getElementById('monitoring-failed-modal').style.display = 'none';
    }
    
    async restartFromFailure() {
        console.log('Restarting monitoring from failure modal...');
        
        // Close the modal first
        this.closeMonitoringFailedModal();
        
        // Start monitoring
        await this.startMonitoring();
        
        // Show success message
        this.showToast('Monitoring restarted successfully', 'success');
    }
    
    showSlotsModal(slots) {
        const slotsList = document.getElementById('slots-list');
        slotsList.innerHTML = '';
        
        slots.forEach((slot, index) => {
            const slotElement = document.createElement('div');
            slotElement.className = 'slot-item';
            slotElement.innerHTML = `
                <div class="slot-header">
                    <strong>Slot ${index + 1}</strong>
                </div>
                <div class="slot-details">
                    <p><strong>Month Offset:</strong> ${slot.month_offset}</p>
                    <p><strong>Status:</strong> ${slot.element_text}</p>
                    <p><strong>Time:</strong> ${slot.time}</p>
                </div>
            `;
            slotsList.appendChild(slotElement);
        });
        
        this.showModal('slots-modal');
    }
    
    addLogEntry(level, message, timestamp = null) {
        const logsContent = document.getElementById('logs-content');
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${level}`;
        
        const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        
        logEntry.innerHTML = `
            <span class="log-time">[${time}]</span>
            <span class="log-message">${this.escapeHtml(message)}</span>
        `;
        
        logsContent.appendChild(logEntry);
        
        // Auto-scroll if enabled
        if (this.autoScroll) {
            logsContent.scrollTop = logsContent.scrollHeight;
        }
        
        // Limit log entries (keep last 100)
        while (logsContent.children.length > 100) {
            logsContent.removeChild(logsContent.firstChild);
        }
    }
    
    clearLogs() {
        const logsContent = document.getElementById('logs-content');
        logsContent.innerHTML = '';
        this.addLogEntry('info', 'Logs cleared - showing only important messages');
    }
    
    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        const btn = document.getElementById('auto-scroll-btn');
        
        if (this.autoScroll) {
            btn.classList.add('active');
            btn.innerHTML = '<i class="fas fa-arrow-down"></i> Auto Scroll';
        } else {
            btn.classList.remove('active');
            btn.innerHTML = '<i class="fas fa-pause"></i> Paused';
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.getElementById('toast-notification');
        const toastMessage = document.getElementById('toast-message');
        const toastIcon = toast.querySelector('.toast-icon i');
        const toastIconDiv = toast.querySelector('.toast-icon');
        
        // Update content
        toastMessage.textContent = message;
        
        // Update icon based on type
        toastIconDiv.className = `toast-icon ${type}`;
        
        switch (type) {
            case 'success':
                toastIcon.className = 'fas fa-check-circle';
                break;
            case 'error':
                toastIcon.className = 'fas fa-exclamation-circle';
                break;
            case 'warning':
                toastIcon.className = 'fas fa-exclamation-triangle';
                break;
            case 'info':
            default:
                toastIcon.className = 'fas fa-info-circle';
                break;
        }
        
        // Show toast
        toast.classList.add('show');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideToast();
        }, 5000);
    }
    
    hideToast() {
        document.getElementById('toast-notification').classList.remove('show');
    }
    
    showModal(modalId) {
        document.getElementById(modalId).classList.add('show');
        document.body.style.overflow = 'hidden';
    }
    
    hideModal(modalId) {
        document.getElementById(modalId).classList.remove('show');
        document.body.style.overflow = '';
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.add('show');
        } else {
            overlay.classList.remove('show');
        }
    }
    
    playNotificationSound() {
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJevrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUYrTp66hVFApGn+P0wF8xBBl/zPDeSzgIGGK+7+OZURE');
            audio.play().catch(() => {
                // Ignore errors if sound cannot be played
            });
        } catch (e) {
            // Ignore errors
        }
    }
    
    formatDateTime(dateString) {
        return new Date(dateString).toLocaleString();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    shouldShowLogMessage(message, level) {
        // Filter out technical UC mode messages
        const filteredMessages = [
            'UC mode opens in separate window (cannot be embedded due to anti-detection features)'
        ];
        
        if (filteredMessages.some(filtered => message.includes(filtered))) {
            return false;
        }
        
        // Always show errors and warnings (except filtered ones above)
        if (level === 'error' || level === 'warning') {
            return true;
        }
        
        // Show important success messages and status updates
        const importantKeywords = [
            // Check results
            'CHECK #', 'completed', 'SLOTS FOUND', 'No slots found', 'No appointment slots found',
            // Major status changes
            'Starting TLS', 'Monitoring started', 'Monitoring stopped', 'Stop signal sent',
            // Success states
            'Login successful', 'Navigation successful', 'Check complete',
            // Important notifications
            'notification sent', 'Email notification', 'Desktop notification',
            // Connection status
            'Socket.IO connection established', 'Dashboard initialized successfully',
            // Configuration
            'Configuration updated', 'Using TLS account'
        ];
        
        // Check if message contains any important keywords
        const messageUpper = message.toUpperCase();
        return importantKeywords.some(keyword => 
            messageUpper.includes(keyword.toUpperCase())
        );
    }
    
    showPopupNotification(data) {
        console.log('Showing popup notification:', data);
        
        const popup = document.getElementById('popup-notification');
        const title = document.getElementById('popup-title');
        const message = document.getElementById('popup-message');
        const icon = document.getElementById('popup-icon');
        const actionsContainer = document.getElementById('popup-actions');
        
        // Set content
        title.textContent = data.title || 'Notification';
        message.innerHTML = (data.message || '').replace(/\n/g, '<br>');
        
        // Set icon and style based on type
        let iconClass = 'fas fa-info-circle';
        let typeClass = 'info';
        
        if (data.type === 'success') {
            iconClass = 'fas fa-check-circle';
            typeClass = 'success';
        } else if (data.type === 'error') {
            iconClass = 'fas fa-exclamation-triangle';
            typeClass = 'error';
        } else if (data.type === 'warning') {
            iconClass = 'fas fa-exclamation-circle';
            typeClass = 'warning';
        }
        
        icon.innerHTML = `<i class="${iconClass}"></i>`;
        popup.className = `popup-notification ${typeClass}`;
        
        // Handle actions
        if (data.actions && data.actions.length > 0) {
            actionsContainer.innerHTML = '';
            data.actions.forEach(action => {
                const button = document.createElement('button');
                button.className = 'btn btn-sm btn-primary';
                button.textContent = action.text;
                button.onclick = () => this.handlePopupAction(action.action);
                actionsContainer.appendChild(button);
            });
            actionsContainer.style.display = 'block';
        } else {
            actionsContainer.style.display = 'none';
        }
        
        // Show popup
        popup.classList.add('show');
        
        // Play sound if requested
        if (data.sound) {
            this.playNotificationSound();
        }
        
        // Auto-hide if duration is specified
        if (data.duration && data.duration > 0) {
            setTimeout(() => {
                this.hidePopupNotification();
            }, data.duration);
        }
        
        // Add to logs
        this.addLogEntry(data.type || 'info', `🔔 ${data.title}: ${data.message}`);
    }
    
    hidePopupNotification() {
        const popup = document.getElementById('popup-notification');
        popup.classList.remove('show');
    }
    
    handlePopupAction(action) {
        console.log('Handling popup action:', action);
        
        if (action === 'restart_monitoring') {
            this.hidePopupNotification();
            this.startMonitoring();
        } else if (action === 'focus_dashboard') {
            this.hidePopupNotification();
            window.focus();
        } else if (action === 'open_tls_website') {
            // Open TLS website in new tab
            window.open('https://visas-de.tlscontact.com/', '_blank');
            this.hidePopupNotification();
        } else if (action === 'view_slot_details') {
            // Hide popup and show slots modal if available
            this.hidePopupNotification();
            // The slots modal should already be shown by the slots_found event
        }
    }
}

// Global functions for modal controls
let dashboardInstance = null;

function closeMonitoringFailedModal() {
    if (dashboardInstance) {
        dashboardInstance.closeMonitoringFailedModal();
    }
}

// Global functions for popup actions
function focusDashboard() {
    window.focus();
}

function restartFromFailure() {
    if (dashboardInstance) {
        dashboardInstance.restartFromFailure();
    }
}

// Initialize the dashboard with retry logic
function initializeDashboard() {
    try {
        console.log('Initializing TLS Monitor Dashboard...');
        dashboardInstance = new TLSMonitorDashboard();
        console.log('Dashboard initialized successfully');
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        // Retry after a short delay
        setTimeout(() => {
            console.log('Retrying dashboard initialization...');
            initializeDashboard();
        }, 2000);
    }
}

// Multiple initialization methods to ensure compatibility
function startInit() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeDashboard);
    } else {
        initializeDashboard();
    }
}

// Start initialization immediately if possible, otherwise wait
if (typeof window !== 'undefined') {
    if (window.addEventListener) {
        window.addEventListener('load', initializeDashboard);
    }
    startInit();
} else {
    // Fallback for older browsers
    setTimeout(initializeDashboard, 1000);
}
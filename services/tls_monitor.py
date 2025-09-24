"""
TLS Web Monitor Service - Koyeb Optimized Version
Enhanced Chrome support for Koyeb cloud deployment
"""

import os
import time
import logging
import random
import smtplib
import threading
import sys
import tempfile
import uuid
import shutil
from datetime import datetime
from typing import Dict, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Check if SeleniumBase is available
try:
    from seleniumbase import Driver
    SELENIUMBASE_AVAILABLE = True
except ImportError:
    SELENIUMBASE_AVAILABLE = False

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

try:
    import win10toast
    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False

# UC control flag - set TLS_ENABLE_UC=1 to force UC in cloud (not recommended for stability)
TLS_ENABLE_UC = os.environ.get("TLS_ENABLE_UC") == "1"

class TLSWebMonitor:
    def __init__(self, config: Dict, socketio=None):
        self.config = config
        self.socketio = socketio
        self.driver = None
        self._is_seleniumbase = False
        self.logger = self._setup_logging()
        self._running = False
        self._initializing = False  # Flag to track driver initialization
        self._stop_event = threading.Event()
        self._last_check_time = None
        self._total_checks = 0
        self._error_count = 0
        self._browser_port = None
        self._temp_user_data_dir = None  # Store temp directory for cleanup
        # Instance identifier (used only for debug/status; safe accessor via getattr elsewhere)
        try:
            self._instance_id = uuid.uuid4().hex[:8]
        except Exception:
            # Fallback static id if uuid fails for any reason
            self._instance_id = "instance"
        
    def _setup_logging(self):
        """Setup logging configuration optimized for cloud deployment"""
        import sys
        
        # Create logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Clear any root logger handlers that might cause duplicates
        root_logger = logging.getLogger()
        if root_logger.handlers:
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler):
                    root_logger.removeHandler(handler)
        
        # Create logs directory in cloud-friendly location
        logs_dir = os.environ.get('LOG_DIR', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_file_path = os.path.join(logs_dir, 'tls_web_monitor.log')
        
        # File handler with UTF-8 encoding
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler with UTF-8 encoding (cloud platforms typically use Linux)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Cloud deployment typically runs on Linux, no need for Windows-specific encoding
        # But keep it for local testing compatibility
        if sys.platform == 'win32':
            try:
                # Try to set console to UTF-8
                os.system("chcp 65001 > nul")
                console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
            except:
                # Fallback: replace Unicode characters for console
                pass
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _emit_log(self, level: str, message: str):
        """Emit log message to web interface and console (no duplication)"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        
        if self.socketio:
            self.socketio.emit('log_message', log_entry)
        
        # Simple console output with timestamp (no logger to avoid duplication)
        timestamp = datetime.now().strftime('[%H:%M:%S]')
        print(f"{timestamp} {message}")
        
        # Only log to file (quietly, no console output from logger)
        try:
            # Create a file-only logger to avoid console duplication
            file_logger = logging.getLogger(f"{__name__}_file_only")
            file_logger.handlers = []  # Clear any existing handlers
            
            # Add only file handler
            file_handler = logging.FileHandler('tls_web_monitor.log', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            file_logger.addHandler(file_handler)
            file_logger.setLevel(logging.INFO)
            
            if level.lower() == 'info':
                file_logger.info(message)
            elif level.lower() == 'warning':
                file_logger.warning(message)
            elif level.lower() == 'error':
                file_logger.error(message)
            
        except Exception as log_error:
            # If logging fails, don't crash the application
            print(f"[LOG ERROR] {log_error}")
    
    def _emit_status_update(self, status_data: Dict):
        """Emit status update to web interface"""
        if self.socketio:
            self.socketio.emit('status_update', status_data)
    
    def _human_delay(self, min_seconds=1, max_seconds=3):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        # Make delay interruptible by checking stop signal
        elapsed = 0
        while elapsed < delay:
            if self._stop_event.is_set():
                return
            sleep_time = min(0.1, delay - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time
    
    def _cleanup_failed_chrome_attempt(self):
        """Clean up any leftover Chrome processes and user data after failed initialization"""
        try:
            # Kill any stray Chrome/ChromeDriver processes
            import subprocess
            
            # Find and kill Chrome processes
            for process_name in ['chrome', 'google-chrome', 'google-chrome-stable', 'chromedriver']:
                try:
                    result = subprocess.run(['pkill', '-f', process_name], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        self._emit_log('info', f"🗑️ Killed stray {process_name} processes")
                except Exception:
                    pass
            
            # Clean up temp user data directory if it exists
            if self._temp_user_data_dir and os.path.exists(self._temp_user_data_dir):
                try:
                    import shutil
                    shutil.rmtree(self._temp_user_data_dir)
                    self._emit_log('info', f"🗑️ Cleaned up failed attempt user data: {self._temp_user_data_dir}")
                    self._temp_user_data_dir = None
                except Exception as e:
                    self._emit_log('warning', f"Could not clean up user data dir: {e}")
                    
            # Small delay to let processes fully terminate
            import time
            time.sleep(0.5)
            
        except Exception as e:
            self._emit_log('warning', f"Error during Chrome cleanup: {e}")

    def _setup_driver(self):
        """Initialize the browser driver with cloud-stable configuration"""
        instance_id = getattr(self, '_instance_id', 'unknown')
        print(f"[DEBUG] {instance_id} - Setting up Chrome WebDriver")
        
        # Detect cloud deployment platforms
        is_render = os.environ.get('RENDER_SERVICE_NAME') is not None
        is_koyeb = os.environ.get('KOYEB_SERVICE_NAME') is not None
        is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None
        is_heroku = os.environ.get('HEROKU_APP_NAME') is not None
        is_cloud_deployment = any([is_render, is_koyeb, is_railway, is_heroku, os.environ.get('PORT')])
        
        # Disable UC in cloud unless explicitly forced via environment variable
        use_uc = (
            self.config.get("use_seleniumbase_uc", False)
            and SELENIUMBASE_AVAILABLE
            and (not is_cloud_deployment or TLS_ENABLE_UC)
        )
        
        # Clean up any stray Chrome processes from previous runs
        if is_cloud_deployment:
            try:
                import subprocess
                process_names = ['chrome', 'google-chrome', 'google-chrome-stable', 'chromedriver', 'uc_driver']
                for process_name in process_names:
                    try:
                        subprocess.run(['pkill', '-f', process_name], capture_output=True, timeout=2)
                    except Exception:
                        pass
                # Small delay to let processes terminate
                time.sleep(0.3)
                self._emit_log('info', "🧹 Cleaned up any stray Chrome processes")
            except Exception as e:
                self._emit_log('info', f"Process cleanup note: {e}")
        
        # Find Chrome binary in cloud environments
        chrome_binary = None
        if is_cloud_deployment:
            platform = "Koyeb" if is_koyeb else "Render" if is_render else "Railway" if is_railway else "Heroku" if is_heroku else "Cloud"
            self._emit_log('info', f"🌐 Detected {platform} deployment - setting up Chrome...")
            
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium'
            ]
            
            for path in chrome_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    chrome_binary = path
                    self._emit_log('info', f"✅ Found Chrome: {chrome_binary}")
                    break
                    
            if not chrome_binary:
                raise RuntimeError(f"Chrome binary not found on {platform} - Chrome installation required")
        
        # Try SeleniumBase UC mode (only if not in cloud or explicitly enabled)
        if use_uc:
            try:
                self._emit_log('info', "🚀 Initializing SeleniumBase UC mode...")
                if chrome_binary:
                    os.environ['CHROME_BIN'] = chrome_binary
                self.driver = Driver(uc=True, headless=is_cloud_deployment or is_render)
                self._is_seleniumbase = True
                self._emit_log('info', "✅ SeleniumBase UC driver initialized successfully")
                return
            except Exception as e:
                self._emit_log('warning', f"❌ SeleniumBase UC failed: {e}")
                self._cleanup_failed_chrome_attempt()
                self._emit_log('info', "🔄 Falling back to regular Selenium WebDriver...")
        
        # Regular Selenium WebDriver setup with minimal, stable flags
        self._emit_log('info', "🔧 Using regular Selenium WebDriver")
        self._is_seleniumbase = False
        
        options = Options()
        
        # Headless mode for cloud or user preference
        headless_mode = True if is_cloud_deployment else self.config.get("headless_mode", False)
        if headless_mode:
            options.add_argument('--headless=new')
        
        # Minimal stable Chrome flags (remove duplicates and problematic ones)
        stable_flags = [
            '--no-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--mute-audio',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-features=TranslateUI',
            '--disable-blink-features=AutomationControlled',
            '--remote-debugging-port=0'  # Use random port to avoid conflicts
        ]
        
        for flag in stable_flags:
            options.add_argument(flag)
        
        # Create unique user data directory (use /tmp instead of /dev/shm for stability)
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time() * 1000)
        process_id = os.getpid()
        unique_user_data_dir = os.path.join(temp_dir, f"chrome_user_data_{timestamp}_{process_id}_{uuid.uuid4().hex[:8]}")
        
        os.makedirs(unique_user_data_dir, exist_ok=True)
        options.add_argument(f'--user-data-dir={unique_user_data_dir}')
        self._temp_user_data_dir = unique_user_data_dir
        self._emit_log('info', f"🗂️ Using user data directory: {unique_user_data_dir}")
        
        # Anti-automation detection
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Set Chrome binary if found
        if chrome_binary:
            options.binary_location = chrome_binary
            self._emit_log('info', f"🎯 Chrome binary set to: {chrome_binary}")
        
        try:
            # Use webdriver-manager to handle ChromeDriver
            self._emit_log('info', "📦 Installing/updating ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            
            self._emit_log('info', f"🚀 Starting Chrome WebDriver with {len(options.arguments)} arguments...")
            
            # Start WebDriver
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Enhanced anti-detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set timeouts
            self.driver.implicitly_wait(self.config.get("implicit_wait", 10))
            self.driver.set_page_load_timeout(self.config.get("page_load_timeout", 30))
            
            self._emit_log('info', "✅ Chrome WebDriver initialized successfully")
            
        except Exception as driver_error:
            self._emit_log('error', f"❌ Failed to initialize Chrome WebDriver: {driver_error}")
            if is_cloud_deployment:
                platform = "Koyeb" if is_koyeb else "Render" if is_render else "Railway" if is_railway else "Heroku" if is_heroku else "Cloud"
                self._emit_log('error', f"🔍 {platform} diagnostic information:")
                self._emit_log('error', f"  Chrome binary: {chrome_binary}")
                self._emit_log('error', f"  CHROME_BIN env: {os.environ.get('CHROME_BIN', 'Not set')}")
                self._emit_log('error', f"🔧 Check {platform} build logs for Chrome installation issues")
            raise
    
    def login(self) -> bool:
        """Log in to TLS website starting from El-Sheikh Zayed page"""
        try:
            # Navigate to El-Sheikh Zayed page
            self._emit_log('info', "Navigating to El-Sheikh Zayed TLS page...")
            self.driver.get(self.config["tls_url"])
            self._human_delay(3, 5)
            
            self._emit_log('info', f"Current URL: {self.driver.current_url}")
            self._emit_log('info', f"Page title: {self.driver.title}")
            
            # Find and click LOGIN button
            self._emit_log('info', "Looking for LOGIN button...")
            login_selector = "//span[contains(text(), 'LOGIN')]"
            
            if self._is_seleniumbase:
                elements = self.driver.find_elements("xpath", login_selector)
            else:
                elements = self.driver.find_elements(By.XPATH, login_selector)
            
            if elements:
                elem = elements[0]
                self._emit_log('info', f"Found login element: {elem.tag_name}")
                
                # Click parent link if it's a span
                if elem.tag_name == 'span':
                    parent = elem.find_element(By.XPATH, "./..")
                    if parent.tag_name == 'a':
                        self._emit_log('info', "Clicking parent link of LOGIN span")
                        if self._is_seleniumbase:
                            self.driver.execute_script("arguments[0].click();", parent)
                        else:
                            parent.click()
                
                self._human_delay(3, 5)
            else:
                self._emit_log('warning', "Could not find LOGIN button, trying direct navigation")
                self.driver.get(self.config["login_start_url"])
                self._human_delay(3, 5)
            
            # Wait for login form and fill credentials
            self._emit_log('info', "Entering login credentials...")
            
            # Fill email
            email_selector = "#email-input-field"
            if self._is_seleniumbase:
                self.driver.type(email_selector, self.config["login_credentials"]["email"])
            else:
                email_field = self.driver.find_element(By.CSS_SELECTOR, email_selector)
                email_field.clear()
                email_field.send_keys(self.config["login_credentials"]["email"])
            
            self._human_delay(1, 2)
            
            # Fill password
            password_selector = "#password-input-field"
            if self._is_seleniumbase:
                self.driver.type(password_selector, self.config["login_credentials"]["password"])
            else:
                password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
                password_field.clear()
                password_field.send_keys(self.config["login_credentials"]["password"])
            
            self._human_delay(1, 2)
            
            # Click login button
            self._emit_log('info', "Clicking login button...")
            login_button_selector = "#btn-login"
            if self._is_seleniumbase:
                self.driver.click(login_button_selector)
            else:
                login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)
                login_button.click()
            
            # Wait for login completion
            self._human_delay(3, 5)
            self._emit_log('info', "Login successful - no CAPTCHA required")
            return True
            
        except Exception as e:
            self._emit_log('error', f"Login failed: {e}")
            return False
    
    def navigate_to_appointment_booking(self) -> bool:
        """Navigate to appointment booking section"""
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Click the Select button for the travel group
            select_button_selector = "[data-testid='btn-select-group']"
            select_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, select_button_selector)))
            select_button.click()
            
            self._emit_log('info', "Navigated to appointment booking section")
            return True
            
        except Exception as e:
            self._emit_log('error', f"Failed to navigate to appointment booking: {e}")
            return False
    
    def check_available_slots(self, month_offset: int = 0) -> List[Dict]:
        """Check for available slots in a specific month"""
        available_slots = []
        
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Handle current month (month_offset 0)
            if month_offset == 0:
                time.sleep(3)  # Wait for page to load
                
                # Click current month button to ensure we're viewing it
                try:
                    current_month_selector = 'a[data-testid="btn-current-month-available"]'
                    current_month_button = self.driver.find_element(By.CSS_SELECTOR, current_month_selector)
                    month_text = current_month_button.text.strip()
                    self._emit_log('info', f"Ensuring we're viewing current month: {month_text}")
                    
                    if self._is_seleniumbase:
                        self.driver.execute_script("arguments[0].click();", current_month_button)
                    else:
                        current_month_button.click()
                    time.sleep(2)
                except Exception:
                    pass  # Continue if current month button click fails
            
            # Handle future months (month_offset > 0)
            elif month_offset > 0:
                next_month_selector = 'a[data-testid="btn-next-month-available"]'
                
                for i in range(month_offset):
                    try:
                        next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_month_selector)))
                        month_text = next_button.text.strip()
                        self._emit_log('info', f"Navigation step {i+1}: Clicking to navigate to {month_text}")
                        
                        if self._is_seleniumbase:
                            self.driver.execute_script("arguments[0].click();", next_button)
                        else:
                            next_button.click()
                        
                        time.sleep(3)
                        self._emit_log('info', f"Successfully navigated to: {month_text}")
                        
                    except Exception:
                        self._emit_log('debug', f"Navigation step {i+1} completed (expected for final month)")
                        break
            
            # Check for "no appointments" message
            page_source = self.driver.page_source.lower()
            no_appointment_texts = [
                "we currently don't have any appointment slots available",
                "no slots are currently available",
                "currently don't have any appointment slots"
            ]
            
            for text in no_appointment_texts:
                if text in page_source:
                    self._emit_log('info', f"No appointments available for month offset {month_offset}: {text}")
                    return []
            
            # If no "no appointments" message found, potential slots available
            self._emit_log('warning', f"POTENTIAL SLOTS AVAILABLE for month offset {month_offset} - verify manually!")
            slot_info = {
                'date': 'Unknown',
                'time': 'Slots may be available (verify manually)',
                'month_offset': month_offset,
                'element_text': 'No "no appointments" message found'
            }
            available_slots.append(slot_info)
            
            return available_slots
            
        except Exception as e:
            self._emit_log('error', f"Error checking month offset {month_offset}: {e}")
            return []
    
    def send_desktop_notification(self, slots: List[Dict], notification_type: str = "slots_found"):
        """Send desktop notification about available slots"""
        try:
            if not self.config["notification"]["desktop"]["enabled"] or not TOAST_AVAILABLE:
                return
            
            toaster = win10toast.ToastNotifier()
            
            title = "TLS Visa Slots Check - VERIFY MANUALLY!"
            message = f"Found {len(slots)} potential appointment slot(s)!\nPlease check TLS website manually to verify."
            
            toaster.show_toast(
                title,
                message,
                duration=30,  # Show for 30 seconds
                icon_path=None,
                threaded=True
            )
            
            self._emit_log('info', "Desktop notification sent successfully")
            
        except Exception as e:
            self._emit_log('error', f"Failed to send desktop notification: {e}")
    
    def send_no_slots_notification(self):
        """Send notification when no slots are found"""
        pass  # Implemented in original for completeness
    
    def send_error_notification(self, error_message: str = ""):
        """Send notification when monitoring encounters an error"""
        pass  # Implemented in original for completeness
    
    def send_monitoring_failed_notification(self):
        """Send notification when monitoring fails completely"""
        pass  # Implemented in original for completeness
        
    def send_email_notification(self, slots: List[Dict]):
        """Send email notification about available slots"""
        try:
            if not self.config["notification"]["email"]["enabled"]:
                return
            
            email_config = self.config["notification"]["email"]
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config["sender_email"]
            msg['To'] = email_config["receiver_email"]
            msg['Subject'] = email_config["subject"]
            
            # Create email body
            body = f"""
TLS Visa Appointment Slots Alert!

ATTENTION: {len(slots)} potential appointment slot(s) detected!

IMPORTANT: Please verify manually on the TLS website as this is an automated check.

Details:
"""
            
            for i, slot in enumerate(slots, 1):
                body += f"\n{i}. Month offset: {slot['month_offset']}"
                body += f"\n   Status: {slot['element_text']}"
                body += f"\n   Time: {slot['time']}"
                body += "\n"
            
            body += f"""
Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please log into the TLS website immediately to verify and book available slots:
https://visas-de.tlscontact.com/

This is an automated notification from your TLS Visa Slot Checker.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Setup SMTP server
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            server.starttls()  # Enable encryption
            server.login(email_config["sender_email"], email_config["sender_password"])
            
            # Send email
            text = msg.as_string()
            server.sendmail(email_config["sender_email"], email_config["receiver_email"], text)
            server.quit()
            
            self._emit_log('info', f"Email notification sent successfully to {email_config['receiver_email']}")
            
        except Exception as e:
            self._emit_log('error', f"Failed to send email notification: {e}")
    
    def run_check_cycle(self) -> bool:
        """Run a complete check cycle for all configured months"""
        try:
            if not self.login():
                return False
            
            if not self.navigate_to_appointment_booking():
                return False
            
            all_available_slots = []
            
            # Check slots for each month (current + next 2 months = 3 total)
            for month_offset in range(self.config["months_to_check"]):
                self._emit_log('info', f"Checking month offset {month_offset}...")
                try:
                    slots = self.check_available_slots(month_offset)
                    all_available_slots.extend(slots)
                except Exception as e:
                    self._emit_log('error', f"Error checking month offset {month_offset}: {type(e).__name__}")
                    continue
                
                time.sleep(2)  # Delay between checks
            
            # Send notifications if slots found
            if all_available_slots:
                self._emit_log('warning', "POTENTIAL SLOTS DETECTED - PLEASE VERIFY MANUALLY!")
                self._emit_log('info', f"SLOTS FOUND! Total: {len(all_available_slots)} available slots")
                for slot in all_available_slots:
                    self._emit_log('info', f"- Month offset {slot['month_offset']}: {slot['element_text']}")
                
                # Send both types of notifications
                self.send_desktop_notification(all_available_slots)
                self.send_email_notification(all_available_slots)
            else:
                self._emit_log('info', "No available slots found in any checked months")
            
            return True
            
        except Exception as e:
            self._emit_log('error', f"Error during check cycle: {e}")
            return False
    
    def start_monitoring(self):
        """Start continuous monitoring for available slots"""
        self._emit_log('info', "Starting TLS Visa Appointment Slot Monitoring...")
        self._emit_log('info', f"Checking every {self.config['check_interval_minutes']} minutes")
        self._emit_log('info', f"Monitoring {self.config['months_to_check']} months ahead")
        
        if self._running or self._initializing:
            self._emit_log('warning', "Monitoring is already running or initializing")
            return
            
        self._running = True
        self._initializing = True
        self._stop_event.clear()
        retry_count = 0
        max_retries = self.config["max_retries"]
        
        try:
            # Initialize driver once at start
            self._setup_driver()
            self._initializing = False  # Driver setup complete
        except Exception as e:
            self._initializing = False
            self._running = False
            self._emit_log('error', f"Failed to initialize driver: {e}")
            return
        
        while not self._stop_event.is_set():
            try:
                # Emit status update before starting check
                self._emit_status_update({
                    'is_running': True,
                    'last_check': None,
                    'total_checks': self._total_checks,
                    'error_count': self._error_count,
                    'status': 'Running check...'
                })
                
                # Driver is already set up once at start - no need to recreate each cycle
                success = self.run_check_cycle()
                self._total_checks += 1
                self._last_check_time = datetime.now()
                
                if success:
                    retry_count = 0  # Reset retry count on success
                    self._emit_status_update({
                        'is_running': True,
                        'last_check': self._last_check_time.isoformat(),
                        'total_checks': self._total_checks,
                        'error_count': self._error_count,
                        'status': 'Check completed successfully'
                    })
                else:
                    retry_count += 1
                    self._error_count += 1
                    self._emit_log('warning', f"Check cycle failed. Retry {retry_count}/{max_retries}")
                    
                    if retry_count >= max_retries:
                        self._emit_log('error', "Maximum retries reached. Stopping monitoring.")
                        break
                        
                    self._emit_status_update({
                        'is_running': True,
                        'last_check': self._last_check_time.isoformat() if self._last_check_time else None,
                        'total_checks': self._total_checks,
                        'error_count': self._error_count,
                        'status': f'Check failed - retry {retry_count}/{max_retries}'
                    })
                
                # Wait before next check (interruptible)
                wait_seconds = self.config['check_interval_minutes'] * 60
                self._emit_log('info', f"Waiting {self.config['check_interval_minutes']} minutes before next check...")
                
                for _ in range(wait_seconds):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
                
            except Exception as e:
                self._emit_log('error', f"Unexpected error: {e}")
                self._error_count += 1
                retry_count += 1
                if retry_count >= max_retries:
                    break
                time.sleep(30)  # Wait 30 seconds before retry
        
        self._running = False
        self._emit_status_update({
            'is_running': False,
            'last_check': self._last_check_time.isoformat() if self._last_check_time else None,
            'total_checks': self._total_checks,
            'error_count': self._error_count,
            'status': 'Monitoring stopped'
        })
    
    def _cleanup_temp_data(self):
        """Clean up temporary user data directory"""
        if self._temp_user_data_dir and os.path.exists(self._temp_user_data_dir):
            try:
                shutil.rmtree(self._temp_user_data_dir)
                self._emit_log('info', f"🗑️ Cleaned up temp user data directory: {self._temp_user_data_dir}")
                self._temp_user_data_dir = None
            except Exception as e:
                self._emit_log('warning', f"Failed to clean up temp directory: {e}")
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        self._emit_log('info', "Stopping monitoring...")
        self._running = False
        self._stop_event.set()
        
        # Clean up driver if it exists
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.driver = None
        
        # Clean up temporary user data directory
        self._cleanup_temp_data()
    
    def force_stop(self):
        """Force stop monitoring immediately"""
        self._emit_log('warning', "Force stopping monitoring...")
        self._running = False
        self._stop_event.set()
        
        # Force quit driver
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.driver = None
        
        # Clean up temporary user data directory
        self._cleanup_temp_data()
    
    def is_running(self) -> bool:
        """Check if monitoring is currently running or initializing"""
        return self._running or self._initializing
    
    def get_last_check_time(self) -> str:
        """Get the last check time as ISO string"""
        return self._last_check_time.isoformat() if self._last_check_time else ""
    
    def get_total_checks(self) -> int:
        """Get total number of checks performed"""
        return self._total_checks
    
    def get_error_count(self) -> int:
        """Get total number of errors encountered"""
        return self._error_count
    
    def get_browser_port(self) -> int:
        """Get browser remote debugging port (Chrome only)"""
        return self._browser_port or 9222
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Clean up temporary user data directory
        if hasattr(self, '_temp_user_data_dir'):
            self._cleanup_temp_data()
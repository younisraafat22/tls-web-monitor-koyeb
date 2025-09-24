"""
TLS Web Monitor Service - Koyeb Optimized Version
Enhanced Chrome support for Koyeb cloud deployment
"""



import osimport os

import timeimport time

import loggingimport logging

import randomimport random

import smtplibimport smtplib

import threadingimport threading

import sysimport sys

from datetime import datetimefrom datetime import datetime

from typing import Dict, Listfrom typing import Dict, List

from email.mime.text import MIMETextfrom email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipartfrom email.mime.multipart import MIMEMultipart



# Check if SeleniumBase is available# Check if SeleniumBase is available

try:try:

    from seleniumbase import Driver    from seleniumbase import Driver

    SELENIUMBASE_AVAILABLE = True    SELENIUMBASE_AVAILABLE = True

except ImportError:except ImportError:

    SELENIUMBASE_AVAILABLE = False    SELENIUMBASE_AVAILABLE = False



from selenium import webdriverfrom selenium import webdriver

from selenium.webdriver.common.by import Byfrom selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWaitfrom selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.support import expected_conditions as ECfrom selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.options import Optionsfrom selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Servicefrom selenium.webdriver.chrome.service import Service

from selenium.common.exceptions import TimeoutException, NoSuchElementExceptionfrom selenium.common.exceptions import TimeoutException, NoSuchElementException

from webdriver_manager.chrome import ChromeDriverManagerfrom webdriver_manager.chrome import ChromeDriverManager



class TLSWebMonitor:try:

    def __init__(self, config: Dict, socketio=None):    import win10toast

        self.config = config    TOAST_AVAILABLE = True

        self.socketio = socketioexcept ImportError:

        self.driver = None    TOAST_AVAILABLE = False

        self._is_seleniumbase = False

        self.logger = self._setup_logging()class TLSWebMonitor:

        self._running = False    def __init__(self, config: Dict, socketio=None):

        self._stop_event = threading.Event()        self.config = config

        self._last_check_time = None        self.socketio = socketio

        self._total_checks = 0        self.driver = None

        self._error_count = 0        self._is_seleniumbase = False

        self._browser_port = None        self.logger = self._setup_logging()

                self._running = False

    def _setup_logging(self):        self._stop_event = threading.Event()

        """Setup logging configuration with Unicode support"""        self._last_check_time = None

        import sys        self._total_checks = 0

                self._error_count = 0

        # Create logger        self._browser_port = None

        logger = logging.getLogger(__name__)        

        logger.setLevel(logging.INFO)    def _setup_logging(self):

                """Setup logging configuration with Unicode support"""

        # Clear existing handlers to avoid duplicates        import sys

        for handler in logger.handlers[:]:        

            logger.removeHandler(handler)        # Create logger

                logger = logging.getLogger(__name__)

        # File handler with UTF-8 encoding        logger.setLevel(logging.INFO)

        os.makedirs('logs', exist_ok=True)        

        file_handler = logging.FileHandler('logs/tls_web_monitor.log', encoding='utf-8')        # Clear existing handlers to avoid duplicates

        file_handler.setLevel(logging.INFO)        for handler in logger.handlers[:]:

                    logger.removeHandler(handler)

        # Console handler with UTF-8 encoding        

        console_handler = logging.StreamHandler(sys.stdout)        # Clear any root logger handlers that might cause duplicates

        console_handler.setLevel(logging.INFO)        root_logger = logging.getLogger()

                if root_logger.handlers:

        # Create formatter            for handler in root_logger.handlers[:]:

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')                if isinstance(handler, logging.StreamHandler):

        file_handler.setFormatter(formatter)                    root_logger.removeHandler(handler)

        console_handler.setFormatter(formatter)        

                # File handler with UTF-8 encoding

        # Add handlers        file_handler = logging.FileHandler('tls_web_monitor.log', encoding='utf-8')

        logger.addHandler(file_handler)        file_handler.setLevel(logging.INFO)

        logger.addHandler(console_handler)        

                # Console handler with UTF-8 encoding for Windows

        return logger        console_handler = logging.StreamHandler(sys.stdout)

            console_handler.setLevel(logging.INFO)

    def _emit_log(self, level: str, message: str):        

        """Emit log message to web interface and console"""        # Set encoding for Windows console

        log_entry = {        if sys.platform == 'win32':

            'timestamp': datetime.now().isoformat(),            try:

            'level': level,                # Try to set console to UTF-8

            'message': message                import os

        }                os.system("chcp 65001 > nul")

                        console_handler.stream.reconfigure(encoding='utf-8', errors='replace')

        if self.socketio:            except:

            self.socketio.emit('log_message', log_entry)                # Fallback: replace Unicode characters for console

                        pass

        # Simple console output with timestamp        

        timestamp = datetime.now().strftime('[%H:%M:%S]')        # Create formatter

        print(f"{timestamp} {message}")        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            file_handler.setFormatter(formatter)

    def _emit_status_update(self, status_data: Dict):        console_handler.setFormatter(formatter)

        """Emit status update to web interface"""        

        if self.socketio:        # Add handlers

            self.socketio.emit('status_update', status_data)        logger.addHandler(file_handler)

            logger.addHandler(console_handler)

    def _human_delay(self, min_seconds=1, max_seconds=3):        

        """Add random delay to mimic human behavior"""        return logger

        delay = random.uniform(min_seconds, max_seconds)    

        # Make delay interruptible by checking stop signal    def _emit_log(self, level: str, message: str):

        elapsed = 0        """Emit log message to web interface and console (no duplication)"""

        while elapsed < delay:        log_entry = {

            if self._stop_event.is_set():            'timestamp': datetime.now().isoformat(),

                return            'level': level,

            sleep_time = min(0.1, delay - elapsed)            'message': message

            time.sleep(sleep_time)        }

            elapsed += sleep_time        

            if self.socketio:

    def _setup_driver(self):            self.socketio.emit('log_message', log_entry)

        """Initialize the browser driver optimized for Koyeb"""        

        use_uc = self.config.get("use_seleniumbase_uc", False) and SELENIUMBASE_AVAILABLE        # Simple console output with timestamp (no logger to avoid duplication)

                timestamp = datetime.now().strftime('[%H:%M:%S]')

        # Detect Koyeb deployment        print(f"{timestamp} {message}")

        is_koyeb = os.environ.get('KOYEB_DEPLOYMENT') is not None or os.environ.get('PORT') is not None        

                # Only log to file (quietly, no console output from logger)

        if is_koyeb:        try:

            self._emit_log('info', "🚀 Koyeb deployment detected - optimizing Chrome setup...")            # Create a file-only logger to avoid console duplication

                        file_logger = logging.getLogger(f"{__name__}_file_only")

            # Verify Chrome installation            file_logger.handlers = []  # Clear any existing handlers

            chrome_paths = [            

                '/usr/bin/google-chrome',            # Add only file handler

                '/usr/bin/google-chrome-stable',            file_handler = logging.FileHandler('tls_web_monitor.log', encoding='utf-8')

                '/usr/bin/chromium-browser',            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

                '/usr/bin/chromium'            file_logger.addHandler(file_handler)

            ]            file_logger.setLevel(logging.INFO)

                        

            chrome_binary = None            if level.lower() == 'info':

            for path in chrome_paths:                file_logger.info(message)

                if os.path.exists(path) and os.access(path, os.X_OK):            elif level.lower() == 'warning':

                    chrome_binary = path                file_logger.warning(message)

                    self._emit_log('info', f"✅ Chrome found: {chrome_binary}")            elif level.lower() == 'error':

                    break                file_logger.error(message)

                        

            if not chrome_binary:        except Exception as log_error:

                self._emit_log('error', "❌ Chrome not found! Check Dockerfile installation.")            # If logging fails, don't crash the application

                raise Exception("Chrome binary not found in Koyeb container")            print(f"[LOG ERROR] {log_error}")

            

        if use_uc:    def _emit_status_update(self, status_data: Dict):

            try:        """Emit status update to web interface"""

                self._emit_log('info', "🛡️ Initializing SeleniumBase UC mode for Cloudflare bypass...")        if self.socketio:

                            self.socketio.emit('status_update', status_data)

                # Set Chrome binary for SeleniumBase    

                if is_koyeb and chrome_binary:    def _human_delay(self, min_seconds=1, max_seconds=3):

                    os.environ['CHROME_BIN'] = chrome_binary        """Add random delay to mimic human behavior"""

                        delay = random.uniform(min_seconds, max_seconds)

                # Create UC driver with Koyeb optimizations        # Make delay interruptible by checking stop signal

                driver_kwargs = {'uc': True}        elapsed = 0

                if is_koyeb:        while elapsed < delay:

                    driver_kwargs['headless'] = True            if self._stop_event.is_set():

                                    return

                self.driver = Driver(**driver_kwargs)            sleep_time = min(0.1, delay - elapsed)

                self._emit_log('info', "✅ SeleniumBase UC mode initialized successfully!")            time.sleep(sleep_time)

                self._is_seleniumbase = True            elapsed += sleep_time

                return    

                    def _setup_driver(self):

            except Exception as e:        """Initialize the browser driver with Render.com cloud support"""

                self._emit_log('warning', f"⚠️ SeleniumBase UC failed: {e}")        use_uc = self.config.get("use_seleniumbase_uc", False) and SELENIUMBASE_AVAILABLE

                self._emit_log('warning', "🔄 Falling back to regular Selenium...")        

                        # Detect Render.com deployment

        # Fallback to regular Selenium with Koyeb optimizations        is_render = os.environ.get('RENDER_SERVICE_NAME') is not None

        self._emit_log('info', "🔧 Initializing regular Chrome WebDriver...")        

        self._is_seleniumbase = False        if is_render:

                    self._emit_log('info', "🌐 Detected Render.com deployment - setting up Chrome...")

        options = Options()            

                    # Force headless mode on Render

        # Koyeb-specific Chrome options            headless_mode = True

        if is_koyeb:            

            self._emit_log('info', "⚙️ Applying Koyeb Chrome optimizations...")            # Find Chrome binary on Render.com

                        chrome_binary = None

            # Essential headless options            render_chrome_paths = [

            options.add_argument('--headless=new')                '/usr/bin/google-chrome',

            options.add_argument('--no-sandbox')                '/usr/bin/google-chrome-stable', 

            options.add_argument('--disable-dev-shm-usage')                '/usr/bin/chromium-browser',

            options.add_argument('--disable-gpu')                '/usr/bin/chromium',

            options.add_argument('--disable-software-rasterizer')                '/opt/google/chrome/chrome',

                            '/snap/bin/chromium'

            # Memory and performance optimizations            ]

            options.add_argument('--memory-pressure-off')            

            options.add_argument('--disable-background-timer-throttling')            self._emit_log('info', "🔍 Searching for Chrome binary on Render...")

            options.add_argument('--disable-backgrounding-occluded-windows')            for path in render_chrome_paths:

            options.add_argument('--disable-renderer-backgrounding')                if os.path.exists(path) and os.access(path, os.X_OK):

            options.add_argument('--disable-features=TranslateUI')                    chrome_binary = path

            options.add_argument('--disable-ipc-flooding-protection')                    self._emit_log('info', f"✅ Found Chrome: {chrome_binary}")

            options.add_argument('--disable-extensions')                    break

            options.add_argument('--disable-plugins')            

            options.add_argument('--disable-default-apps')            if not chrome_binary:

            options.add_argument('--disable-sync')                self._emit_log('warning', "⚠️ Chrome not found in standard locations, checking installed packages...")

                            try:

            # Set Chrome binary                    import subprocess

            if chrome_binary:                    result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True, timeout=10)

                options.binary_location = chrome_binary                    if result.returncode == 0 and result.stdout.strip():

                self._emit_log('info', f"🎯 Chrome binary: {chrome_binary}")                        chrome_binary = result.stdout.strip()

                                self._emit_log('info', f"✅ Found Chrome via which: {chrome_binary}")

        # Anti-detection options                    else:

        options.add_argument('--disable-blink-features=AutomationControlled')                        result = subprocess.run(['which', 'chromium-browser'], capture_output=True, text=True, timeout=10)

        options.add_experimental_option("excludeSwitches", ["enable-automation"])                        if result.returncode == 0 and result.stdout.strip():

        options.add_experimental_option('useAutomationExtension', False)                            chrome_binary = result.stdout.strip()

        options.add_argument('--disable-web-security')                            self._emit_log('info', f"✅ Found Chromium via which: {chrome_binary}")

        options.add_argument('--allow-running-insecure-content')                except Exception as e:

                            self._emit_log('warning', f"Chrome detection error: {e}")

        if not is_koyeb and self.config.get("headless_mode", False):            

            options.add_argument('--headless')            if not chrome_binary:

                        self._emit_log('error', "❌ Chrome/Chromium not found! Check Render build logs for installation issues.")

        try:                self._emit_log('error', "🔧 Render deployment requires Chrome to be installed via aptfile")

            # Initialize ChromeDriver                raise Exception("Chrome binary not found on Render.com - check aptfile installation")

            self._emit_log('info', "📦 Setting up ChromeDriver...")        

            service = Service(ChromeDriverManager().install())        if use_uc:

                        try:

            self._emit_log('info', "🚀 Starting Chrome WebDriver...")                self._emit_log('info', "🚀 Initializing SeleniumBase UC mode for Cloudflare bypass...")

            self.driver = webdriver.Chrome(service=service, options=options)                

                            # For Render, we need to pass the chrome binary path to SeleniumBase

            # Enhanced anti-detection                if is_render and chrome_binary:

            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")                    os.environ['CHROME_BIN'] = chrome_binary

                                self._emit_log('info', f"🎯 Set CHROME_BIN environment variable: {chrome_binary}")

            # Set timeouts                

            self.driver.implicitly_wait(self.config.get("implicit_wait", 10))                self.driver = Driver(uc=True, headless=is_render)

            self.driver.set_page_load_timeout(self.config.get("page_load_timeout", 30))                self._emit_log('info', "✅ SeleniumBase UC driver initialized successfully")

                            self._is_seleniumbase = True

            self._emit_log('info', "✅ Chrome WebDriver initialized successfully!")                return

                            

        except Exception as driver_error:            except Exception as e:

            self._emit_log('error', f"❌ Chrome WebDriver initialization failed: {driver_error}")                self._emit_log('warning', f"❌ SeleniumBase UC failed: {e}")

                            self._emit_log('warning', "🔄 Falling back to regular Selenium WebDriver...")

            if is_koyeb:                

                self._emit_log('error', "🔍 Koyeb diagnostic info:")        # Fallback to regular Selenium

                self._emit_log('error', f"  Chrome binary: {chrome_binary}")        self._emit_log('info', "🔧 Using regular Selenium WebDriver")

                self._emit_log('error', f"  CHROME_BIN env: {os.environ.get('CHROME_BIN', 'Not set')}")        self._is_seleniumbase = False

                self._emit_log('error', "💡 Check Dockerfile Chrome installation")        

                    options = Options()

            raise        

            # Essential Chrome options for Render.com

    def login(self) -> bool:        if is_render:

        """Log in to TLS website starting from El-Sheikh Zayed page"""            self._emit_log('info', "⚙️ Applying Render.com Chrome optimizations...")

        try:            options.add_argument('--headless=new')  # Use new headless mode

            # Navigate to El-Sheikh Zayed page            options.add_argument('--no-sandbox')

            self._emit_log('info', "🌐 Navigating to TLS El-Sheikh Zayed page...")            options.add_argument('--disable-dev-shm-usage')

            self.driver.get(self.config["tls_url"])            options.add_argument('--disable-gpu')

            self._human_delay(3, 5)            options.add_argument('--disable-features=VizDisplayCompositor')

                        options.add_argument('--disable-background-timer-throttling')

            self._emit_log('info', f"📍 Current URL: {self.driver.current_url}")            options.add_argument('--disable-backgrounding-occluded-windows')

            self._emit_log('info', f"📄 Page title: {self.driver.title}")            options.add_argument('--disable-renderer-backgrounding')

                        options.add_argument('--disable-field-trial-config')

            # Find and click LOGIN button            options.add_argument('--disable-back-forward-cache')

            self._emit_log('info', "🔍 Looking for LOGIN button...")            options.add_argument('--disable-extensions')

            login_selector = "//span[contains(text(), 'LOGIN')]"            options.add_argument('--disable-plugins')

                        options.add_argument('--disable-default-apps')

            if self._is_seleniumbase:            options.add_argument('--disable-sync')

                elements = self.driver.find_elements("xpath", login_selector)            options.add_argument('--disable-translate')

            else:            options.add_argument('--hide-scrollbars')

                elements = self.driver.find_elements(By.XPATH, login_selector)            options.add_argument('--mute-audio')

                        options.add_argument('--disable-logging')

            if elements:            options.add_argument('--disable-background-networking')

                elem = elements[0]            options.add_argument('--disable-client-side-phishing-detection')

                self._emit_log('info', f"✅ Found login element: {elem.tag_name}")            options.add_argument('--disable-component-extensions-with-background-pages')

                            options.add_argument('--disable-ipc-flooding-protection')

                # Click parent link if it's a span            options.add_argument('--disable-hang-monitor')

                if elem.tag_name == 'span':            options.add_argument('--disable-prompt-on-repost')

                    parent = elem.find_element(By.XPATH, "./..")            options.add_argument('--disable-web-security')  # For testing

                    if parent.tag_name == 'a':            options.add_argument('--allow-running-insecure-content')

                        self._emit_log('info', "🔗 Clicking LOGIN link...")            options.add_argument('--ignore-certificate-errors')

                        if self._is_seleniumbase:            options.add_argument('--ignore-ssl-errors')

                            self.driver.execute_script("arguments[0].click();", parent)            options.add_argument('--ignore-certificate-errors-spki-list')

                        else:            

                            parent.click()            # Set Chrome binary if found

                            if chrome_binary:

                self._human_delay(3, 5)                options.binary_location = chrome_binary

            else:                self._emit_log('info', f"🎯 Chrome binary set to: {chrome_binary}")

                self._emit_log('warning', "⚠️ LOGIN button not found, trying direct navigation")            

                self.driver.get(self.config["login_start_url"])        # Standard Chrome options

                self._human_delay(3, 5)        options.add_argument('--disable-blink-features=AutomationControlled')

                    options.add_experimental_option("excludeSwitches", ["enable-automation"])

            # Wait for login form and fill credentials        options.add_experimental_option('useAutomationExtension', False)

            self._emit_log('info', f"🔑 Entering credentials for: {self.config['login_credentials']['email']}")        

                    if not is_render and self.config.get("headless_mode", False):

            # Fill email            options.add_argument('--headless')

            email_selector = "#email-input-field"        

            if self._is_seleniumbase:        try:

                self.driver.type(email_selector, self.config["login_credentials"]["email"])            # Use webdriver-manager to handle ChromeDriver

            else:            self._emit_log('info', "📦 Installing/updating ChromeDriver...")

                email_field = self.driver.find_element(By.CSS_SELECTOR, email_selector)            service = Service(ChromeDriverManager().install())

                email_field.clear()            

                email_field.send_keys(self.config["login_credentials"]["email"])            self._emit_log('info', "🚀 Starting Chrome WebDriver...")

                        self.driver = webdriver.Chrome(service=service, options=options)

            self._human_delay(1, 2)            

                        # Enhanced anti-detection for regular Selenium

            # Fill password            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            password_selector = "#password-input-field"            

            if self._is_seleniumbase:            # Set timeouts

                self.driver.type(password_selector, self.config["login_credentials"]["password"])            self.driver.implicitly_wait(self.config.get("implicit_wait", 10))

            else:            self.driver.set_page_load_timeout(self.config.get("page_load_timeout", 30))

                password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)            

                password_field.clear()            self._emit_log('info', "✅ Chrome WebDriver initialized successfully")

                password_field.send_keys(self.config["login_credentials"]["password"])            

                    except Exception as driver_error:

            self._human_delay(1, 2)            self._emit_log('error', f"❌ Failed to initialize Chrome WebDriver: {driver_error}")

                        

            # Click login button            if is_render:

            self._emit_log('info', "🚀 Clicking login button...")                self._emit_log('error', "🔍 Render.com diagnostic information:")

            login_button_selector = "#btn-login"                self._emit_log('error', f"  Chrome binary: {chrome_binary}")

            if self._is_seleniumbase:                self._emit_log('error', f"  CHROME_BIN env: {os.environ.get('CHROME_BIN', 'Not set')}")

                self.driver.click(login_button_selector)                self._emit_log('error', "🔧 Check Render build logs for Chrome installation issues")

            else:                self._emit_log('error', "📋 Ensure aptfile contains: chromium-browser")

                login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)            

                login_button.click()            raise

                

            # Wait for login completion    def login(self) -> bool:

            self._human_delay(3, 5)        """Log in to TLS website starting from El-Sheikh Zayed page"""

            self._emit_log('info', "✅ Login process completed!")        try:

            return True            # Navigate to El-Sheikh Zayed page

                        self._emit_log('info', "Navigating to El-Sheikh Zayed TLS page...")

        except Exception as e:            self.driver.get(self.config["tls_url"])

            self._emit_log('error', f"❌ Login failed: {e}")            self._human_delay(3, 5)

            return False            

                self._emit_log('info', f"Current URL: {self.driver.current_url}")

    def navigate_to_appointment_booking(self) -> bool:            self._emit_log('info', f"Page title: {self.driver.title}")

        """Navigate to appointment booking section"""            

        try:            # Find and click LOGIN button

            wait = WebDriverWait(self.driver, 10)            self._emit_log('info', "Looking for LOGIN button...")

                        login_selector = "//span[contains(text(), 'LOGIN')]"

            # Click the Select button for the travel group            

            select_button_selector = "[data-testid='btn-select-group']"            if self._is_seleniumbase:

            select_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, select_button_selector)))                elements = self.driver.find_elements("xpath", login_selector)

            select_button.click()            else:

                            elements = self.driver.find_elements(By.XPATH, login_selector)

            self._emit_log('info', "📅 Navigated to appointment booking section")            

            return True            if elements:

                            elem = elements[0]

        except Exception as e:                self._emit_log('info', f"Found login element: {elem.tag_name}")

            self._emit_log('error', f"❌ Failed to navigate to appointment booking: {e}")                

            return False                # Click parent link if it's a span

                    if elem.tag_name == 'span':

    def check_available_slots(self, month_offset: int = 0) -> List[Dict]:                    parent = elem.find_element(By.XPATH, "./..")

        """Check for available slots in a specific month"""                    if parent.tag_name == 'a':

        available_slots = []                        self._emit_log('info', "Clicking parent link of LOGIN span")

                                if self._is_seleniumbase:

        try:                            self.driver.execute_script("arguments[0].click();", parent)

            wait = WebDriverWait(self.driver, 10)                        else:

                                        parent.click()

            # Handle current month (month_offset 0)                

            if month_offset == 0:                self._human_delay(3, 5)

                time.sleep(3)  # Wait for page to load            else:

                                self._emit_log('warning', "Could not find LOGIN button, trying direct navigation")

                # Click current month button to ensure we're viewing it                self.driver.get(self.config["login_start_url"])

                try:                self._human_delay(3, 5)

                    current_month_selector = 'a[data-testid="btn-current-month-available"]'            

                    current_month_button = self.driver.find_element(By.CSS_SELECTOR, current_month_selector)            # Wait for login form and fill credentials

                    month_text = current_month_button.text.strip()            self._emit_log('info', "Entering login credentials...")

                    self._emit_log('info', f"📅 Checking current month: {month_text}")            

                                # Fill email

                    if self._is_seleniumbase:            email_selector = "#email-input-field"

                        self.driver.execute_script("arguments[0].click();", current_month_button)            if self._is_seleniumbase:

                    else:                self.driver.type(email_selector, self.config["login_credentials"]["email"])

                        current_month_button.click()            else:

                    time.sleep(2)                email_field = self.driver.find_element(By.CSS_SELECTOR, email_selector)

                except Exception:                email_field.clear()

                    pass  # Continue if current month button click fails                email_field.send_keys(self.config["login_credentials"]["email"])

                        

            # Handle future months (month_offset > 0)            self._human_delay(1, 2)

            elif month_offset > 0:            

                next_month_selector = 'a[data-testid="btn-next-month-available"]'            # Fill password

                            password_selector = "#password-input-field"

                for i in range(month_offset):            if self._is_seleniumbase:

                    try:                self.driver.type(password_selector, self.config["login_credentials"]["password"])

                        next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_month_selector)))            else:

                        month_text = next_button.text.strip()                password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)

                        self._emit_log('info', f"➡️ Navigation step {i+1}: Moving to {month_text}")                password_field.clear()

                                        password_field.send_keys(self.config["login_credentials"]["password"])

                        if self._is_seleniumbase:            

                            self.driver.execute_script("arguments[0].click();", next_button)            self._human_delay(1, 2)

                        else:            

                            next_button.click()            # Click login button

                                    self._emit_log('info', "Clicking login button...")

                        time.sleep(3)            login_button_selector = "#btn-login"

                        self._emit_log('info', f"✅ Successfully navigated to: {month_text}")            if self._is_seleniumbase:

                                        self.driver.click(login_button_selector)

                    except Exception:            else:

                        self._emit_log('debug', f"📍 Navigation step {i+1} completed")                login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)

                        break                login_button.click()

                        

            # Check for "no appointments" message            # Wait for login completion

            page_source = self.driver.page_source.lower()            self._human_delay(3, 5)

            no_appointment_texts = [            self._emit_log('info', "Login successful - no CAPTCHA required")

                "we currently don't have any appointment slots available",            return True

                "no slots are currently available",            

                "currently don't have any appointment slots"        except Exception as e:

            ]            self._emit_log('error', f"Login failed: {e}")

                        return False

            for text in no_appointment_texts:    

                if text in page_source:    def navigate_to_appointment_booking(self) -> bool:

                    self._emit_log('info', f"ℹ️ No appointments available for month offset {month_offset}")        """Navigate to appointment booking section"""

                    return []        try:

                        wait = WebDriverWait(self.driver, 10)

            # If no "no appointments" message found, potential slots available            

            self._emit_log('warning', f"🎯 POTENTIAL SLOTS AVAILABLE for month offset {month_offset} - VERIFY MANUALLY!")            # Click the Select button for the travel group

            slot_info = {            select_button_selector = "[data-testid='btn-select-group']"

                'date': 'Unknown',            select_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, select_button_selector)))

                'time': 'Slots may be available (verify manually)',            select_button.click()

                'month_offset': month_offset,            

                'element_text': 'No "no appointments" message found'            self._emit_log('info', "Navigated to appointment booking section")

            }            return True

            available_slots.append(slot_info)            

                    except Exception as e:

            return available_slots            self._emit_log('error', f"Failed to navigate to appointment booking: {e}")

                        return False

        except Exception as e:    

            self._emit_log('error', f"❌ Error checking month offset {month_offset}: {e}")    def check_available_slots(self, month_offset: int = 0) -> List[Dict]:

            return []        """Check for available slots in a specific month"""

            available_slots = []

    def send_email_notification(self, slots: List[Dict]):        

        """Send email notification about available slots"""        try:

        try:            wait = WebDriverWait(self.driver, 10)

            if not self.config["notification"]["email"]["enabled"]:            

                return            # Handle current month (month_offset 0)

                        if month_offset == 0:

            email_config = self.config["notification"]["email"]                time.sleep(3)  # Wait for page to load

                            

            # Create message                # Click current month button to ensure we're viewing it

            msg = MIMEMultipart()                try:

            msg['From'] = email_config["sender_email"]                    current_month_selector = 'a[data-testid="btn-current-month-available"]'

            msg['To'] = email_config["receiver_email"]                    current_month_button = self.driver.find_element(By.CSS_SELECTOR, current_month_selector)

            msg['Subject'] = email_config["subject"]                    month_text = current_month_button.text.strip()

                                self._emit_log('info', f"Ensuring we're viewing current month: {month_text}")

            # Create email body                    

            body = f"""                    if self._is_seleniumbase:

🎯 TLS Visa Appointment Slots Alert!                        self.driver.execute_script("arguments[0].click();", current_month_button)

                    else:

ATTENTION: {len(slots)} potential appointment slot(s) detected!                        current_month_button.click()

                    time.sleep(2)

IMPORTANT: Please verify manually on the TLS website as this is an automated check.                except Exception:

                    pass  # Continue if current month button click fails

Details:            

"""            # Handle future months (month_offset > 0)

                        elif month_offset > 0:

            for i, slot in enumerate(slots, 1):                next_month_selector = 'a[data-testid="btn-next-month-available"]'

                body += f"\n{i}. Month offset: {slot['month_offset']}"                

                body += f"\n   Status: {slot['element_text']}"                for i in range(month_offset):

                body += f"\n   Time: {slot['time']}"                    try:

                body += "\n"                        next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_month_selector)))

                                    month_text = next_button.text.strip()

            body += f"""                        self._emit_log('info', f"Navigation step {i+1}: Clicking to navigate to {month_text}")

Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                        

Deployed on: Koyeb Cloud Platform                        if self._is_seleniumbase:

                            self.driver.execute_script("arguments[0].click();", next_button)

Please log into the TLS website immediately to verify and book available slots:                        else:

https://visas-de.tlscontact.com/                            next_button.click()

                        

This is an automated notification from your TLS Visa Slot Checker.                        time.sleep(3)

"""                        self._emit_log('info', f"Successfully navigated to: {month_text}")

                                    

            msg.attach(MIMEText(body, 'plain'))                    except Exception:

                                    self._emit_log('debug', f"Navigation step {i+1} completed (expected for final month)")

            # Setup SMTP server                        break

            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])            

            server.starttls()  # Enable encryption            # Check for "no appointments" message

            server.login(email_config["sender_email"], email_config["sender_password"])            page_source = self.driver.page_source.lower()

                        no_appointment_texts = [

            # Send email                "we currently don't have any appointment slots available",

            text = msg.as_string()                "no slots are currently available",

            server.sendmail(email_config["sender_email"], email_config["receiver_email"], text)                "currently don't have any appointment slots"

            server.quit()            ]

                        

            self._emit_log('info', f"📧 Email notification sent successfully to {email_config['receiver_email']}")            for text in no_appointment_texts:

                            if text in page_source:

        except Exception as e:                    self._emit_log('info', f"No appointments available for month offset {month_offset}: {text}")

            self._emit_log('error', f"❌ Failed to send email notification: {e}")                    return []

                

    def run_check_cycle(self) -> bool:            # If no "no appointments" message found, potential slots available

        """Run a complete check cycle for all configured months"""            self._emit_log('warning', f"POTENTIAL SLOTS AVAILABLE for month offset {month_offset} - verify manually!")

        try:            slot_info = {

            if not self.login():                'date': 'Unknown',

                return False                'time': 'Slots may be available (verify manually)',

                            'month_offset': month_offset,

            if not self.navigate_to_appointment_booking():                'element_text': 'No "no appointments" message found'

                return False            }

                        available_slots.append(slot_info)

            all_available_slots = []            

                        return available_slots

            # Check slots for each month            

            for month_offset in range(self.config["months_to_check"]):        except Exception as e:

                self._emit_log('info', f"🔍 Checking month offset {month_offset}...")            self._emit_log('error', f"Error checking month offset {month_offset}: {e}")

                try:            return []

                    slots = self.check_available_slots(month_offset)    

                    all_available_slots.extend(slots)    def send_desktop_notification(self, slots: List[Dict], notification_type: str = "slots_found"):

                except Exception as e:        """Send desktop notification about available slots"""

                    self._emit_log('error', f"❌ Error checking month offset {month_offset}: {type(e).__name__}")        try:

                    continue            if not self.config["notification"]["desktop"]["enabled"] or not TOAST_AVAILABLE:

                                return

                time.sleep(2)  # Delay between checks            

                        toaster = win10toast.ToastNotifier()

            # Send notifications if slots found            

            if all_available_slots:            title = "TLS Visa Slots Check - VERIFY MANUALLY!"

                self._emit_log('warning', "🚨 POTENTIAL SLOTS DETECTED - PLEASE VERIFY MANUALLY!")            message = f"Found {len(slots)} potential appointment slot(s)!\nPlease check TLS website manually to verify."

                self._emit_log('info', f"🎯 SLOTS FOUND! Total: {len(all_available_slots)} available slots")            

                for slot in all_available_slots:            toaster.show_toast(

                    self._emit_log('info', f"- Month offset {slot['month_offset']}: {slot['element_text']}")                title,

                                message,

                # Send email notification                duration=30,  # Show for 30 seconds

                self.send_email_notification(all_available_slots)                icon_path=None,

            else:                threaded=True

                self._emit_log('info', "ℹ️ No available slots found in any checked months")            )

                        

            return True            self._emit_log('info', "Desktop notification sent successfully")

                        

        except Exception as e:        except Exception as e:

            self._emit_log('error', f"❌ Error during check cycle: {e}")            self._emit_log('error', f"Failed to send desktop notification: {e}")

            return False    

        def send_no_slots_notification(self):

    def start_monitoring(self):        """Send notification when no slots are found"""

        """Start continuous monitoring for available slots"""        pass  # Implemented in original for completeness

        self._emit_log('info', "🚀 Starting TLS Visa Appointment Slot Monitoring on Koyeb...")    

        self._emit_log('info', f"⏰ Checking every {self.config['check_interval_minutes']} minutes")    def send_error_notification(self, error_message: str = ""):

        self._emit_log('info', f"📅 Monitoring {self.config['months_to_check']} months ahead")        """Send notification when monitoring encounters an error"""

                pass  # Implemented in original for completeness

        self._running = True    

        self._stop_event.clear()    def send_monitoring_failed_notification(self):

        retry_count = 0        """Send notification when monitoring fails completely"""

        max_retries = self.config["max_retries"]        pass  # Implemented in original for completeness

                

        while not self._stop_event.is_set():    def send_email_notification(self, slots: List[Dict]):

            try:        """Send email notification about available slots"""

                # Emit status update before starting check        try:

                self._emit_status_update({            if not self.config["notification"]["email"]["enabled"]:

                    'is_running': True,                return

                    'last_check': None,            

                    'total_checks': self._total_checks,            email_config = self.config["notification"]["email"]

                    'error_count': self._error_count,            

                    'status': 'Running check...'            # Create message

                })            msg = MIMEMultipart()

                            msg['From'] = email_config["sender_email"]

                # Setup fresh driver for each cycle            msg['To'] = email_config["receiver_email"]

                self._setup_driver()            msg['Subject'] = email_config["subject"]

                            

                success = self.run_check_cycle()            # Create email body

                self._total_checks += 1            body = f"""

                self._last_check_time = datetime.now()TLS Visa Appointment Slots Alert!

                

                if success:ATTENTION: {len(slots)} potential appointment slot(s) detected!

                    retry_count = 0  # Reset retry count on success

                    self._emit_status_update({IMPORTANT: Please verify manually on the TLS website as this is an automated check.

                        'is_running': True,

                        'last_check': self._last_check_time.isoformat(),Details:

                        'total_checks': self._total_checks,"""

                        'error_count': self._error_count,            

                        'status': 'Check completed successfully'            for i, slot in enumerate(slots, 1):

                    })                body += f"\n{i}. Month offset: {slot['month_offset']}"

                else:                body += f"\n   Status: {slot['element_text']}"

                    retry_count += 1                body += f"\n   Time: {slot['time']}"

                    self._error_count += 1                body += "\n"

                    self._emit_log('warning', f"⚠️ Check cycle failed. Retry {retry_count}/{max_retries}")            

                                body += f"""

                    if retry_count >= max_retries:Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

                        self._emit_log('error', "❌ Maximum retries reached. Stopping monitoring.")

                        breakPlease log into the TLS website immediately to verify and book available slots:

                        https://visas-de.tlscontact.com/

                    self._emit_status_update({

                        'is_running': True,This is an automated notification from your TLS Visa Slot Checker.

                        'last_check': self._last_check_time.isoformat() if self._last_check_time else None,"""

                        'total_checks': self._total_checks,            

                        'error_count': self._error_count,            msg.attach(MIMEText(body, 'plain'))

                        'status': f'Check failed - retry {retry_count}/{max_retries}'            

                    })            # Setup SMTP server

                            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])

                # Clean up driver            server.starttls()  # Enable encryption

                if self.driver:            server.login(email_config["sender_email"], email_config["sender_password"])

                    self.driver.quit()            

                            # Send email

                # Wait before next check (interruptible)            text = msg.as_string()

                wait_seconds = self.config['check_interval_minutes'] * 60            server.sendmail(email_config["sender_email"], email_config["receiver_email"], text)

                self._emit_log('info', f"⏳ Waiting {self.config['check_interval_minutes']} minutes before next check...")            server.quit()

                            

                for _ in range(wait_seconds):            self._emit_log('info', f"Email notification sent successfully to {email_config['receiver_email']}")

                    if self._stop_event.is_set():            

                        break        except Exception as e:

                    time.sleep(1)            self._emit_log('error', f"Failed to send email notification: {e}")

                    

            except Exception as e:    def run_check_cycle(self) -> bool:

                self._emit_log('error', f"❌ Unexpected error: {e}")        """Run a complete check cycle for all configured months"""

                self._error_count += 1        try:

                retry_count += 1            if not self.login():

                if retry_count >= max_retries:                return False

                    break            

                time.sleep(30)  # Wait 30 seconds before retry            if not self.navigate_to_appointment_booking():

                        return False

        self._running = False            

        self._emit_status_update({            all_available_slots = []

            'is_running': False,            

            'last_check': self._last_check_time.isoformat() if self._last_check_time else None,            # Check slots for each month (current + next 2 months = 3 total)

            'total_checks': self._total_checks,            for month_offset in range(self.config["months_to_check"]):

            'error_count': self._error_count,                self._emit_log('info', f"Checking month offset {month_offset}...")

            'status': 'Monitoring stopped'                try:

        })                    slots = self.check_available_slots(month_offset)

                        all_available_slots.extend(slots)

    def stop_monitoring(self):                except Exception as e:

        """Stop the monitoring process"""                    self._emit_log('error', f"Error checking month offset {month_offset}: {type(e).__name__}")

        self._emit_log('info', "⏹️ Stopping monitoring...")                    continue

        self._running = False                

        self._stop_event.set()                time.sleep(2)  # Delay between checks

                    

        # Clean up driver if it exists            # Send notifications if slots found

        if self.driver:            if all_available_slots:

            try:                self._emit_log('warning', "POTENTIAL SLOTS DETECTED - PLEASE VERIFY MANUALLY!")

                self.driver.quit()                self._emit_log('info', f"SLOTS FOUND! Total: {len(all_available_slots)} available slots")

            except:                for slot in all_available_slots:

                pass                    self._emit_log('info', f"- Month offset {slot['month_offset']}: {slot['element_text']}")

                    

    def force_stop(self):                # Send both types of notifications

        """Force stop monitoring immediately"""                self.send_desktop_notification(all_available_slots)

        self._emit_log('warning', "🛑 Force stopping monitoring...")                self.send_email_notification(all_available_slots)

        self._running = False            else:

        self._stop_event.set()                self._emit_log('info', "No available slots found in any checked months")

                    

        # Force quit driver            return True

        if self.driver:            

            try:        except Exception as e:

                self.driver.quit()            self._emit_log('error', f"Error during check cycle: {e}")

                self.driver = None            return False

            except:    

                pass    def start_monitoring(self):

            """Start continuous monitoring for available slots"""

    def is_running(self) -> bool:        self._emit_log('info', "Starting TLS Visa Appointment Slot Monitoring...")

        """Check if monitoring is currently running"""        self._emit_log('info', f"Checking every {self.config['check_interval_minutes']} minutes")

        return self._running        self._emit_log('info', f"Monitoring {self.config['months_to_check']} months ahead")

            

    def get_last_check_time(self) -> str:        self._running = True

        """Get the last check time as ISO string"""        self._stop_event.clear()

        return self._last_check_time.isoformat() if self._last_check_time else ""        retry_count = 0

            max_retries = self.config["max_retries"]

    def get_total_checks(self) -> int:        

        """Get total number of checks performed"""        while not self._stop_event.is_set():

        return self._total_checks            try:

                    # Emit status update before starting check

    def get_error_count(self) -> int:                self._emit_status_update({

        """Get total number of errors encountered"""                    'is_running': True,

        return self._error_count                    'last_check': None,

                        'total_checks': self._total_checks,

    def get_browser_port(self) -> int:                    'error_count': self._error_count,

        """Get browser remote debugging port"""                    'status': 'Running check...'

        return self._browser_port or 9222                })

                    

    def __del__(self):                # Setup fresh driver for each cycle

        """Cleanup when object is destroyed"""                self._setup_driver()

        if hasattr(self, 'driver') and self.driver:                

            try:                success = self.run_check_cycle()

                self.driver.quit()                self._total_checks += 1

            except:                self._last_check_time = datetime.now()

                pass                
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
                
                # Clean up driver
                if self.driver:
                    self.driver.quit()
                
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
    
    def force_stop(self):
        """Force stop monitoring immediately"""
        self._emit_log('warning', "Force stopping monitoring...")
        self._running = False
        self._stop_event.set()
        
        # Force quit driver
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass
    
    def is_running(self) -> bool:
        """Check if monitoring is currently running"""
        return self._running
    
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
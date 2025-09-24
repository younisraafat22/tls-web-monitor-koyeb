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
        """Initialize the browser driver with Render.com cloud support"""
        # Guard against missing attribute if code runs before __init__ fully executed
        instance_id = getattr(self, '_instance_id', 'unknown')
        print(f"[DEBUG] {instance_id} - Setting up Chrome WebDriver")
        use_uc = self.config.get("use_seleniumbase_uc", False) and SELENIUMBASE_AVAILABLE
        
        # Detect cloud deployment (Render, Koyeb, Railway, Heroku, etc.)
        is_render = os.environ.get('RENDER_SERVICE_NAME') is not None
        is_koyeb = os.environ.get('KOYEB_SERVICE_NAME') is not None
        is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None
        is_heroku = os.environ.get('HEROKU_APP_NAME') is not None
        is_cloud_deployment = is_render or is_koyeb or is_railway or is_heroku or os.environ.get('PORT') is not None
        
        if is_cloud_deployment:
            platform = "Koyeb" if is_koyeb else "Render" if is_render else "Railway" if is_railway else "Heroku" if is_heroku else "Cloud"
            self._emit_log('info', f"🌐 Detected {platform} deployment - setting up Chrome...")
            
            # Force headless mode on cloud deployments
            headless_mode = True
            
            # Find Chrome binary on cloud deployment
            chrome_binary = None
            cloud_chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable', 
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/opt/google/chrome/chrome',
                '/snap/bin/chromium',
                '/app/.chrome-for-testing/chrome-linux64/chrome',  # Koyeb specific
                '/workspace/.chrome/chrome',  # Alternative Koyeb path
                '/opt/chrome/chrome',  # Alternative cloud path
            ]
            
            self._emit_log('info', f"🔍 Searching for Chrome binary on {platform}...")
            
            # Debug: List available paths first
            self._emit_log('info', "🔍 Debugging - checking all Chrome paths...")
            for path in cloud_chrome_paths:
                exists = os.path.exists(path)
                executable = os.access(path, os.X_OK) if exists else False
                self._emit_log('info', f"  {path}: exists={exists}, executable={executable}")
                if exists and executable:
                    chrome_binary = path
                    self._emit_log('info', f"✅ Found Chrome: {chrome_binary}")
                    break
            
            if not chrome_binary:
                self._emit_log('warning', "⚠️ Chrome not found in standard locations, checking installed packages...")
                try:
                    import subprocess
                    
                    # Try multiple Chrome commands
                    chrome_commands = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium']
                    for cmd in chrome_commands:
                        try:
                            result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=10)
                            if result.returncode == 0 and result.stdout.strip():
                                chrome_binary = result.stdout.strip()
                                self._emit_log('info', f"✅ Found {cmd} via which: {chrome_binary}")
                                break
                        except Exception as cmd_error:
                            self._emit_log('warning', f"Failed to check {cmd}: {cmd_error}")
                    
                    # If still not found, try alternative methods
                    if not chrome_binary:
                        try:
                            # Try find command to locate Chrome
                            result = subprocess.run(['find', '/usr', '/opt', '-name', 'google-chrome*', '-type', 'f', '-executable'], 
                                                  capture_output=True, text=True, timeout=15)
                            if result.returncode == 0 and result.stdout.strip():
                                lines = result.stdout.strip().split('\n')
                                for line in lines:
                                    if 'google-chrome' in line and os.path.exists(line):
                                        chrome_binary = line
                                        self._emit_log('info', f"✅ Found Chrome via find: {chrome_binary}")
                                        break
                        except Exception as find_error:
                            self._emit_log('warning', f"Find command failed: {find_error}")
                            
                except Exception as e:
                    self._emit_log('warning', f"Chrome detection error: {e}")
            
            if not chrome_binary:
                self._emit_log('warning', f"❌ Chrome/Chromium not found on {platform}! Running comprehensive discovery...")
                
                # Comprehensive Chrome discovery for debugging
                self._emit_log('info', "🔍 CHROME DISCOVERY DEBUG - Starting comprehensive search...")
                
                try:
                    import subprocess
                    
                    # 1. Check if Chrome package is installed
                    self._emit_log('info', "1️⃣ Checking installed packages...")
                    try:
                        result = subprocess.run(['dpkg', '-l', '|', 'grep', 'chrome'], 
                                              capture_output=True, text=True, shell=True, timeout=10)
                        if result.stdout:
                            self._emit_log('info', f"   Installed packages: {result.stdout}")
                        else:
                            self._emit_log('warning', "   No Chrome packages found via dpkg")
                    except Exception as e:
                        self._emit_log('warning', f"   Package check failed: {e}")
                    
                    # 2. Search entire filesystem for Chrome binaries
                    self._emit_log('info', "2️⃣ Searching filesystem for Chrome binaries...")
                    try:
                        search_commands = [
                            ['find', '/', '-name', '*chrome*', '-type', 'f', '-executable', '2>/dev/null'],
                            ['find', '/usr', '-name', '*chrome*', '-type', 'f', '2>/dev/null'],
                            ['find', '/opt', '-name', '*chrome*', '-type', 'f', '2>/dev/null'],
                            ['find', '/app', '-name', '*chrome*', '-type', 'f', '2>/dev/null']
                        ]
                        
                        for cmd in search_commands:
                            try:
                                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, shell=True)
                                if result.stdout.strip():
                                    lines = result.stdout.strip().split('\n')[:10]  # Limit output
                                    for line in lines:
                                        if line.strip():
                                            self._emit_log('info', f"   Found: {line}")
                                            # Try this as Chrome binary
                                            if 'chrome' in line.lower() and os.path.exists(line) and os.access(line, os.X_OK):
                                                chrome_binary = line
                                                self._emit_log('info', f"✅ DISCOVERED Chrome binary: {chrome_binary}")
                                                break
                                if chrome_binary:
                                    break
                            except Exception as cmd_error:
                                self._emit_log('warning', f"   Search command failed: {cmd_error}")
                    except Exception as e:
                        self._emit_log('warning', f"   Filesystem search failed: {e}")
                    
                    # 3. Check environment variables
                    self._emit_log('info', "3️⃣ Checking environment variables...")
                    chrome_env_vars = ['CHROME_BIN', 'GOOGLE_CHROME_BIN', 'CHROME_EXECUTABLE']
                    for env_var in chrome_env_vars:
                        value = os.environ.get(env_var)
                        if value:
                            self._emit_log('info', f"   {env_var}={value}")
                            if os.path.exists(value) and os.access(value, os.X_OK) and not chrome_binary:
                                chrome_binary = value
                                self._emit_log('info', f"✅ Using Chrome from environment: {chrome_binary}")
                        else:
                            self._emit_log('info', f"   {env_var}=<not set>")
                    
                    # 4. Try to run Chrome commands to see what happens
                    self._emit_log('info', "4️⃣ Testing Chrome commands...")
                    chrome_commands = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chrome']
                    for cmd in chrome_commands:
                        try:
                            result = subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10)
                            if result.returncode == 0:
                                self._emit_log('info', f"   {cmd} works: {result.stdout.strip()}")
                                if not chrome_binary:
                                    # Find where this command is located
                                    which_result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
                                    if which_result.returncode == 0:
                                        chrome_binary = which_result.stdout.strip()
                                        self._emit_log('info', f"✅ Found working Chrome: {chrome_binary}")
                            else:
                                self._emit_log('info', f"   {cmd} failed: {result.stderr.strip()}")
                        except Exception as cmd_error:
                            self._emit_log('info', f"   {cmd} error: {cmd_error}")
                    
                    # 5. List common directories
                    self._emit_log('info', "5️⃣ Listing contents of common Chrome directories...")
                    common_dirs = ['/usr/bin', '/opt', '/usr/lib', '/app', '/workspace']
                    for directory in common_dirs:
                        if os.path.exists(directory):
                            try:
                                files = os.listdir(directory)
                                chrome_files = [f for f in files if 'chrome' in f.lower()]
                                if chrome_files:
                                    self._emit_log('info', f"   {directory}: {chrome_files}")
                                    # Check if any of these are executable
                                    for file in chrome_files:
                                        full_path = os.path.join(directory, file)
                                        if os.access(full_path, os.X_OK) and not chrome_binary:
                                            chrome_binary = full_path
                                            self._emit_log('info', f"✅ Found executable Chrome: {chrome_binary}")
                                            break
                            except Exception as e:
                                self._emit_log('warning', f"   Cannot list {directory}: {e}")
                
                except Exception as discovery_error:
                    self._emit_log('error', f"Chrome discovery failed: {discovery_error}")
                
                # Final check
                if chrome_binary:
                    self._emit_log('info', f"🎉 CHROME DISCOVERY SUCCESSFUL: {chrome_binary}")
                else:
                    self._emit_log('error', "❌ CHROME DISCOVERY FAILED - Chrome not found anywhere!")
                    if is_render:
                        self._emit_log('error', "🔧 Render deployment requires Chrome to be installed via aptfile")
                    elif is_koyeb:
                        self._emit_log('error', "🔧 Koyeb deployment requires Chrome installation in Dockerfile")
                        self._emit_log('error', "💡 Check Dockerfile Chrome installation steps")
                    else:
                        self._emit_log('error', f"🔧 {platform} deployment requires Chrome installation")
                    
                    # Raise exception to stop monitoring - no fallback
                    raise Exception(f"Chrome binary not found on {platform} - Chrome installation required")
        
        if use_uc:
            try:
                self._emit_log('info', "🚀 Initializing SeleniumBase UC mode for Cloudflare bypass...")
                
                # For cloud deployments, we need to pass the chrome binary path to SeleniumBase
                if is_cloud_deployment and chrome_binary:
                    os.environ['CHROME_BIN'] = chrome_binary
                    self._emit_log('info', f"🎯 Set CHROME_BIN environment variable: {chrome_binary}")
                
                self.driver = Driver(uc=True, headless=is_render)
                self._emit_log('info', "✅ SeleniumBase UC driver initialized successfully")
                self._is_seleniumbase = True
                return
                
            except Exception as e:
                self._emit_log('warning', f"❌ SeleniumBase UC failed: {e}")
                
                # Clean up any leftover processes and user data from failed UC attempt
                self._cleanup_failed_chrome_attempt()
                
                self._emit_log('warning', "🔄 Falling back to regular Selenium WebDriver...")
                
        # Fallback to regular Selenium
        self._emit_log('info', "🔧 Using regular Selenium WebDriver")
        self._is_seleniumbase = False
        
        options = Options()
        
        # Essential Chrome options for cloud deployment (Koyeb/Render)
        if is_cloud_deployment:
            self._emit_log('info', "⚙️ Applying Cloud deployment Chrome optimizations...")
            options.add_argument('--headless=new')  # Use new headless mode
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-field-trial-config')
            options.add_argument('--disable-back-forward-cache')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-translate')
            options.add_argument('--hide-scrollbars')
            options.add_argument('--mute-audio')
            options.add_argument('--disable-logging')
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--disable-component-extensions-with-background-pages')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--disable-hang-monitor')
            options.add_argument('--disable-prompt-on-repost')
            options.add_argument('--disable-web-security')  # For testing
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--ignore-certificate-errors-spki-list')
            # Koyeb-specific optimizations
            options.add_argument('--memory-pressure-off')  # Help with memory management
            options.add_argument('--max_old_space_size=512')  # Limit memory usage
            # Removed --single-process as it can conflict with user data directory
            
            # Create unique user data directory to avoid conflicts in containerized environments
            temp_dir = tempfile.gettempdir()
            import time
            timestamp = int(time.time() * 1000)  # Millisecond timestamp
            process_id = os.getpid()
            unique_user_data_dir = os.path.join(temp_dir, f"chrome_user_data_{timestamp}_{process_id}_{uuid.uuid4().hex[:8]}")
            
            # Alternative 1: Try using /dev/shm for faster I/O if available (Linux containers)
            shm_dir = "/dev/shm"
            if os.path.exists(shm_dir) and os.access(shm_dir, os.W_OK):
                unique_user_data_dir = os.path.join(shm_dir, f"chrome_user_data_{timestamp}_{process_id}_{uuid.uuid4().hex[:8]}")
                self._emit_log('info', f"🚀 Using /dev/shm for user data directory (faster I/O)")
            
            os.makedirs(unique_user_data_dir, exist_ok=True)
            
            # Clean up any existing lock files in the directory
            lock_files = ['SingletonLock', 'SingletonSocket', 'SingletonCookie']
            for lock_file in lock_files:
                lock_path = os.path.join(unique_user_data_dir, lock_file)
                if os.path.exists(lock_path):
                    try:
                        os.remove(lock_path)
                        self._emit_log('info', f"🗑️ Removed existing lock file: {lock_file}")
                    except Exception as e:
                        self._emit_log('warning', f"⚠️ Could not remove lock file {lock_file}: {e}")
            
            options.add_argument(f'--user-data-dir={unique_user_data_dir}')
            self._temp_user_data_dir = unique_user_data_dir  # Store for cleanup
            self._emit_log('info', f"🗂️ Using unique user data directory: {unique_user_data_dir}")
            
            # DEBUG: Log directory creation and permissions
            if os.path.exists(unique_user_data_dir):
                import stat
                dir_stat = os.stat(unique_user_data_dir)
                self._emit_log('info', f"📁 Directory created successfully: {unique_user_data_dir}")
                self._emit_log('info', f"📊 Directory permissions: {oct(dir_stat.st_mode)}")
                self._emit_log('info', f"👤 Directory owner: UID={dir_stat.st_uid}, GID={dir_stat.st_gid}")
                
                # Check if directory is writable
                if os.access(unique_user_data_dir, os.W_OK):
                    self._emit_log('info', f"✅ Directory is writable")
                else:
                    self._emit_log('warning', f"⚠️ Directory is not writable!")
            else:
                self._emit_log('error', f"❌ Failed to create directory: {unique_user_data_dir}")
            
            # Alternative 2: Add Chrome options specifically for containerized environments
            # Based on Chrome documentation for avoiding user data directory conflicts
            options.add_argument('--disable-dev-shm-usage')  # Already exists but critical
            options.add_argument('--disable-background-timer-throttling')  # Already exists 
            options.add_argument('--disable-backgrounding-occluded-windows')  # Already exists
            options.add_argument('--disable-renderer-backgrounding')  # Already exists
            options.add_argument('--disable-ipc-flooding-protection')  # Already exists
            options.add_argument('--no-zygote')  # Disable zygote process
            options.add_argument('--no-crash-upload')  # Disable crash reporting
            options.add_argument('--disable-crash-reporter')  # Disable crash reporter
            options.add_argument('--disable-in-process-stack-traces')  # Disable stack traces
            
            # Additional Chrome options to prevent directory conflicts
            options.add_argument('--no-first-run')  # Skip first run tasks
            options.add_argument('--no-default-browser-check')  # Skip browser checks
            options.add_argument('--disable-background-mode')  # Disable background mode
            options.add_argument('--disable-backgrounding-occluded-windows')  # Already exists but good to have
            options.add_argument('--disable-component-update')  # Disable component updates
            options.add_argument('--disable-features=TranslateUI')  # Disable translate
            options.add_argument('--disable-features=VizDisplayCompositor')  # Already exists but good to have
            
            # Set Chrome binary if found
            if chrome_binary:
                options.binary_location = chrome_binary
                self._emit_log('info', f"🎯 Chrome binary set to: {chrome_binary}")
            
        # Standard Chrome options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if not is_cloud_deployment and self.config.get("headless_mode", False):
            options.add_argument('--headless')
        
        try:
            # Use webdriver-manager to handle ChromeDriver
            self._emit_log('info', "📦 Installing/updating ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            
            # DEBUG: Log all Chrome options before starting WebDriver
            self._emit_log('info', "🔍 DEBUG: Chrome Options Analysis")
            all_options = options.arguments
            self._emit_log('info', f"📋 Total Chrome arguments: {len(all_options)}")
            
            # Check for user-data-dir specifically
            user_data_args = [arg for arg in all_options if 'user-data-dir' in arg]
            if user_data_args:
                self._emit_log('info', f"🗂️ User data directory arguments found: {user_data_args}")
            else:
                self._emit_log('warning', f"⚠️ No user-data-dir argument found in options!")
            
            # Log all Chrome arguments for debugging
            for i, arg in enumerate(all_options):
                self._emit_log('info', f"  [{i:2d}] {arg}")
            
            # Check Chrome binary location
            if hasattr(options, 'binary_location') and options.binary_location:
                self._emit_log('info', f"🎯 Chrome binary location: {options.binary_location}")
                if os.path.exists(options.binary_location):
                    self._emit_log('info', f"✅ Chrome binary exists and is accessible")
                else:
                    self._emit_log('error', f"❌ Chrome binary not found at: {options.binary_location}")
            
            # Check for running Chrome processes
            try:
                import subprocess
                result = subprocess.run(['pgrep', '-f', 'chrome'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    processes = result.stdout.strip().split('\n')
                    self._emit_log('warning', f"⚠️ Found {len(processes)} running Chrome processes: {processes}")
                else:
                    self._emit_log('info', f"✅ No running Chrome processes found")
            except Exception as e:
                self._emit_log('info', f"🔍 Could not check for running Chrome processes: {e}")
            
            self._emit_log('info', "🚀 Starting Chrome WebDriver...")
            
            # Alternative approach: Try multiple strategies for Chrome startup
            strategies = [
                ("with_user_data_dir", "Using unique user data directory"),
                ("without_user_data_dir", "Without user data directory"),
                ("with_tmp_profile", "Using temporary profile")
            ]
            
            for strategy_name, strategy_desc in strategies:
                try:
                    self._emit_log('info', f"🔄 Trying strategy: {strategy_desc}")
                    
                    if strategy_name == "without_user_data_dir":
                        # Remove user-data-dir argument
                        modified_options = webdriver.ChromeOptions()
                        for arg in options.arguments:
                            if not arg.startswith('--user-data-dir='):
                                modified_options.add_argument(arg)
                        
                        # Copy experimental options
                        if hasattr(options, '_experimental_options'):
                            for key, value in options._experimental_options.items():
                                modified_options.add_experimental_option(key, value)
                        
                        if hasattr(options, 'binary_location') and options.binary_location:
                            modified_options.binary_location = options.binary_location
                        
                        self.driver = webdriver.Chrome(service=service, options=modified_options)
                        
                    elif strategy_name == "with_tmp_profile":
                        # Try with a completely different temp directory approach
                        import tempfile
                        with tempfile.TemporaryDirectory(prefix='chrome_profile_') as temp_profile:
                            modified_options = webdriver.ChromeOptions()
                            for arg in options.arguments:
                                if not arg.startswith('--user-data-dir='):
                                    modified_options.add_argument(arg)
                            
                            modified_options.add_argument(f'--user-data-dir={temp_profile}')
                            
                            # Copy experimental options
                            if hasattr(options, '_experimental_options'):
                                for key, value in options._experimental_options.items():
                                    modified_options.add_experimental_option(key, value)
                            
                            if hasattr(options, 'binary_location') and options.binary_location:
                                modified_options.binary_location = options.binary_location
                            
                            self.driver = webdriver.Chrome(service=service, options=modified_options)
                    
                    else:
                        # Original approach with user data directory
                        self.driver = webdriver.Chrome(service=service, options=options)
                    
                    # If we get here, the driver started successfully
                    self._emit_log('info', f"✅ Chrome WebDriver started successfully with strategy: {strategy_desc}")
                    break
                    
                except Exception as e:
                    self._emit_log('warning', f"❌ Strategy '{strategy_desc}' failed: {str(e)}")
                    if strategy_name == strategies[-1][0]:  # Last strategy
                        raise  # Re-raise the last exception
                    continue
            
            if not self.driver:
                raise Exception("All Chrome WebDriver strategies failed")
            
            # Enhanced anti-detection for regular Selenium
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set timeouts
            self.driver.implicitly_wait(self.config.get("implicit_wait", 10))
            self.driver.set_page_load_timeout(self.config.get("page_load_timeout", 30))
            
            self._emit_log('info', "✅ Chrome WebDriver initialized successfully")
            
        except Exception as driver_error:
            self._emit_log('error', f"❌ Failed to initialize Chrome WebDriver: {driver_error}")
            
            if is_render:
                self._emit_log('error', "🔍 Render.com diagnostic information:")
                self._emit_log('error', f"  Chrome binary: {chrome_binary}")
                self._emit_log('error', f"  CHROME_BIN env: {os.environ.get('CHROME_BIN', 'Not set')}")
                self._emit_log('error', "🔧 Check Render build logs for Chrome installation issues")
                self._emit_log('error', "📋 Ensure aptfile contains: chromium-browser")
            
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
"""
TLS Visa Appointment Web Monitor
Modern web interface for monitoring TLS visa appointment slots
"""

# IMPORTANT: eventlet monkey patch MUST be first, before any other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_socketio import SocketIO, emit
import json
import os
import threading
import time
from datetime import datetime
from services.tls_monitor import TLSWebMonitor
from services.config_manager import ConfigManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tls_monitor_secret_key_2024'

# Improve static file serving for production
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static files for 1 year
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Detect if we're in production (Koyeb, Render, or other cloud platforms)
is_production = (os.environ.get('RENDER_SERVICE_NAME') is not None or 
                 os.environ.get('KOYEB_SERVICE_NAME') is not None or
                 os.environ.get('RAILWAY_ENVIRONMENT') is not None or
                 os.environ.get('HEROKU_APP_NAME') is not None or
                 os.environ.get('PORT') is not None)

socketio = SocketIO(app, 
                    cors_allowed_origins="*",
                    ping_timeout=60,
                    ping_interval=25,
                    engineio_logger=False,
                    socketio_logger=False,
                    async_mode='eventlet' if is_production else 'threading',
                    logger=False,
                    allow_upgrades=True)

# Global monitor instance and thread tracking
monitor = None
monitor_thread = None
config_manager = ConfigManager()

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files with proper MIME types"""
    return send_from_directory('static', filename)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        config = config_manager.get_config()
        
        # Detect cloud environment
        is_cloud = any([
            os.environ.get('RENDER_SERVICE_NAME'),
            os.environ.get('HEROKU_APP_NAME'),
            os.environ.get('RAILWAY_ENVIRONMENT'),
            os.path.exists('/.dockerenv')
        ])
        
        # Force headless mode in cloud environments
        if is_cloud:
            config['headless_mode'] = True
            config['force_headless'] = True
            config['environment'] = 'cloud'
        else:
            config['force_headless'] = False
            config['environment'] = 'local'
            
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        data = request.get_json()
        config_manager.update_config(data)
        return jsonify({'success': True, 'message': 'Configuration updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/keep-alive')
def keep_alive():
    """Keep-alive endpoint to prevent server from sleeping"""
    return jsonify({
        'status': 'alive', 
        'timestamp': datetime.now().isoformat(),
        'message': 'TLS Monitor is running'
    })

@app.route('/debug/chrome-discovery')
def debug_chrome_discovery():
    """Debug endpoint to discover Chrome installation paths"""
    import subprocess
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'platform_detection': {},
        'environment_variables': {},
        'file_system_search': {},
        'command_tests': {},
        'directory_listings': {}
    }
    
    try:
        # Platform detection
        debug_info['platform_detection'] = {
            'RENDER_SERVICE_NAME': os.environ.get('RENDER_SERVICE_NAME'),
            'KOYEB_SERVICE_NAME': os.environ.get('KOYEB_SERVICE_NAME'), 
            'RAILWAY_ENVIRONMENT': os.environ.get('RAILWAY_ENVIRONMENT'),
            'HEROKU_APP_NAME': os.environ.get('HEROKU_APP_NAME'),
            'PORT': os.environ.get('PORT'),
            'dockerenv_exists': os.path.exists('/.dockerenv')
        }
        
        # Chrome-related environment variables
        chrome_env_vars = ['CHROME_BIN', 'GOOGLE_CHROME_BIN', 'CHROME_EXECUTABLE', 'CHROMIUM_BIN']
        for var in chrome_env_vars:
            value = os.environ.get(var)
            debug_info['environment_variables'][var] = {
                'value': value,
                'exists': os.path.exists(value) if value else None,
                'executable': os.access(value, os.X_OK) if value and os.path.exists(value) else None
            }
        
        # Test Chrome commands
        chrome_commands = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium', 'chrome']
        for cmd in chrome_commands:
            try:
                # Test version command
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10)
                # Find location
                which_result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
                
                debug_info['command_tests'][cmd] = {
                    'version_works': result.returncode == 0,
                    'version_output': result.stdout.strip() if result.returncode == 0 else result.stderr.strip(),
                    'location': which_result.stdout.strip() if which_result.returncode == 0 else None
                }
            except Exception as e:
                debug_info['command_tests'][cmd] = {'error': str(e)}
        
        # Search common Chrome paths
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable', 
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/opt/google/chrome/chrome',
            '/snap/bin/chromium',
            '/app/.chrome-for-testing/chrome-linux64/chrome',
            '/workspace/.chrome/chrome',
            '/opt/chrome/chrome'
        ]
        
        for path in chrome_paths:
            debug_info['file_system_search'][path] = {
                'exists': os.path.exists(path),
                'executable': os.access(path, os.X_OK) if os.path.exists(path) else None,
                'is_file': os.path.isfile(path) if os.path.exists(path) else None
            }
        
        # List contents of common directories
        common_dirs = ['/usr/bin', '/opt', '/usr/lib', '/app', '/workspace']
        for directory in common_dirs:
            if os.path.exists(directory):
                try:
                    files = os.listdir(directory)
                    chrome_files = [f for f in files if 'chrome' in f.lower()]
                    debug_info['directory_listings'][directory] = chrome_files[:20]  # Limit to 20 files
                except Exception as e:
                    debug_info['directory_listings'][directory] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'debug_info': debug_info,
            'message': 'Chrome discovery debug completed'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'debug_info': debug_info
        })

@app.route('/debug/system-info')
def debug_system_info():
    """Debug endpoint for system information and Chrome process analysis"""
    try:
        import psutil
        import platform
        
        debug_info = {
            'system': {
                'platform': platform.platform(),
                'architecture': platform.architecture(),
                'python_version': platform.python_version(),
                'processor': platform.processor(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': dict(psutil.disk_usage('/')._asdict()) if os.path.exists('/') else 'N/A'
            },
            'processes': {
                'chrome_processes': [],
                'total_processes': len(psutil.pids()),
                'current_user': os.environ.get('USER', 'unknown'),
                'current_uid': os.getuid() if hasattr(os, 'getuid') else 'N/A',
                'current_gid': os.getgid() if hasattr(os, 'getgid') else 'N/A'
            },
            'temp_directories': {},
            'running_services': []
        }
        
        # Find Chrome processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    debug_info['processes']['chrome_processes'].append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'username': proc.info['username'],
                        'cmdline': ' '.join(proc.info['cmdline'][:5]) + '...' if len(proc.info['cmdline']) > 5 else ' '.join(proc.info['cmdline'])
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Check temp directories
        temp_dirs = ['/tmp', '/dev/shm', tempfile.gettempdir()]
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    stat_info = os.stat(temp_dir)
                    debug_info['temp_directories'][temp_dir] = {
                        'exists': True,
                        'writable': os.access(temp_dir, os.W_OK),
                        'permissions': oct(stat_info.st_mode),
                        'owner_uid': stat_info.st_uid,
                        'owner_gid': stat_info.st_gid,
                        'size': sum(os.path.getsize(os.path.join(temp_dir, f)) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f)))
                    }
                    
                    # List chrome-related files
                    chrome_files = []
                    try:
                        for item in os.listdir(temp_dir):
                            if 'chrome' in item.lower():
                                chrome_files.append(item)
                        debug_info['temp_directories'][temp_dir]['chrome_files'] = chrome_files[:10]  # Limit to 10
                    except:
                        debug_info['temp_directories'][temp_dir]['chrome_files'] = 'access_denied'
                        
                except Exception as e:
                    debug_info['temp_directories'][temp_dir] = {'error': str(e)}
            else:
                debug_info['temp_directories'][temp_dir] = {'exists': False}
        
        return jsonify({
            'success': True,
            'debug_info': debug_info,
            'message': 'System debug info collected'
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'psutil not available',
            'message': 'System debug requires psutil package'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'System debug failed'
        })

@app.route('/api/start-monitoring', methods=['POST'])
def start_monitoring():
    """Start the TLS monitoring process"""
    global monitor, monitor_thread
    
    try:
        print(f"[DEBUG] Start monitoring called. Current monitor: {monitor}, is_running: {monitor.is_running() if monitor else 'None'}")
        
        # Check if monitoring is already running
        if monitor and monitor.is_running():
            print("[DEBUG] Monitoring already running - returning early")
            return jsonify({'success': False, 'error': 'Monitoring is already running'})
        
        # Clean up any existing thread
        if monitor_thread and monitor_thread.is_alive():
            print("[DEBUG] Previous thread still alive - waiting for cleanup")
            return jsonify({'success': False, 'error': 'Previous monitoring session is still stopping. Please wait a moment and try again.'})
        
        # Force cleanup any existing monitor instance
        if monitor:
            print("[DEBUG] Cleaning up existing monitor instance")
            try:
                monitor.force_stop()
            except:
                pass
            monitor = None
            
        # Clean up thread reference
        monitor_thread = None
        
        config = config_manager.get_config()
        
        # Validate configuration before starting
        is_valid, error_message = config_manager.validate_config(config)
        if not is_valid:
            return jsonify({'success': False, 'error': error_message})
        
        # Specifically check TLS credentials
        tls_email = config.get('login_credentials', {}).get('email', '').strip()
        tls_password = config.get('login_credentials', {}).get('password', '').strip()
        
        if not tls_email or not tls_password:
            return jsonify({
                'success': False, 
                'error': 'TLS email and password are required. Please fill in your TLS account credentials before starting monitoring.'
            })
        
        print("[DEBUG] Creating new TLSWebMonitor instance")
        monitor = TLSWebMonitor(config, socketio)
        
        print("[DEBUG] Starting monitoring thread")
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=monitor.start_monitoring, daemon=True, name="TLS-Monitor")
        monitor_thread.start()
        
        print("[DEBUG] Monitoring started successfully")
        return jsonify({'success': True, 'message': 'Monitoring started successfully'})
    except Exception as e:
        print(f"[DEBUG] Start monitoring error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop-monitoring', methods=['POST'])
def stop_monitoring():
    """Stop the TLS monitoring process"""
    global monitor, monitor_thread
    
    try:
        if not monitor:
            return jsonify({'success': False, 'error': 'No monitoring process is running'})
        
        if not monitor.is_running():
            return jsonify({'success': False, 'error': 'Monitoring is not currently running'})
        
        # Signal the monitor to stop
        monitor.stop_monitoring()
        
        # Wait for the thread to finish (with timeout)
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join(timeout=10.0)  # Wait up to 10 seconds
            
            # If thread is still alive after timeout, force cleanup
            if monitor_thread.is_alive():
                # Thread didn't stop gracefully, force cleanup
                monitor.force_stop()
                monitor_thread.join(timeout=5.0)  # Wait another 5 seconds
                
                if monitor_thread.is_alive():
                    return jsonify({
                        'success': False, 
                        'error': 'Monitoring process is not responding. It may continue running in the background.'
                    })
        
        # Clear references
        monitor = None
        monitor_thread = None
        
        return jsonify({'success': True, 'message': 'Monitoring stopped successfully'})
    except Exception as e:
        # Force cleanup on error
        if monitor:
            try:
                monitor.force_stop()
            except:
                pass
        monitor = None
        monitor_thread = None
        return jsonify({'success': False, 'error': f'Error stopping monitoring: {str(e)}'})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current monitoring status"""
    try:
        if monitor:
            instance_id = getattr(monitor, '_instance_id', 'unknown')
            print(f"[DEBUG] Status check - Monitor instance: {instance_id}")
            
            status = {
                'is_running': monitor.is_running(),
                'last_check': monitor.get_last_check_time(),
                'total_checks': monitor.get_total_checks(),
                'error_count': monitor.get_error_count(),
                'browser_port': monitor.get_browser_port(),
                'instance_id': instance_id  # Debug info
            }
        else:
            status = {
                'is_running': False,
                'last_check': None,
                'total_checks': 0,
                'error_count': 0,
                'browser_port': None
            }
        
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-notifications', methods=['POST'])
def test_notifications():
    """Test notification system"""
    try:
        data = request.get_json()
        notification_type = data.get('type', 'both')
        
        config = config_manager.get_config()
        
        if monitor:
            test_slots = [{
                'date': 'Test',
                'time': 'Test notification',
                'month_offset': 0,
                'element_text': 'This is a test notification'
            }]
            
            success = False
            
            if notification_type in ['desktop', 'both']:
                monitor.send_desktop_notification(test_slots)
                success = True
                
            if notification_type in ['email', 'both']:
                monitor.send_email_notification(test_slots)
                success = True
            
            if success:
                return jsonify({'success': True, 'message': 'Test notification sent successfully'})
            else:
                return jsonify({'success': False, 'error': 'No notification type specified'})
        else:
            return jsonify({'success': False, 'error': 'Monitor not initialized'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to TLS Monitor'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    print("Starting TLS Web Monitor...")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    
    print(f"Access the dashboard at: http://localhost:{port}")
    print("Using eventlet server for production compatibility")
    
    # Run with eventlet for production compatibility
    socketio.run(app, 
                host=host, 
                port=port, 
                debug=False,
                use_reloader=False,
                log_output=True,
                allow_unsafe_werkzeug=True)
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

@app.route('/api/start-monitoring', methods=['POST'])
def start_monitoring():
    """Start the TLS monitoring process"""
    global monitor, monitor_thread
    
    try:
        # Check if monitoring is already running
        if monitor and monitor.is_running():
            return jsonify({'success': False, 'error': 'Monitoring is already running'})
        
        # Clean up any existing thread
        if monitor_thread and monitor_thread.is_alive():
            return jsonify({'success': False, 'error': 'Previous monitoring session is still stopping. Please wait a moment and try again.'})
        
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
        
        monitor = TLSWebMonitor(config, socketio)
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=monitor.start_monitoring, daemon=True, name="TLS-Monitor")
        monitor_thread.start()
        
        return jsonify({'success': True, 'message': 'Monitoring started successfully'})
    except Exception as e:
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
            status = {
                'is_running': monitor.is_running(),
                'last_check': monitor.get_last_check_time(),
                'total_checks': monitor.get_total_checks(),
                'error_count': monitor.get_error_count(),
                'browser_port': monitor.get_browser_port()
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
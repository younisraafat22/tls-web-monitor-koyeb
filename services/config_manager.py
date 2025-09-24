"""
Configuration Manager for TLS Web Monitor
Handles saving and loading user settings
"""

import json
import os
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.default_config = {
            # TLS Website URLs
            "tls_url": "https://visas-de.tlscontact.com/en-us/country/eg/vac/egCAI2de",
            "login_start_url": "https://visas-de.tlscontact.com/en-us/login",
            
            # Login Credentials (will be updated by user)
            "login_credentials": {
                "email": "",
                "password": ""
            },
            
            # Notification Settings
            "notification": {
                "desktop": {
                    "enabled": True
                },
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender_email": "younis.raafat2@gmail.com",  # Hardcoded sender email
                    "sender_password": "rnhi xzku xrtk vkyo",  # Hardcoded app password
                    "receiver_email": "",
                    "subject": "TLS Visa Slots Available!"
                }
            },
            
            # Monitoring Settings
            "check_interval_minutes": 15,
            "months_to_check": 3,
            "max_retries": 3,
            
            # Browser Settings
            "headless_mode": True,
            "use_seleniumbase_uc": True,
            "implicit_wait": 10,
            "page_load_timeout": 30,
            "remote_debugging_port": 9222
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Load configuration from file or return default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Merge with default config to ensure all keys exist
                merged_config = self._deep_merge(self.default_config.copy(), config)
                return merged_config
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration and save to file"""
        try:
            current_config = self.get_config()
            updated_config = self._deep_merge(current_config, new_config)
            
            # Always preserve hardcoded email credentials
            if 'notification' in updated_config and 'email' in updated_config['notification']:
                updated_config['notification']['email']['sender_email'] = "younis.raafat2@gmail.com"
                updated_config['notification']['email']['sender_password'] = "rnhi xzku xrtk vkyo"
                # Ensure other email settings from default config
                updated_config['notification']['email']['smtp_server'] = "smtp.gmail.com"
                updated_config['notification']['email']['smtp_port'] = 587
                updated_config['notification']['email']['subject'] = "TLS Visa Slots Available!"
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(updated_config, f, indent=2)
                
            print("Configuration updated successfully")
        except Exception as e:
            print(f"Error updating config: {e}")
            raise
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate configuration"""
        try:
            # Check required fields
            if not config.get('login_credentials', {}).get('email'):
                return False, "TLS email is required"
            
            if not config.get('login_credentials', {}).get('password'):
                return False, "TLS password is required"
            
            # Validate email notification settings if enabled
            email_config = config.get('notification', {}).get('email', {})
            if email_config.get('enabled', False):
                if not email_config.get('receiver_email'):
                    return False, "Receiver email is required when email notifications are enabled"
            
            # Validate numeric settings
            check_interval = config.get('check_interval_minutes', 0)
            if not isinstance(check_interval, (int, float)) or check_interval < 1:
                return False, "Check interval must be at least 1 minute"
            
            months_to_check = config.get('months_to_check', 0)
            if not isinstance(months_to_check, int) or months_to_check < 1:
                return False, "Months to check must be at least 1"
            
            return True, "Configuration is valid"
            
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
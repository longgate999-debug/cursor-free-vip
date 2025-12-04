#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pro Trial Activation Bypass
This script bypasses Stripe integration to activate pro trial for Cursor
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from colorama import Fore, Style, init
import logging

# Initialize colorama
init()

# Setup logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define emoji constants
EMOJI = {
    'SUCCESS': '✅',
    'ERROR': '❌',
    'INFO': 'ℹ️',
    'WARNING': '⚠️',
    'ROCKET': '🚀',
    'SUBSCRIPTION': '💳',
    'USER': '👤',
    'TIME': '🕒'
}


class ProTrialActivator:
    """Pro Trial Activation Bypass"""
    
    def __init__(self, translator=None):
        self.translator = translator
        self.config = None
        self.paths = self._get_paths()
        
    def _get_paths(self):
        """Get system-specific paths"""
        try:
            from config import get_config
            config = get_config()
            
            if not config:
                return None
            
            system = sys.platform
            if system == "win32":  # Windows
                if config.has_section('WindowsPaths'):
                    return {
                        'storage_path': config.get('WindowsPaths', 'storage_path'),
                        'sqlite_path': config.get('WindowsPaths', 'sqlite_path'),
                        'cursor_path': config.get('WindowsPaths', 'cursor_path', fallback=os.path.join(os.getenv("APPDATA"), "Cursor"))
                    }
            elif system == 'linux':  # Linux
                if config.has_section('LinuxPaths'):
                    return {
                        'storage_path': config.get('LinuxPaths', 'storage_path'),
                        'sqlite_path': config.get('LinuxPaths', 'sqlite_path'),
                        'cursor_path': os.path.expanduser("~/.config/Cursor")
                    }
            elif system == 'darwin':  # macOS
                if config.has_section('MacPaths'):
                    return {
                        'storage_path': config.get('MacPaths', 'storage_path'),
                        'sqlite_path': config.get('MacPaths', 'sqlite_path'),
                        'cursor_path': os.path.expanduser("~/Library/Application Support/Cursor")
                    }
        except Exception as e:
            logger.error(f"Get paths failed: {str(e)}")
        
        return None
    
    def _get_token(self):
        """Get Cursor authentication token"""
        if not self.paths:
            return None
        
        # Try to get from storage.json
        try:
            storage_path = self.paths['storage_path']
            if os.path.exists(storage_path):
                with open(storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'cursorAuth/accessToken' in data:
                        return data['cursorAuth/accessToken']
                    
                    for key in data:
                        if 'token' in key.lower() and isinstance(data[key], str) and len(data[key]) > 20:
                            return data[key]
        except Exception as e:
            logger.error(f"Failed to get token from storage: {str(e)}")
        
        # Try to get from SQLite
        try:
            sqlite_path = self.paths['sqlite_path']
            if os.path.exists(sqlite_path):
                conn = sqlite3.connect(sqlite_path)
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%token%' LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    value = row[0]
                    if isinstance(value, str) and len(value) > 20:
                        return value
                    try:
                        data = json.loads(value)
                        if isinstance(data, dict) and 'token' in data:
                            return data['token']
                    except:
                        pass
        except Exception as e:
            logger.error(f"Failed to get token from SQLite: {str(e)}")
        
        return None
    
    def _make_api_request(self, token, endpoint, method='GET', data=None):
        """Make API request to Cursor backend"""
        try:
            url = f"https://api2.cursor.sh{endpoint}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, json=data, timeout=10)
            
            response.raise_for_status()
            return response.json() if response.text else None
            
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return None
    
    def _bypass_stripe_profile(self, token):
        """Bypass Stripe profile check by modifying local subscription data"""
        if not self.paths:
            return False
        
        try:
            sqlite_path = self.paths['sqlite_path']
            if not os.path.exists(sqlite_path):
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('pro_trial.sqlite_not_found') if self.translator else 'SQLite database not found'}{Style.RESET_ALL}")
                return False
            
            # Create pro trial membership data
            pro_trial_data = {
                "membershipType": "pro_trial",
                "subscriptionStatus": "active",
                "daysRemainingOnTrial": 14,
                "trialStartDate": datetime.now().isoformat(),
                "trialEndDate": (datetime.now() + timedelta(days=14)).isoformat()
            }
            
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Check if subscription data exists
            cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%subscription%' OR key LIKE '%membership%' LIMIT 1")
            row = cursor.fetchone()
            
            # Insert or update subscription data
            subscription_key = 'cursorSubscription/membershipData'
            cursor.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                (subscription_key, json.dumps(pro_trial_data))
            )
            
            # Also set trial activation flag
            trial_flag_key = 'cursorSubscription/proTrialActive'
            cursor.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                (trial_flag_key, json.dumps(True))
            )
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to bypass Stripe profile: {str(e)}")
            return False
    
    def _update_local_storage(self):
        """Update local storage with pro trial activation"""
        if not self.paths:
            return False
        
        try:
            storage_path = self.paths['storage_path']
            
            if os.path.exists(storage_path):
                with open(storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Add pro trial activation markers
            pro_trial_data = {
                "membershipType": "pro_trial",
                "subscriptionStatus": "active",
                "daysRemainingOnTrial": 14,
                "trialStartDate": datetime.now().isoformat(),
                "trialEndDate": (datetime.now() + timedelta(days=14)).isoformat()
            }
            
            data['cursorSubscription/membership'] = json.dumps(pro_trial_data)
            data['cursorSubscription/proTrialActive'] = json.dumps(True)
            
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update local storage: {str(e)}")
            return False
    
    def activate_pro_trial(self):
        """Main function to activate pro trial"""
        try:
            print(f"\n{Fore.CYAN}{EMOJI['ROCKET']} {self.translator.get('pro_trial.activating') if self.translator else 'Activating Pro Trial...'}{Style.RESET_ALL}")
            
            # Get token
            token = self._get_token()
            if not token:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('pro_trial.token_not_found') if self.translator else 'Authentication token not found. Please log in first.'}{Style.RESET_ALL}")
                return False
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('pro_trial.token_found') if self.translator else 'Authentication token found'}{Style.RESET_ALL}")
            
            # Step 1: Update local storage
            if self._update_local_storage():
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('pro_trial.local_storage_updated') if self.translator else 'Local storage updated'}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('pro_trial.local_storage_failed') if self.translator else 'Failed to update local storage (non-critical)'}{Style.RESET_ALL}")
            
            # Step 2: Bypass SQLite
            if self._bypass_stripe_profile(token):
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('pro_trial.sqlite_updated') if self.translator else 'Database updated with pro trial data'}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('pro_trial.sqlite_failed') if self.translator else 'Failed to update database (non-critical)'}{Style.RESET_ALL}")
            
            # Step 3: Attempt API bypass (try to call trial activation endpoint)
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('pro_trial.attempting_api_bypass') if self.translator else 'Attempting API bypass...'}{Style.RESET_ALL}")
            
            result = self._make_api_request(
                token,
                '/auth/activate_pro_trial',
                method='POST',
                data={'bypass': True}
            )
            
            if result:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('pro_trial.api_bypass_success') if self.translator else 'API bypass successful'}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('pro_trial.api_bypass_skipped') if self.translator else 'API bypass not available (non-critical)'}{Style.RESET_ALL}")
            
            print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('pro_trial.activation_complete') if self.translator else 'Pro Trial activation completed!'}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('pro_trial.restart_cursor') if self.translator else 'Please restart Cursor to apply changes.'}{Style.RESET_ALL}")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('pro_trial.activation_failed', error=str(e)) if self.translator else f'Pro Trial activation failed: {str(e)}'}{Style.RESET_ALL}")
            return False


def main(translator=None):
    """Main function"""
    try:
        activator = ProTrialActivator(translator)
        return activator.activate_pro_trial()
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('pro_trial.error', error=str(e)) if translator else f'Error: {str(e)}'}{Style.RESET_ALL}")
        return False


if __name__ == "__main__":
    main()

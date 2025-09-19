"""
API Manager module for handling multiple Gemini API keys with failover and load balancing
"""

import time
import random
import logging
import asyncio
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
import google.generativeai as genai
from config import MAX_APIS, API_TIMEOUT, API_RETRY_ATTEMPTS, API_COOLDOWN

logger = logging.getLogger(__name__)

class APIStatus(Enum):
    ACTIVE = "active"
    FAILED = "failed" 
    COOLDOWN = "cooldown"
    DISABLED = "disabled"

@dataclass
class APIKey:
    id: str
    key: str
    name: str
    status: APIStatus
    last_used: float
    failure_count: int
    success_count: int
    total_requests: int
    last_error: str
    cooldown_until: float
    
    def is_available(self) -> bool:
        """Check if API key is available for use"""
        if self.status == APIStatus.DISABLED:
            return False
        
        if self.status == APIStatus.COOLDOWN:
            if time.time() > self.cooldown_until:
                self.status = APIStatus.ACTIVE
                return True
            return False
        
        return self.status == APIStatus.ACTIVE
    
    def mark_success(self):
        """Mark API as successful"""
        self.status = APIStatus.ACTIVE
        self.success_count += 1
        self.total_requests += 1
        self.last_used = time.time()
        self.failure_count = 0  # Reset failure count on success
    
    def mark_failure(self, error: str):
        """Mark API as failed"""
        self.failure_count += 1
        self.total_requests += 1
        self.last_error = error
        
        if self.failure_count >= API_RETRY_ATTEMPTS:
            self.status = APIStatus.COOLDOWN
            self.cooldown_until = time.time() + API_COOLDOWN
        else:
            self.status = APIStatus.FAILED

class APIManager:
    def __init__(self):
        self.api_keys: Dict[str, APIKey] = {}
        self.current_api_index = 0
        self._initialize_from_env()
    
    def _initialize_from_env(self):
        """Initialize with environment variable if available"""
        from config import GEMINI_API_KEY
        if GEMINI_API_KEY:
            self.add_api_key(GEMINI_API_KEY, "Environment")
    
    def add_api_key(self, api_key: str, name: str = None) -> Tuple[bool, str]:
        """Add a new API key"""
        if len(self.api_keys) >= MAX_APIS:
            return False, f"❌ Maximum {MAX_APIS} API keys allowed"
        
        # Validate API key format
        if not self._validate_api_key_format(api_key):
            return False, "❌ Invalid API key format"
        
        # Check if API key already exists
        for existing_api in self.api_keys.values():
            if existing_api.key == api_key:
                return False, "❌ API key already exists"
        
        # Generate unique ID
        api_id = f"api_{len(self.api_keys) + 1}_{int(time.time())}"
        
        # Create API key object
        new_api = APIKey(
            id=api_id,
            key=api_key,
            name=name or f"API Key {len(self.api_keys) + 1}",
            status=APIStatus.ACTIVE,
            last_used=0,
            failure_count=0,
            success_count=0,
            total_requests=0,
            last_error="",
            cooldown_until=0
        )
        
        # Test the API key
        if self._test_api_key(api_key):
            self.api_keys[api_id] = new_api
            logger.info(f"Added API key: {new_api.name} ({api_id})")
            return True, f"✅ API key '{new_api.name}' added successfully!"
        else:
            return False, "❌ API key test failed. Invalid or rate-limited key."
    
    def remove_api_key(self, api_id: str) -> Tuple[bool, str]:
        """Remove an API key"""
        if api_id not in self.api_keys:
            return False, "❌ API key not found"
        
        if len(self.api_keys) <= 1:
            return False, "❌ Cannot remove the last API key"
        
        removed_api = self.api_keys.pop(api_id)
        logger.info(f"Removed API key: {removed_api.name} ({api_id})")
        return True, f"✅ API key '{removed_api.name}' removed successfully!"
    
    def get_available_api(self) -> Optional[APIKey]:
        """Get next available API key using round-robin with failover"""
        if not self.api_keys:
            return None
        
        available_apis = [api for api in self.api_keys.values() if api.is_available()]
        
        if not available_apis:
            # All APIs are down, wait and retry the least recently failed one
            logger.warning("All API keys are unavailable, using least recently failed")
            return min(self.api_keys.values(), key=lambda x: x.last_used)
        
        # Round-robin selection among available APIs
        if self.current_api_index >= len(available_apis):
            self.current_api_index = 0
        
        selected_api = available_apis[self.current_api_index]
        self.current_api_index = (self.current_api_index + 1) % len(available_apis)
        
        return selected_api
    
    def get_best_api(self) -> Optional[APIKey]:
        """Get the best performing API key"""
        available_apis = [api for api in self.api_keys.values() if api.is_available()]
        
        if not available_apis:
            return self.get_available_api()
        
        # Sort by success rate and recent usage
        best_api = max(available_apis, key=lambda x: (
            x.success_count / max(x.total_requests, 1),  # Success rate
            -x.failure_count,  # Fewer failures
            -abs(time.time() - x.last_used)  # More recently used
        ))
        
        return best_api
    
    def disable_api_key(self, api_id: str) -> Tuple[bool, str]:
        """Manually disable an API key"""
        if api_id not in self.api_keys:
            return False, "❌ API key not found"
        
        self.api_keys[api_id].status = APIStatus.DISABLED
        return True, f"✅ API key '{self.api_keys[api_id].name}' disabled"
    
    def enable_api_key(self, api_id: str) -> Tuple[bool, str]:
        """Manually enable an API key"""
        if api_id not in self.api_keys:
            return False, "❌ API key not found"
        
        api = self.api_keys[api_id]
        if self._test_api_key(api.key):
            api.status = APIStatus.ACTIVE
            api.failure_count = 0
            api.cooldown_until = 0
            return True, f"✅ API key '{api.name}' enabled"
        else:
            return False, f"❌ API key '{api.name}' test failed"
    
    def get_api_statistics(self) -> Dict:
        """Get comprehensive API statistics"""
        if not self.api_keys:
            return {
                'total_apis': 0,
                'active_apis': 0,
                'failed_apis': 0,
                'total_requests': 0,
                'total_successes': 0
            }
        
        active_count = sum(1 for api in self.api_keys.values() if api.status == APIStatus.ACTIVE)
        failed_count = sum(1 for api in self.api_keys.values() if api.status in [APIStatus.FAILED, APIStatus.COOLDOWN])
        total_requests = sum(api.total_requests for api in self.api_keys.values())
        total_successes = sum(api.success_count for api in self.api_keys.values())
        
        return {
            'total_apis': len(self.api_keys),
            'active_apis': active_count,
            'failed_apis': failed_count,
            'disabled_apis': sum(1 for api in self.api_keys.values() if api.status == APIStatus.DISABLED),
            'cooldown_apis': sum(1 for api in self.api_keys.values() if api.status == APIStatus.COOLDOWN),
            'total_requests': total_requests,
            'total_successes': total_successes,
            'success_rate': (total_successes / max(total_requests, 1)) * 100
        }
    
    def get_api_details(self) -> List[Dict]:
        """Get detailed information about all API keys"""
        details = []
        for api in self.api_keys.values():
            success_rate = (api.success_count / max(api.total_requests, 1)) * 100
            
            details.append({
                'id': api.id,
                'name': api.name,
                'status': api.status.value,
                'success_rate': success_rate,
                'total_requests': api.total_requests,
                'success_count': api.success_count,
                'failure_count': api.failure_count,
                'last_used': api.last_used,
                'last_error': api.last_error,
                'is_available': api.is_available(),
                'masked_key': f"...{api.key[-8:]}"
            })
        
        return details
    
    def _validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format"""
        return len(api_key) >= 20 and api_key.startswith('AI')
    
    def _test_api_key(self, api_key: str) -> bool:
        """Test if API key is valid and working"""
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content("Say 'test' if you can read this.")
            return response and len(response.text) > 0
        except Exception as e:
            logger.error(f"API key test failed: {e}")
            return False

# Global API manager instance
api_manager = APIManager()

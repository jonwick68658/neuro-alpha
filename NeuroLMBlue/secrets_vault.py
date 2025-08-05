"""
Secrets Vault System for NeuroLM
Secure storage and management of user API keys and credentials
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta

class SecretsVault:
    """Secure vault for storing user API keys and credentials"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.master_key = os.environ.get('VAULT_MASTER_KEY', 'default-master-key-change-in-production')
        self.setup_database()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def setup_database(self):
        """Create secrets vault tables"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Create secrets table with UUID user_id
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_secrets (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL,
                        secret_type VARCHAR(50) NOT NULL,
                        secret_name VARCHAR(100) NOT NULL,
                        encrypted_value TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        metadata JSONB DEFAULT '{}',
                        UNIQUE(user_id, secret_type, secret_name)
                    )
                """)
                
                # Create secret access log table with UUID user_id
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS secret_access_log (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL,
                        secret_type VARCHAR(50) NOT NULL,
                        secret_name VARCHAR(100) NOT NULL,
                        action VARCHAR(20) NOT NULL,
                        ip_address INET,
                        user_agent TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Create secret sharing table for organization features
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS secret_sharing (
                        id SERIAL PRIMARY KEY,
                        secret_id INTEGER REFERENCES user_secrets(id) ON DELETE CASCADE,
                        shared_with_user_id INTEGER,
                        shared_with_org_id INTEGER,
                        permission_level VARCHAR(20) DEFAULT 'read',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NULL,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                conn.commit()
        finally:
            conn.close()
    
    def _generate_key(self, user_id: str, salt: Optional[bytes] = None) -> bytes:
        """Generate encryption key for user"""
        if salt is None:
            salt = f"user_{user_id}_salt".encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return key
    
    def _encrypt_value(self, value: str, user_id: str) -> str:
        """Encrypt a secret value"""
        key = self._generate_key(user_id)
        f = Fernet(key)
        encrypted = f.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def _decrypt_value(self, encrypted_value: str, user_id: str) -> str:
        """Decrypt a secret value"""
        key = self._generate_key(user_id)
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def store_secret(self, user_id: str, secret_type: str, secret_name: str, 
                    secret_value: str, metadata: Optional[Dict] = None, expires_at: Optional[datetime] = None) -> bool:
        """Store a secret in the vault"""
        try:
            encrypted_value = self._encrypt_value(secret_value, str(user_id))
            metadata = metadata or {}
            
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO user_secrets 
                        (user_id, secret_type, secret_name, encrypted_value, metadata, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, secret_type, secret_name)
                        DO UPDATE SET 
                            encrypted_value = EXCLUDED.encrypted_value,
                            metadata = EXCLUDED.metadata,
                            expires_at = EXCLUDED.expires_at,
                            updated_at = CURRENT_TIMESTAMP,
                            is_active = TRUE
                    """, (user_id, secret_type, secret_name, encrypted_value, 
                         json.dumps(metadata), expires_at))
                    
                    conn.commit()
                    
                    # Log the action
                    self._log_access(user_id, secret_type, secret_name, 'store')
                    
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error storing secret: {e}")
            return False
    
    def get_secret(self, user_id: str, secret_type: str, secret_name: str) -> Optional[str]:
        """Retrieve a secret from the vault"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT encrypted_value, expires_at 
                        FROM user_secrets 
                        WHERE user_id = %s AND secret_type = %s AND secret_name = %s 
                        AND is_active = TRUE
                    """, (user_id, secret_type, secret_name))
                    
                    result = cursor.fetchone()
                    if not result:
                        return None
                    
                    # Check if expired
                    if result['expires_at'] and datetime.now() > result['expires_at']:
                        self.delete_secret(user_id, secret_type, secret_name)
                        return None
                    
                    decrypted_value = self._decrypt_value(result['encrypted_value'], str(user_id))
                    
                    # Log the access
                    self._log_access(user_id, secret_type, secret_name, 'retrieve')
                    
                    return decrypted_value
            finally:
                conn.close()
        except Exception as e:
            print(f"Error retrieving secret: {e}")
            self._log_access(user_id, secret_type, secret_name, 'retrieve', success=False)
            return None
    
    def delete_secret(self, user_id: str, secret_type: str, secret_name: str) -> bool:
        """Delete a secret from the vault"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE user_secrets 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND secret_type = %s AND secret_name = %s
                    """, (user_id, secret_type, secret_name))
                    
                    conn.commit()
                    
                    # Log the action
                    self._log_access(user_id, secret_type, secret_name, 'delete')
                    
                    return cursor.rowcount > 0
            finally:
                conn.close()
        except Exception as e:
            print(f"Error deleting secret: {e}")
            return False
    
    def list_user_secrets(self, user_id: str, secret_type: Optional[str] = None) -> List[Dict]:
        """List all secrets for a user"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if secret_type:
                        cursor.execute("""
                            SELECT secret_type, secret_name, created_at, updated_at, 
                                   expires_at, metadata
                            FROM user_secrets 
                            WHERE user_id = %s AND secret_type = %s AND is_active = TRUE
                            ORDER BY secret_type, secret_name
                        """, (user_id, secret_type))
                    else:
                        cursor.execute("""
                            SELECT secret_type, secret_name, created_at, updated_at, 
                                   expires_at, metadata
                            FROM user_secrets 
                            WHERE user_id = %s AND is_active = TRUE
                            ORDER BY secret_type, secret_name
                        """, (user_id,))
                    
                    results = cursor.fetchall()
                    
                    # Convert to list of dicts and parse metadata
                    secrets = []
                    for row in results:
                        secret_info = dict(row)
                        # Handle metadata parsing safely
                        if secret_info['metadata']:
                            try:
                                if isinstance(secret_info['metadata'], str):
                                    secret_info['metadata'] = json.loads(secret_info['metadata'])
                                # If it's already a dict, keep it as is
                            except (json.JSONDecodeError, TypeError):
                                secret_info['metadata'] = {}
                        else:
                            secret_info['metadata'] = {}
                        secrets.append(secret_info)
                    
                    return secrets
            finally:
                conn.close()
        except Exception as e:
            print(f"Error listing secrets: {e}")
            return []
    
    def update_secret_metadata(self, user_id: str, secret_type: str, secret_name: str, 
                              metadata: Dict) -> bool:
        """Update metadata for a secret"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE user_secrets 
                        SET metadata = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND secret_type = %s AND secret_name = %s 
                        AND is_active = TRUE
                    """, (json.dumps(metadata), user_id, secret_type, secret_name))
                    
                    conn.commit()
                    return cursor.rowcount > 0
            finally:
                conn.close()
        except Exception as e:
            print(f"Error updating secret metadata: {e}")
            return False
    
    def _log_access(self, user_id: str, secret_type: str, secret_name: str, 
                   action: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None, 
                   success: bool = True):
        """Log secret access for security auditing"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO secret_access_log 
                        (user_id, secret_type, secret_name, action, ip_address, user_agent, success)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, secret_type, secret_name, action, ip_address, user_agent, success))
                    
                    conn.commit()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error logging secret access: {e}")
    
    def get_access_log(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get access log for a user"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT secret_type, secret_name, action, ip_address, 
                               user_agent, timestamp, success
                        FROM secret_access_log 
                        WHERE user_id = %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (user_id, limit))
                    
                    return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        except Exception as e:
            print(f"Error getting access log: {e}")
            return []
    
    def rotate_secret(self, user_id: str, secret_type: str, secret_name: str, 
                     new_value: str) -> bool:
        """Rotate a secret (update with new value while keeping history)"""
        try:
            # Get current secret metadata
            current_secrets = self.list_user_secrets(user_id, secret_type)
            current_secret = next((s for s in current_secrets if s['secret_name'] == secret_name), None)
            
            if current_secret:
                # Update metadata with rotation info
                metadata = current_secret.get('metadata', {})
                metadata['last_rotated'] = datetime.now().isoformat()
                metadata['rotation_count'] = metadata.get('rotation_count', 0) + 1
                
                # Store the new value
                return self.store_secret(user_id, secret_type, secret_name, new_value, metadata)
            else:
                # New secret
                return self.store_secret(user_id, secret_type, secret_name, new_value)
        except Exception as e:
            print(f"Error rotating secret: {e}")
            return False
    
    def cleanup_expired_secrets(self):
        """Clean up expired secrets"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE user_secrets 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE expires_at < CURRENT_TIMESTAMP AND is_active = TRUE
                    """)
                    
                    conn.commit()
                    return cursor.rowcount
            finally:
                conn.close()
        except Exception as e:
            print(f"Error cleaning up expired secrets: {e}")
            return 0

# Global vault instance
vault = SecretsVault()

# Helper functions for API key management
def store_api_key(user_id: str, provider: str, api_key: str) -> bool:
    """Store an API key for a user"""
    metadata = {
        'provider': provider,
        'masked_key': api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else 'sk-...',
        'created_via': 'web_interface'
    }
    return vault.store_secret(user_id, 'api_key', provider, api_key, metadata)

def get_api_key(user_id: str, provider: str) -> Optional[str]:
    """Get an API key for a user"""
    return vault.get_secret(user_id, 'api_key', provider)

def delete_api_key(user_id: str, provider: str) -> bool:
    """Delete an API key for a user"""
    return vault.delete_secret(user_id, 'api_key', provider)

def list_api_keys(user_id: str) -> List[Dict]:
    """List all API keys for a user"""
    return vault.list_user_secrets(user_id, 'api_key')

def rotate_api_key(user_id: str, provider: str, new_key: str) -> bool:
    """Rotate an API key"""
    return vault.rotate_secret(user_id, 'api_key', provider, new_key)
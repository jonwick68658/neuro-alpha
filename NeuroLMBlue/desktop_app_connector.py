"""
Desktop App Connector
Manages communication between web app and desktop personal AI models
"""

import json
import asyncio
import websockets
import psycopg2
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import hashlib
import uuid
from personal_models_config import get_model_by_id

class DesktopAppConnector:
    """Manages desktop app connections and model communication"""
    
    def __init__(self):
        self.db_connection = None
        self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        self._init_database()
    
    def get_connection(self):
        """Get database connection"""
        if self.db_connection is None or self.db_connection.closed:
            self.db_connection = psycopg2.connect(os.environ.get("DATABASE_URL"))
        return self.db_connection
    
    def _init_database(self):
        """Initialize database tables for desktop app connections"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Desktop app connections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS desktop_app_connections (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                connection_id VARCHAR(255) UNIQUE NOT NULL,
                app_version VARCHAR(50),
                os_info VARCHAR(100),
                hardware_info JSONB,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'connected',
                local_models JSONB DEFAULT '[]'
            )
        """)
        
        # Desktop model requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS desktop_model_requests (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                model_id VARCHAR(255) NOT NULL,
                request_type VARCHAR(50) NOT NULL,
                request_data JSONB,
                response_data JSONB,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        conn.commit()
    
    async def register_connection(self, websocket: websockets.WebSocketServerProtocol, 
                                user_id: str, connection_data: Dict) -> str:
        """Register a new desktop app connection"""
        connection_id = str(uuid.uuid4())
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.user_connections[user_id] = connection_id
        
        # Save to database
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO desktop_app_connections 
            (user_id, connection_id, app_version, os_info, hardware_info)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (connection_id) DO UPDATE SET
                last_seen = CURRENT_TIMESTAMP,
                status = 'connected',
                app_version = EXCLUDED.app_version,
                os_info = EXCLUDED.os_info,
                hardware_info = EXCLUDED.hardware_info
        """, (
            user_id, connection_id, 
            connection_data.get('app_version'),
            connection_data.get('os_info'),
            json.dumps(connection_data.get('hardware_info', {}))
        ))
        
        conn.commit()
        
        return connection_id
    
    async def unregister_connection(self, connection_id: str):
        """Unregister a desktop app connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from user connections
        user_id = None
        for uid, cid in self.user_connections.items():
            if cid == connection_id:
                user_id = uid
                break
        
        if user_id:
            del self.user_connections[user_id]
        
        # Update database
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE desktop_app_connections 
            SET status = 'disconnected', last_seen = CURRENT_TIMESTAMP
            WHERE connection_id = %s
        """, (connection_id,))
        
        conn.commit()
    
    async def send_to_desktop(self, user_id: str, message: Dict) -> bool:
        """Send message to user's desktop app"""
        connection_id = self.user_connections.get(user_id)
        if not connection_id or connection_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"Error sending to desktop: {e}")
            await self.unregister_connection(connection_id)
            return False
    
    async def request_model_download(self, user_id: str, model_id: str) -> Dict:
        """Request desktop app to download a model"""
        model_config = get_model_by_id(model_id)
        if not model_config:
            return {"error": "Model not found"}
        
        # Create request record
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO desktop_model_requests 
            (user_id, model_id, request_type, request_data)
            VALUES (%s, %s, 'download', %s)
            RETURNING id
        """, (user_id, model_id, json.dumps({
            "model_name": model_config.name,
            "download_url": model_config.download_url,
            "size_gb": model_config.size_gb
        })))
        
        request_id = cursor.fetchone()[0]
        conn.commit()
        
        # Send to desktop app
        message = {
            "type": "model_download_request",
            "request_id": request_id,
            "model_id": model_id,
            "model_data": {
                "name": model_config.name,
                "display_name": model_config.display_name,
                "download_url": model_config.download_url,
                "size_gb": model_config.size_gb,
                "repository": model_config.repository,
                "inference_engine": model_config.inference_engine,
                "quantization": model_config.quantization
            }
        }
        
        success = await self.send_to_desktop(user_id, message)
        
        if success:
            return {"request_id": request_id, "status": "sent"}
        else:
            return {"error": "Desktop app not connected"}
    
    async def request_model_training(self, user_id: str, model_id: str, 
                                   training_data: str) -> Dict:
        """Request desktop app to train a model"""
        # Create request record
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO desktop_model_requests 
            (user_id, model_id, request_type, request_data)
            VALUES (%s, %s, 'train', %s)
            RETURNING id
        """, (user_id, model_id, json.dumps({
            "training_data": training_data,
            "training_type": "fine_tuning"
        })))
        
        request_id = cursor.fetchone()[0]
        conn.commit()
        
        # Send to desktop app
        message = {
            "type": "model_training_request",
            "request_id": request_id,
            "model_id": model_id,
            "training_data": training_data
        }
        
        success = await self.send_to_desktop(user_id, message)
        
        if success:
            return {"request_id": request_id, "status": "sent"}
        else:
            return {"error": "Desktop app not connected"}
    
    async def chat_with_local_model(self, user_id: str, model_id: str, 
                                  message: str, conversation_id: str = None) -> Dict:
        """Send chat message to local model running on desktop"""
        # Create request record
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO desktop_model_requests 
            (user_id, model_id, request_type, request_data)
            VALUES (%s, %s, 'chat', %s)
            RETURNING id
        """, (user_id, model_id, json.dumps({
            "message": message,
            "conversation_id": conversation_id
        })))
        
        request_id = cursor.fetchone()[0]
        conn.commit()
        
        # Send to desktop app
        message_data = {
            "type": "chat_request",
            "request_id": request_id,
            "model_id": model_id,
            "message": message,
            "conversation_id": conversation_id
        }
        
        success = await self.send_to_desktop(user_id, message_data)
        
        if success:
            return {"request_id": request_id, "status": "sent"}
        else:
            return {"error": "Desktop app not connected"}
    
    async def handle_desktop_response(self, connection_id: str, response: Dict):
        """Handle response from desktop app"""
        try:
            request_id = response.get("request_id")
            if not request_id:
                return
            
            # Update request in database
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE desktop_model_requests 
                SET response_data = %s, 
                    status = %s, 
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                json.dumps(response.get("data", {})),
                response.get("status", "completed"),
                request_id
            ))
            
            conn.commit()
            
        except Exception as e:
            print(f"Error handling desktop response: {e}")
    
    async def get_user_connection_status(self, user_id: str) -> Dict:
        """Get connection status for a user"""
        connection_id = self.user_connections.get(user_id)
        is_connected = connection_id is not None and connection_id in self.active_connections
        
        if not is_connected:
            return {"connected": False}
        
        # Get connection details from database
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT app_version, os_info, hardware_info, connected_at, local_models
            FROM desktop_app_connections 
            WHERE connection_id = %s AND status = 'connected'
        """, (connection_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                "connected": True,
                "connection_id": connection_id,
                "app_version": result[0],
                "os_info": result[1],
                "hardware_info": result[2],
                "connected_at": result[3].isoformat() if result[3] else None,
                "local_models": result[4] if result[4] else []
            }
        
        return {"connected": False}
    
    async def get_pending_requests(self, user_id: str) -> List[Dict]:
        """Get pending requests for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, model_id, request_type, request_data, status, created_at
            FROM desktop_model_requests 
            WHERE user_id = %s AND status = 'pending'
            ORDER BY created_at DESC
        """, (user_id,))
        
        requests = []
        for row in cursor.fetchall():
            requests.append({
                "id": row[0],
                "model_id": row[1],
                "request_type": row[2],
                "request_data": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            })
        
        return requests
    
    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections from desktop app"""
        connection_id = None
        
        try:
            # Wait for authentication message
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            if auth_data.get("type") != "authenticate":
                await websocket.close(code=4001, reason="Authentication required")
                return
            
            user_id = auth_data.get("user_id")
            connection_data = auth_data.get("connection_data", {})
            
            if not user_id:
                await websocket.close(code=4001, reason="User ID required")
                return
            
            # Register connection
            connection_id = await self.register_connection(websocket, user_id, connection_data)
            
            # Send confirmation
            await websocket.send(json.dumps({
                "type": "authenticated",
                "connection_id": connection_id
            }))
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_desktop_response(connection_id, data)
                except json.JSONDecodeError:
                    print(f"Invalid JSON from desktop app: {message}")
                except Exception as e:
                    print(f"Error handling desktop message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"Desktop app disconnected: {connection_id}")
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            if connection_id:
                await self.unregister_connection(connection_id)
    
    async def update_model_status(self, connection_id: str, status_data: Dict) -> Dict:
        """Update model status from desktop app"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update model status in database
            cursor.execute("""
                UPDATE desktop_app_connections 
                SET local_models = %s, last_seen = CURRENT_TIMESTAMP 
                WHERE connection_id = %s
            """, (json.dumps(status_data.get('models', [])), connection_id))
            
            conn.commit()
            return {"success": True, "message": "Model status updated"}
            
        except Exception as e:
            print(f"Error updating model status: {e}")
            return {"success": False, "error": str(e)}
    
    async def handle_chat_response(self, connection_id: str, response_data: Dict) -> Dict:
        """Handle chat response from desktop app"""
        try:
            # Store chat response for retrieval
            response_id = response_data.get('response_id')
            message = response_data.get('message', '')
            
            # You could store this in a chat responses table or return directly
            # For now, we'll just acknowledge receipt
            
            return {"success": True, "message": "Chat response received"}
            
        except Exception as e:
            print(f"Error handling chat response: {e}")
            return {"success": False, "error": str(e)}

    def close(self):
        """Close all connections"""
        if self.db_connection:
            self.db_connection.close()

# Global instance
desktop_connector = DesktopAppConnector()
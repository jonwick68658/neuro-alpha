"""
Personal Model Manager
Handles downloading, fine-tuning, and managing personal AI models
"""

import os
import json
import psycopg2
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from personal_models_config import AVAILABLE_MODELS, ModelConfig, get_model_by_id
from dataclasses import asdict
import hashlib
import requests
from pathlib import Path

class PersonalModelManager:
    """Manages personal AI models for users"""
    
    def __init__(self):
        self.db_connection = None
        self.models_dir = Path("personal_models")
        self.models_dir.mkdir(exist_ok=True)
        self._init_database()
    
    def get_connection(self):
        """Get database connection"""
        if self.db_connection is None or self.db_connection.closed:
            self.db_connection = psycopg2.connect(os.environ.get("DATABASE_URL"))
        return self.db_connection
    
    def _init_database(self):
        """Initialize database tables for personal models"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # User models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_personal_models (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                model_id VARCHAR(255) NOT NULL,
                custom_name VARCHAR(255),
                status VARCHAR(50) DEFAULT 'pending',
                download_progress FLOAT DEFAULT 0.0,
                local_path VARCHAR(500),
                fine_tuned BOOLEAN DEFAULT FALSE,
                fine_tune_version INTEGER DEFAULT 0,
                last_training_date TIMESTAMP,
                model_size_gb FLOAT,
                performance_score FLOAT,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, model_id)
            )
        """)
        
        # Model training jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_model_training_jobs (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                model_id VARCHAR(255) NOT NULL,
                job_status VARCHAR(50) DEFAULT 'pending',
                training_data_size INTEGER,
                training_progress FLOAT DEFAULT 0.0,
                estimated_completion TIMESTAMP,
                error_message TEXT,
                training_metrics JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Model usage analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_model_usage (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                model_id VARCHAR(255) NOT NULL,
                usage_type VARCHAR(50),
                response_time_ms INTEGER,
                quality_rating FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
    
    async def get_user_models(self, user_id: str) -> List[Dict]:
        """Get all personal models for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT model_id, custom_name, status, download_progress, 
                   fine_tuned, fine_tune_version, last_training_date,
                   model_size_gb, performance_score, usage_count,
                   created_at, updated_at
            FROM user_personal_models 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        user_models = []
        for row in cursor.fetchall():
            model_config = get_model_by_id(row[0])
            if model_config:
                user_models.append({
                    "model_id": row[0],
                    "custom_name": row[1],
                    "status": row[2],
                    "download_progress": row[3],
                    "fine_tuned": row[4],
                    "fine_tune_version": row[5],
                    "last_training_date": row[6].isoformat() if row[6] else None,
                    "model_size_gb": row[7],
                    "performance_score": row[8],
                    "usage_count": row[9],
                    "created_at": row[10].isoformat(),
                    "updated_at": row[11].isoformat(),
                    "config": asdict(model_config)
                })
        
        return user_models
    
    async def add_model_to_user(self, user_id: str, model_id: str, custom_name: str = None) -> Dict:
        """Add a model to user's personal collection"""
        model_config = get_model_by_id(model_id)
        if not model_config:
            raise ValueError(f"Model {model_id} not found")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO user_personal_models 
                (user_id, model_id, custom_name, model_size_gb, status)
                VALUES (%s, %s, %s, %s, 'pending')
                ON CONFLICT (user_id, model_id) 
                DO UPDATE SET 
                    custom_name = EXCLUDED.custom_name,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (user_id, model_id, custom_name or model_config.display_name, model_config.size_gb))
            
            model_record_id = cursor.fetchone()[0]
            conn.commit()
            
            return {
                "id": model_record_id,
                "model_id": model_id,
                "custom_name": custom_name or model_config.display_name,
                "status": "pending",
                "message": "Model added to your collection. Download will begin shortly."
            }
            
        except psycopg2.IntegrityError as e:
            conn.rollback()
            return {"error": "Model already exists in your collection"}
    
    async def remove_model_from_user(self, user_id: str, model_id: str) -> Dict:
        """Remove a model from user's collection"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get model path for cleanup
        cursor.execute("""
            SELECT local_path FROM user_personal_models 
            WHERE user_id = %s AND model_id = %s
        """, (user_id, model_id))
        
        result = cursor.fetchone()
        if result and result[0]:
            local_path = Path(result[0])
            if local_path.exists():
                try:
                    # Remove model files
                    import shutil
                    shutil.rmtree(local_path.parent)
                except Exception as e:
                    print(f"Error removing model files: {e}")
        
        # Remove from database
        cursor.execute("""
            DELETE FROM user_personal_models 
            WHERE user_id = %s AND model_id = %s
        """, (user_id, model_id))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        if deleted_count > 0:
            return {"message": "Model removed from your collection"}
        else:
            return {"error": "Model not found in your collection"}
    
    async def update_model_status(self, user_id: str, model_id: str, status: str, 
                                 progress: float = None, local_path: str = None) -> bool:
        """Update model download/training status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        update_fields = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
        values = [status]
        
        if progress is not None:
            update_fields.append("download_progress = %s")
            values.append(progress)
        
        if local_path:
            update_fields.append("local_path = %s")
            values.append(local_path)
        
        values.extend([user_id, model_id])
        
        cursor.execute(f"""
            UPDATE user_personal_models 
            SET {', '.join(update_fields)}
            WHERE user_id = %s AND model_id = %s
        """, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        return success
    
    async def start_model_training(self, user_id: str, model_id: str) -> Dict:
        """Start fine-tuning process for a user's model"""
        # Import here to avoid circular imports
        from custom_model_trainer import CustomModelTrainer
        
        trainer = CustomModelTrainer()
        
        # Check if user has enough training data
        analysis = await trainer.analyze_training_potential(user_id)
        if analysis["total_examples"] < 50:  # Minimum for fine-tuning
            return {
                "error": "Insufficient training data. You need at least 50 high-quality conversations.",
                "current_count": analysis["total_examples"],
                "required_count": 50
            }
        
        # Create training job record
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO personal_model_training_jobs 
            (user_id, model_id, training_data_size, job_status)
            VALUES (%s, %s, %s, 'preparing')
            RETURNING id
        """, (user_id, model_id, analysis["total_examples"]))
        
        job_id = cursor.fetchone()[0]
        conn.commit()
        
        # Start training process (this would be done in background)
        # For now, we'll simulate the process
        await self._simulate_training_process(user_id, model_id, job_id)
        
        return {
            "job_id": job_id,
            "status": "started",
            "message": "Training job started. This process may take 2-6 hours.",
            "training_data_size": analysis["total_examples"]
        }
    
    async def _simulate_training_process(self, user_id: str, model_id: str, job_id: int):
        """Simulate the training process (placeholder for actual implementation)"""
        # This would integrate with actual training pipeline
        # For now, we'll just update the job status
        
        import asyncio
        await asyncio.sleep(1)  # Simulate preparation time
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Update job to running
        cursor.execute("""
            UPDATE personal_model_training_jobs 
            SET job_status = 'running', 
                training_progress = 0.1,
                estimated_completion = %s
            WHERE id = %s
        """, (datetime.now() + timedelta(hours=3), job_id))
        
        # Update model record
        cursor.execute("""
            UPDATE user_personal_models 
            SET status = 'training'
            WHERE user_id = %s AND model_id = %s
        """, (user_id, model_id))
        
        conn.commit()
    
    async def get_training_jobs(self, user_id: str) -> List[Dict]:
        """Get all training jobs for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, model_id, job_status, training_data_size, 
                   training_progress, estimated_completion, error_message,
                   training_metrics, created_at, completed_at
            FROM personal_model_training_jobs 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        jobs = []
        for row in cursor.fetchall():
            model_config = get_model_by_id(row[1])
            jobs.append({
                "id": row[0],
                "model_id": row[1],
                "model_name": model_config.display_name if model_config else row[1],
                "status": row[2],
                "training_data_size": row[3],
                "progress": row[4],
                "estimated_completion": row[5].isoformat() if row[5] else None,
                "error_message": row[6],
                "metrics": row[7],
                "created_at": row[8].isoformat(),
                "completed_at": row[9].isoformat() if row[9] else None
            })
        
        return jobs
    
    async def get_available_models(self) -> List[Dict]:
        """Get all available models for download"""
        models = []
        for model_config in AVAILABLE_MODELS.values():
            models.append(asdict(model_config))
        return models
    
    async def record_model_usage(self, user_id: str, model_id: str, 
                               usage_type: str, response_time_ms: int, 
                               quality_rating: float = None):
        """Record model usage for analytics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO personal_model_usage 
            (user_id, model_id, usage_type, response_time_ms, quality_rating)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, model_id, usage_type, response_time_ms, quality_rating))
        
        # Update usage count
        cursor.execute("""
            UPDATE user_personal_models 
            SET usage_count = usage_count + 1
            WHERE user_id = %s AND model_id = %s
        """, (user_id, model_id))
        
        conn.commit()
    
    async def get_usage_analytics(self, user_id: str, model_id: str = None) -> Dict:
        """Get usage analytics for user's models"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if model_id:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_usage,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(quality_rating) as avg_quality,
                    usage_type,
                    DATE(timestamp) as usage_date,
                    COUNT(*) as daily_count
                FROM personal_model_usage 
                WHERE user_id = %s AND model_id = %s
                GROUP BY usage_type, DATE(timestamp)
                ORDER BY usage_date DESC
            """, (user_id, model_id))
        else:
            cursor.execute("""
                SELECT 
                    model_id,
                    COUNT(*) as total_usage,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(quality_rating) as avg_quality
                FROM personal_model_usage 
                WHERE user_id = %s
                GROUP BY model_id
                ORDER BY total_usage DESC
            """, (user_id,))
        
        results = cursor.fetchall()
        
        if model_id:
            return {
                "model_id": model_id,
                "analytics": [
                    {
                        "total_usage": row[0],
                        "avg_response_time": float(row[1]) if row[1] else 0,
                        "avg_quality": float(row[2]) if row[2] else 0,
                        "usage_type": row[3],
                        "usage_date": row[4].isoformat(),
                        "daily_count": row[5]
                    }
                    for row in results
                ]
            }
        else:
            return {
                "models": [
                    {
                        "model_id": row[0],
                        "total_usage": row[1],
                        "avg_response_time": float(row[2]) if row[2] else 0,
                        "avg_quality": float(row[3]) if row[3] else 0
                    }
                    for row in results
                ]
            }
    
    def close(self):
        """Close database connections"""
        if self.db_connection:
            self.db_connection.close()

# Global instance
personal_model_manager = PersonalModelManager()
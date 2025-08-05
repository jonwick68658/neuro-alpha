"""
Training Scheduler - Automated Model Training During Off-Peak Hours
Manages weekly training sessions and model deployment
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from custom_model_trainer import custom_model_trainer
from typing import Dict, List, Optional
import json
import os
import threading

class TrainingScheduler:
    """Manages automated training schedules and model deployment"""
    
    def __init__(self):
        self.training_jobs = {}  # Track active training jobs
        self.trained_models = {}  # Track successfully trained models
        self.scheduler_running = False
        self.scheduler_thread = None
        
    async def weekly_training_analysis(self):
        """Analyze all users for training potential"""
        print("🔍 Starting weekly training analysis...")
        
        # Get all users with training potential
        users_analysis = await custom_model_trainer.get_all_users_training_potential()
        
        # Filter users ready for training
        ready_users = [
            user for user in users_analysis 
            if user['training_ready'] and user['avg_quality'] >= 0.7
        ]
        
        print(f"📊 Found {len(ready_users)} users ready for training")
        
        # Start training for ready users
        for user in ready_users:
            await self.start_user_training(user['user_id'])
            
        return {
            "total_users_analyzed": len(users_analysis),
            "users_ready_for_training": len(ready_users),
            "training_jobs_started": len(ready_users)
        }
    
    async def start_user_training(self, user_id: str):
        """Start training process for a specific user"""
        try:
            print(f"🚀 Starting training for user {user_id}")
            
            # Prepare training data
            data_result = await custom_model_trainer.prepare_training_data(user_id)
            
            if data_result['status'] != 'success':
                print(f"❌ Training data preparation failed for user {user_id}: {data_result.get('message', 'Unknown error')}")
                return
            
            # Start fine-tuning
            training_result = await custom_model_trainer.fine_tune_model(
                data_result['train_file'],
                data_result['val_file']
            )
            
            if training_result['status'] == 'started':
                # Track training job
                self.training_jobs[user_id] = {
                    'job_id': training_result['job_id'],
                    'started_at': datetime.now(),
                    'model': training_result['model'],
                    'train_examples': data_result['train_examples'],
                    'val_examples': data_result['val_examples']
                }
                
                print(f"✅ Training started for user {user_id}, job ID: {training_result['job_id']}")
                
                # Schedule status check
                await self.schedule_status_check(user_id, training_result['job_id'])
            else:
                print(f"❌ Training failed to start for user {user_id}: {training_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error starting training for user {user_id}: {e}")
    
    async def schedule_status_check(self, user_id: str, job_id: str):
        """Schedule periodic status checks for training job"""
        max_checks = 30  # Check for up to 5 hours (10 min intervals)
        check_count = 0
        
        while check_count < max_checks:
            await asyncio.sleep(600)  # Wait 10 minutes
            check_count += 1
            
            try:
                status = await custom_model_trainer.check_training_status(job_id)
                
                if status['status'] == 'succeeded':
                    print(f"🎉 Training completed successfully for user {user_id}")
                    
                    # Store trained model info
                    self.trained_models[user_id] = {
                        'model_id': status['fine_tuned_model'],
                        'completed_at': datetime.now(),
                        'job_id': job_id,
                        'trained_tokens': status.get('trained_tokens', 0)
                    }
                    
                    # Clean up training files
                    await self.cleanup_training_files(user_id)
                    
                    # Remove from active jobs
                    if user_id in self.training_jobs:
                        del self.training_jobs[user_id]
                    
                    break
                    
                elif status['status'] == 'failed':
                    print(f"❌ Training failed for user {user_id}: {status.get('error', 'Unknown error')}")
                    
                    # Remove from active jobs
                    if user_id in self.training_jobs:
                        del self.training_jobs[user_id]
                    
                    break
                    
                elif status['status'] in ['validating_files', 'queued', 'running']:
                    print(f"⏳ Training in progress for user {user_id}: {status['status']}")
                    
                else:
                    print(f"❓ Unknown training status for user {user_id}: {status['status']}")
                    
            except Exception as e:
                print(f"❌ Error checking training status for user {user_id}: {e}")
    
    async def cleanup_training_files(self, user_id: str):
        """Clean up training files after completion"""
        try:
            files_to_remove = [
                f"train_training_data.jsonl",
                f"val_training_data.jsonl"
            ]
            
            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🧹 Cleaned up {file_path}")
                    
        except Exception as e:
            print(f"❌ Error cleaning up training files: {e}")
    
    def start_scheduler(self):
        """Start the training scheduler"""
        if self.scheduler_running:
            print("⚠️ Scheduler already running")
            return
        
        # Schedule weekly training at 2 AM Sunday (off-peak hours)
        schedule.every().sunday.at("02:00").do(
            lambda: asyncio.run(self.weekly_training_analysis())
        )
        
        # Schedule daily status checks at 3 AM
        schedule.every().day.at("03:00").do(
            lambda: asyncio.run(self.check_all_training_jobs())
        )
        
        self.scheduler_running = True
        
        # Start scheduler in separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print("📅 Training scheduler started")
        print("📅 Weekly training: Sunday 2:00 AM")
        print("📅 Daily status checks: 3:00 AM")
    
    def _run_scheduler(self):
        """Internal scheduler runner"""
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop the training scheduler"""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("🛑 Training scheduler stopped")
    
    async def check_all_training_jobs(self):
        """Check status of all active training jobs"""
        print("🔍 Checking all active training jobs...")
        
        for user_id, job_info in list(self.training_jobs.items()):
            try:
                status = await custom_model_trainer.check_training_status(job_info['job_id'])
                
                if status['status'] == 'succeeded':
                    print(f"✅ Training completed for user {user_id}")
                    
                    # Store completed model
                    self.trained_models[user_id] = {
                        'model_id': status['fine_tuned_model'],
                        'completed_at': datetime.now(),
                        'job_id': job_info['job_id'],
                        'trained_tokens': status.get('trained_tokens', 0)
                    }
                    
                    # Clean up
                    await self.cleanup_training_files(user_id)
                    del self.training_jobs[user_id]
                    
                elif status['status'] == 'failed':
                    print(f"❌ Training failed for user {user_id}")
                    del self.training_jobs[user_id]
                    
            except Exception as e:
                print(f"❌ Error checking job for user {user_id}: {e}")
    
    async def get_training_status(self) -> Dict:
        """Get current training status"""
        return {
            "scheduler_running": self.scheduler_running,
            "active_jobs": len(self.training_jobs),
            "completed_models": len(self.trained_models),
            "active_training_jobs": [
                {
                    "user_id": user_id,
                    "started_at": job_info['started_at'].isoformat(),
                    "job_id": job_info['job_id'],
                    "model": job_info['model']
                }
                for user_id, job_info in self.training_jobs.items()
            ],
            "trained_models": [
                {
                    "user_id": user_id,
                    "model_id": model_info['model_id'],
                    "completed_at": model_info['completed_at'].isoformat(),
                    "trained_tokens": model_info['trained_tokens']
                }
                for user_id, model_info in self.trained_models.items()
            ]
        }
    
    async def manual_training_trigger(self) -> Dict:
        """Manually trigger training analysis and job creation"""
        print("🔄 Manual training trigger initiated...")
        return await self.weekly_training_analysis()
    
    def get_user_custom_model(self, user_id: str) -> Optional[str]:
        """Get custom model ID for a user if available"""
        if user_id in self.trained_models:
            return self.trained_models[user_id]['model_id']
        return None

# Global scheduler instance
training_scheduler = TrainingScheduler()

async def start_training_scheduler():
    """Start the automated training scheduler"""
    training_scheduler.start_scheduler()

async def stop_training_scheduler():
    """Stop the automated training scheduler"""
    training_scheduler.stop_scheduler()

async def get_training_status():
    """Get current training status"""
    return await training_scheduler.get_training_status()

async def trigger_manual_training():
    """Manually trigger training analysis"""
    return await training_scheduler.manual_training_trigger()

def get_user_custom_model(user_id: str) -> Optional[str]:
    """Get custom model for user if available"""
    return training_scheduler.get_user_custom_model(user_id)
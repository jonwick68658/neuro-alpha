#!/usr/bin/env python3
"""
Error Cleanup Scheduler Service
==============================

Background service that runs nightly cleanup of system error messages.
Integrates with the existing FastAPI application lifecycle.
"""

import asyncio
import schedule
import time
import threading
from datetime import datetime
import subprocess
import os

class ErrorCleanupScheduler:
    """Background scheduler for nightly error message cleanup."""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        
    def start(self):
        """Start the background scheduler."""
        if self.running:
            return
            
        print("✅ Error cleanup scheduler starting...")
        
        # Schedule cleanup for 2 AM daily
        schedule.every().day.at("02:00").do(self._run_cleanup)
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        print("✅ Nightly error cleanup scheduled for 2:00 AM daily")
        
    def stop(self):
        """Stop the background scheduler."""
        self.running = False
        schedule.clear()
        print("❌ Error cleanup scheduler stopped")
        
    def _scheduler_loop(self):
        """Main scheduler loop running in background thread."""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    def _run_cleanup(self):
        """Execute the nightly cleanup job."""
        try:
            print(f"[{datetime.now()}] Running scheduled error message cleanup...")
            
            # Get the current working directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cleanup_script = os.path.join(script_dir, "nightly_error_cleanup.py")
            
            # Run the cleanup script
            result = subprocess.run([
                "python3", cleanup_script
            ], capture_output=True, text=True, cwd=script_dir)
            
            if result.returncode == 0:
                print(f"✅ Scheduled cleanup completed successfully")
                print(f"Output: {result.stdout}")
            else:
                print(f"❌ Scheduled cleanup failed with exit code {result.returncode}")
                print(f"Error: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error running scheduled cleanup: {e}")
    
    def run_manual_cleanup(self):
        """Run cleanup manually (for testing)."""
        print("Running manual cleanup...")
        self._run_cleanup()

# Global scheduler instance
error_cleanup_scheduler = ErrorCleanupScheduler()

def start_error_cleanup_scheduler():
    """Start the error cleanup scheduler (called from main.py)."""
    error_cleanup_scheduler.start()

def stop_error_cleanup_scheduler():
    """Stop the error cleanup scheduler (called from main.py)."""
    error_cleanup_scheduler.stop()

if __name__ == "__main__":
    # For testing the scheduler
    print("Testing error cleanup scheduler...")
    error_cleanup_scheduler.start()
    
    # Run manual cleanup for testing
    error_cleanup_scheduler.run_manual_cleanup()
    
    print("Scheduler test completed. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        error_cleanup_scheduler.stop()
        print("Scheduler stopped.")
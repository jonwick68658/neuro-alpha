#!/usr/bin/env python3
"""
Nightly System Error Message Cleanup
=====================================

Simple script to remove system-generated error messages from conversation history.
These messages provide no value to users and clutter conversation records.

Runs nightly at 2 AM via cron job.
Targets exact system error message patterns only.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# System error patterns (exact matches only)
SYSTEM_ERROR_PATTERNS = [
    "I apologize, but I'm experiencing technical difficulties processing your request right now.",
    "I apologize, but I'm experiencing technical difficulties. Please try again.",
    "Sorry, there was a streaming error. You can retry.",
    "Sorry, I encountered an error. Please try again.",
    "I'm having trouble responding right now.",
    "Service temporarily unavailable"
]

def get_database_connection():
    """Get PostgreSQL connection using environment variables."""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise Exception("DATABASE_URL environment variable not found")
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)

def cleanup_system_errors():
    """Remove system error messages from conversation_messages table."""
    
    print(f"[{datetime.now()}] Starting nightly error message cleanup...")
    
    conn = get_database_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        total_deleted = 0
        
        # Clean each error pattern
        for pattern in SYSTEM_ERROR_PATTERNS:
            print(f"Cleaning pattern: {pattern[:50]}...")
            
            # First, count how many will be deleted
            cur.execute("""
                SELECT COUNT(*) as count
                FROM conversation_messages 
                WHERE message_type = 'assistant' 
                  AND content = %s
            """, (pattern,))
            
            count_result = cur.fetchone()
            count = count_result['count'] if count_result else 0
            
            if count > 0:
                # Delete the error messages
                cur.execute("""
                    DELETE FROM conversation_messages 
                    WHERE message_type = 'assistant' 
                      AND content = %s
                """, (pattern,))
                
                deleted = cur.rowcount
                total_deleted += deleted
                print(f"  → Deleted {deleted} instances")
            else:
                print(f"  → No instances found")
        
        # Commit all deletions
        conn.commit()
        
        print(f"[{datetime.now()}] Cleanup completed. Total messages deleted: {total_deleted}")
        
        # Log summary for monitoring
        if total_deleted > 0:
            print(f"SUCCESS: Removed {total_deleted} system error messages from conversation history")
        else:
            print("INFO: No system error messages found to clean")
            
    except Exception as e:
        conn.rollback()
        print(f"ERROR: Cleanup failed: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

def verify_cleanup():
    """Verify no system error messages remain."""
    
    print("Verifying cleanup results...")
    
    conn = get_database_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check for any remaining error messages
        for pattern in SYSTEM_ERROR_PATTERNS:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM conversation_messages 
                WHERE message_type = 'assistant' 
                  AND content = %s
            """, (pattern,))
            
            result = cur.fetchone()
            count = result['count'] if result else 0
            
            if count > 0:
                print(f"WARNING: {count} instances of pattern still remain: {pattern[:50]}")
            
    except Exception as e:
        print(f"Verification failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Run cleanup
    cleanup_system_errors()
    
    # Verify results
    verify_cleanup()
    
    print("Nightly cleanup completed successfully")
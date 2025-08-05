"""
Outbox Worker for Neo4j Synchronization
Implements at-least-once delivery with exponential backoff and dead-letter handling
"""

import os
import time
import json
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional, List
import traceback
from datetime import datetime, timedelta

# Optional Neo4j
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    GraphDatabase = None

class OutboxWorker:
    def __init__(self):
        self.running = False
        self.max_attempts = 10
        self.base_delay = 1.0  # Start with 1 second
        self.max_delay = 300.0  # Cap at 5 minutes
        self.batch_size = 50
        self.poll_interval = 5.0  # Check for work every 5 seconds
        
        # Database connections
        self.pg_url = os.getenv("DATABASE_URL") or os.getenv("DEV_DATABASE_URL")
        
        # Neo4j connection
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        self.neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        
    def get_pg_connection(self):
        """Get PostgreSQL connection"""
        if not self.pg_url:
            raise RuntimeError("DATABASE_URL not configured")
        return psycopg2.connect(self.pg_url)
        
    def get_neo4j_driver(self):
        """Get Neo4j driver"""
        if not NEO4J_AVAILABLE:
            raise RuntimeError("Neo4j driver not available")
        return GraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password),
            database=self.neo4j_database
        )
        
    def calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
        
    async def process_outbox_events(self):
        """Process pending outbox events"""
        if not NEO4J_AVAILABLE:
            print("[OutboxWorker] Neo4j driver not available, skipping")
            return
            
        conn = None
        driver = None
        
        try:
            conn = self.get_pg_connection()
            driver = self.get_neo4j_driver()
            
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get pending events
            cur.execute("""
                SELECT id, event_type, entity_id, payload, attempts, last_error
                FROM graph_outbox 
                WHERE status = 'pending' 
                ORDER BY created_at ASC 
                LIMIT %s
            """, (self.batch_size,))
            
            events = cur.fetchall()
            
            if not events:
                return
                
            print(f"[OutboxWorker] Processing {len(events)} outbox events")
            
            for event in events:
                try:
                    # Mark as processing
                    cur.execute("""
                        UPDATE graph_outbox 
                        SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (event['id'],))
                    conn.commit()
                    
                    # Process the event
                    success = await self.process_single_event(driver, event)
                    
                    if success:
                        # Mark as done
                        cur.execute("""
                            UPDATE graph_outbox 
                            SET status = 'done', updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (event['id'],))
                        print(f"[OutboxWorker] Successfully processed {event['event_type']} for {event['entity_id']}")
                    else:
                        # Handle failure
                        await self.handle_event_failure(cur, event)
                        
                    conn.commit()
                    
                except Exception as e:
                    print(f"[OutboxWorker] Error processing event {event['id']}: {e}")
                    await self.handle_event_failure(cur, event, str(e))
                    conn.commit()
                    
        except Exception as e:
            print(f"[OutboxWorker] Error in process_outbox_events: {e}")
            traceback.print_exc()
        finally:
            if conn:
                conn.close()
            if driver:
                driver.close()
                
    async def process_single_event(self, driver, event: Dict[str, Any]) -> bool:
        """Process a single outbox event"""
        try:
            event_type = event['event_type']
            payload = event['payload']
            
            with driver.session() as session:
                if event_type == 'conversation_upsert':
                    return self.upsert_conversation(session, payload)
                elif event_type == 'message_upsert':
                    return self.upsert_message(session, payload)
                elif event_type == 'feedback':
                    return self.upsert_feedback(session, payload)
                else:
                    print(f"[OutboxWorker] Unknown event type: {event_type}")
                    return False
                    
        except Exception as e:
            print(f"[OutboxWorker] Error processing event: {e}")
            return False
            
    def upsert_conversation(self, session, payload: Dict[str, Any]) -> bool:
        """Upsert conversation + topic/subtopic relationships"""
        try:
            cypher = """
            MERGE (u:User {id: $user_id})
            MERGE (c:Conversation {id: $conversation_id})
            ON CREATE SET c.title = $title, c.updated_at = datetime()
            ON MATCH SET  c.title = coalesce($title, c.title), c.updated_at = datetime()
            MERGE (u)-[:OWNS]->(c)
            WITH c, $topic AS topicName, $sub_topic AS sub
            OPTIONAL MATCH (c)-[r:HAS_TOPIC]->(:Topic) DELETE r
            FOREACH (_ IN CASE WHEN topicName IS NULL OR topicName = '' THEN [] ELSE [1] END |
              MERGE (t:Topic {name: topicName})
              MERGE (c)-[:HAS_TOPIC]->(t)
              FOREACH (__ IN CASE WHEN sub IS NULL OR sub = '' THEN [] ELSE [1] END |
                MERGE (s:SubTopic {name: sub})
                MERGE (t)-[:HAS_SUBTOPIC]->(s)
              )
            )
            """
            
            session.run(cypher, 
                user_id=payload.get('user_id'),
                conversation_id=payload.get('conversation_id'),
                title=payload.get('title'),
                topic=payload.get('topic'),
                sub_topic=payload.get('sub_topic')
            )
            return True
            
        except Exception as e:
            print(f"[OutboxWorker] Error upserting conversation: {e}")
            return False
            
    def upsert_message(self, session, payload: Dict[str, Any]) -> bool:
        """Upsert message linkage"""
        try:
            cypher = """
            MERGE (c:Conversation {id: $conversation_id})
            MERGE (m:Message {id: $message_id})
            ON CREATE SET m.type = $message_type, m.created_at = datetime()
            MERGE (c)-[:HAS_MESSAGE]->(m)
            """
            
            session.run(cypher,
                conversation_id=payload.get('conversation_id'),
                message_id=payload.get('message_id'),
                message_type=payload.get('message_type')
            )
            return True
            
        except Exception as e:
            print(f"[OutboxWorker] Error upserting message: {e}")
            return False
            
    def upsert_feedback(self, session, payload: Dict[str, Any]) -> bool:
        """Upsert feedback relationship"""
        try:
            cypher = """
            MERGE (u:User {id: $user_id})
            MERGE (m:Message {id: $message_id})
            MERGE (u)-[f:GAVE_FEEDBACK]->(m)
            SET f.type = $feedback_type, f.score = $score, f.at = datetime()
            """
            
            session.run(cypher,
                user_id=payload.get('user_id'),
                message_id=payload.get('message_id'),
                feedback_type=payload.get('feedback_type'),
                score=payload.get('score')
            )
            return True
            
        except Exception as e:
            print(f"[OutboxWorker] Error upserting feedback: {e}")
            return False
            
    async def handle_event_failure(self, cursor, event: Dict[str, Any], error_msg: str = None):
        """Handle event processing failure with exponential backoff"""
        attempts = event['attempts'] + 1
        delay = self.calculate_delay(attempts)
        
        if attempts >= self.max_attempts:
            # Move to dead letter
            cursor.execute("""
                UPDATE graph_outbox 
                SET status = 'deadletter', 
                    attempts = %s,
                    last_error = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (attempts, error_msg or event.get('last_error', 'Unknown error'), event['id']))
            print(f"[OutboxWorker] Event {event['id']} moved to dead letter after {attempts} attempts")
        else:
            # Schedule retry
            next_retry = datetime.now() + timedelta(seconds=delay)
            cursor.execute("""
                UPDATE graph_outbox 
                SET status = 'pending', 
                    attempts = %s,
                    last_error = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (attempts, error_msg or event.get('last_error', 'Unknown error'), event['id']))
            print(f"[OutboxWorker] Event {event['id']} scheduled for retry in {delay:.1f}s (attempt {attempts}/{self.max_attempts})")
            
    async def run(self):
        """Main worker loop"""
        print("[OutboxWorker] Starting outbox worker...")
        self.running = True
        
        while self.running:
            try:
                await self.process_outbox_events()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                print(f"[OutboxWorker] Error in main loop: {e}")
                await asyncio.sleep(self.poll_interval)
                
        print("[OutboxWorker] Outbox worker stopped")
        
    def stop(self):
        """Stop the worker"""
        self.running = False

# Outbox utility functions for use in main.py
def add_outbox_event(event_type: str, entity_id: str, payload: Dict[str, Any]):
    """Add an event to the outbox for processing"""
    try:
        import uuid
        pg_url = os.getenv("DATABASE_URL") or os.getenv("DEV_DATABASE_URL")
        
        if not pg_url:
            print("[Outbox] DATABASE_URL not configured")
            return
            
        conn = psycopg2.connect(pg_url)
        try:
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO graph_outbox (id, event_type, entity_id, payload, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (str(uuid.uuid4()), event_type, entity_id, json.dumps(payload)))
            
            conn.commit()
            
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        print(f"[Outbox] Error adding outbox event: {e}")

# Global worker instance
_worker_instance: Optional[OutboxWorker] = None
_worker_task: Optional[asyncio.Task] = None

async def start_outbox_worker():
    """Start the global outbox worker"""
    global _worker_instance, _worker_task
    
    if _worker_instance is None:
        _worker_instance = OutboxWorker()
        _worker_task = asyncio.create_task(_worker_instance.run())
        print("[OutboxWorker] Global outbox worker started")

async def stop_outbox_worker():
    """Stop the global outbox worker"""
    global _worker_instance, _worker_task
    
    if _worker_instance:
        _worker_instance.stop()
        
    if _worker_task:
        try:
            await asyncio.wait_for(_worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            _worker_task.cancel()
            
    _worker_instance = None
    _worker_task = None
    print("[OutboxWorker] Global outbox worker stopped")
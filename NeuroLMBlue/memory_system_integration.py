"""
Memory System Integration
Coordinates all memory system components for seamless operation
"""

import asyncio
from typing import Dict, List, Optional
from hybrid_intelligent_memory import hybrid_intelligent_memory_system
from hybrid_background_riai import hybrid_background_riai_service
from context_detector import ContextDetector
from temporal_summarizer import TemporalSummarizer
from datetime import datetime


class MemorySystemIntegration:
    """Main integration class for the enhanced memory system"""

    def __init__(self):
        self.memory_system = hybrid_intelligent_memory_system
        self.riai_system = hybrid_background_riai_service
        self.context_detector = ContextDetector()
        self.temporal_summarizer = TemporalSummarizer()

    async def process_user_query(
            self, user_id: str, query: str,
            conversation_history: List[Dict[str, str]]) -> Dict:
        """Process user query with full memory system integration"""
        try:
            # Detect current context
            current_context = self.context_detector.detect_current_context(
                conversation_history, user_id)

            # Get relevant memories using hierarchical retrieval
            memories = await self.memory_system.retrieve_relevant_memories(
                query, user_id, current_context)

            # Get temporal summary for context
            temporal_summary = await self.temporal_summarizer.get_temporal_summary(
                user_id,
                time_range="session",
                topic=current_context['topic'],
                sub_topic=current_context['sub_topic'])

            # Prepare context for AI response
            context = {
                "relevant_memories": memories,
                "current_context": current_context,
                "temporal_summary": temporal_summary,
                "user_id": user_id
            }

            return context

        except Exception as e:
            print(f"Error processing user query: {e}")
            return {
                "relevant_memories": [],
                "current_context": {
                    "topic": "general",
                    "sub_topic": "general"
                },
                "temporal_summary": {
                    "summary": "Error generating summary"
                },
                "user_id": user_id
            }

    async def store_interaction(
            self, user_id: str, user_query: str, ai_response: str,
            conversation_history: List[Dict[str, str]]) -> bool:
        """Store interaction with full context"""
        try:
            # Detect context for this interaction
            current_context = self.context_detector.detect_current_context(
                conversation_history, user_id)

            # Store memory with context
            success = await self.memory_system.store_memory(
                user_query,
                ai_response,
                user_id,
                topic=current_context['topic'],
                sub_topic=current_context['sub_topic'],
                session_id=current_context['session_id'])

            # Trigger background RIA scoring
            # Note: The RIAI system will automatically process this in background
            pass

            return success

        except Exception as e:
            print(f"Error storing interaction: {e}")
            return False

    async def get_conversation_summary(self,
                                       user_id: str,
                                       time_range: str = "session") -> Dict:
        """Get comprehensive conversation summary"""
        try:
            # Get temporal summary
            temporal_summary = await self.temporal_summarizer.get_temporal_summary(
                user_id, time_range=time_range)

            # Get conversation progression for active topics
            active_topics = await self._get_active_topics(user_id)

            progressions = {}
            for topic in active_topics:
                progression = await self.temporal_summarizer.get_conversation_progression(
                    user_id, topic['topic'], topic.get('sub_topic'))
                progressions[
                    f"{topic['topic']}/{topic.get('sub_topic', 'general')}"] = progression

            return {
                "temporal_summary": temporal_summary,
                "conversation_progressions": progressions,
                "active_topics": active_topics
            }

        except Exception as e:
            print(f"Error getting conversation summary: {e}")
            return {"error": str(e)}

    async def _get_active_topics(self, user_id: str) -> List[Dict]:
        """Get active topics for user"""
        try:
            conn = self.memory_system.get_pg_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT DISTINCT topic, sub_topic, COUNT(*) as count
                FROM intelligent_memories
                WHERE user_id = %s 
                AND created_at >= NOW() - INTERVAL '7 days'
                GROUP BY topic, sub_topic
                ORDER BY count DESC
                LIMIT 10
            """, (user_id, ))

            topics = [{
                "topic": row[0],
                "sub_topic": row[1],
                "count": row[2]
            } for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return topics

        except Exception as e:
            print(f"Error getting active topics: {e}")
            return []


# Global instance
memory_system_integration = MemorySystemIntegration()


# Convenience functions for direct usage
async def process_query(user_id: str, query: str,
                        conversation_history: List[Dict[str, str]]) -> Dict:
    """Process user query with memory integration"""
    return await memory_system_integration.process_user_query(
        user_id, query, conversation_history)


async def store_interaction(
        user_id: str, user_query: str, ai_response: str,
        conversation_history: List[Dict[str, str]]) -> bool:
    """Store interaction with context"""
    return await memory_system_integration.store_interaction(
        user_id, user_query, ai_response, conversation_history)


async def get_summary(user_id: str, time_range: str = "session") -> Dict:
    """Get conversation summary"""
    return await memory_system_integration.get_conversation_summary(
        user_id, time_range)

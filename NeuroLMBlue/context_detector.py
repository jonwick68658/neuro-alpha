"""
Context Detection Service
Detects conversation topics and sub-topics for hierarchical memory retrieval
"""

import re
import json
from typing import Dict, List, Optional
from datetime import datetime
import openai
import os

class ContextDetector:
    """Detects and manages conversation context"""

    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def detect_current_context(self, conversation: List[Dict[str, str]], user_id: str) -> Dict[str, str]:
        """Detect current conversation context"""
        try:
            # Build conversation text
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in conversation[-5:]  # Last 5 messages
            ])

            # Create prompt for context detection
            prompt = f"""
            Analyze this conversation and extract:
            1. Main topic (broad category like "technology", "health", "work", etc.)
            2. Sub-topic (specific focus like "python programming", "sleep research", "project management", etc.)
            3. Session identifier (unique for this conversation session)

            Conversation:
            {conversation_text}

            Respond with JSON format:
            {{
                "topic": "main topic",
                "sub_topic": "specific sub-topic",
                "session_id": "session_identifier"
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )

            try:
                content = response.choices[0].message.content
                if content:
                    result = json.loads(content)
                    return {
                        "topic": result.get("topic", "general"),
                        "sub_topic": result.get("sub_topic", "general"),
                        "session_id": result.get("session_id", f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    }
                else:
                    return self._simple_context_detection(conversation_text, user_id)
            except (json.JSONDecodeError, AttributeError):
                # Fallback to simple detection
                return self._simple_context_detection(conversation_text, user_id)

        except Exception as e:
            print(f"Error detecting context: {e}")
            return self._simple_context_detection("", user_id)

    def _simple_context_detection(self, text: str, user_id: str) -> Dict[str, str]:
        """Simple fallback context detection"""
        text_lower = text.lower()

        # Topic detection patterns
        topic_patterns = {
            "technology": ["python", "javascript", "code", "programming", "ai", "machine learning", "neural", "algorithm"],
            "health": ["sleep", "health", "medical", "doctor", "exercise", "diet", "wellness"],
            "work": ["project", "meeting", "deadline", "manager", "client", "task", "work"],
            "personal": ["family", "friend", "weekend", "hobby", "travel", "home"],
            "education": ["learning", "course", "study", "exam", "university", "class"]
        }

        # Sub-topic detection
        sub_topic_patterns = {
            "python": ["python", "django", "flask", "pandas", "numpy"],
            "javascript": ["javascript", "react", "node", "vue", "angular"],
            "sleep": ["sleep", "insomnia", "rest", "bedtime", "circadian"],
            "project": ["project", "planning", "timeline", "deliverable", "milestone"]
        }

        detected_topic = "general"
        detected_sub_topic = "general"

        # Detect topic
        for topic, keywords in topic_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_topic = topic
                break

        # Detect sub-topic
        for sub_topic, keywords in sub_topic_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_sub_topic = sub_topic
                break

        return {
            "topic": detected_topic,
            "sub_topic": detected_sub_topic,
            "session_id": f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }

    def get_context_hierarchy(self, topic: str, sub_topic: str) -> Dict[str, List[str]]:
        """Get context hierarchy for bottom-up retrieval"""
        return {
            "current": [sub_topic],
            "topic": [topic],
            "general": ["general"]
        }
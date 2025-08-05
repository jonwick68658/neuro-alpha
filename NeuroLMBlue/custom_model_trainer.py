"""
Custom Model Training System
Exports user interaction data for fine-tuning and manages training workflows
"""

import json
import os
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import openai
from dataclasses import dataclass

@dataclass
class TrainingExample:
    """Represents a single training example for fine-tuning"""
    system_prompt: str
    user_message: str
    assistant_response: str
    quality_score: Optional[float] = None
    conversation_id: Optional[str] = None
    timestamp: Optional[datetime] = None

class CustomModelTrainer:
    """System for training custom models from user interaction data"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.min_quality_score = 0.7  # Only use high-quality interactions
        self.min_examples = 100  # Minimum examples needed for training
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    async def extract_training_data(self, user_id: str, days_back: int = 30) -> List[TrainingExample]:
        """Extract high-quality training examples from user interactions"""
        examples = []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get conversations with quality scores
                cursor.execute("""
                    SELECT 
                        m.content,
                        m.message_type,
                        m.conversation_id,
                        m.timestamp,
                        m.quality_score,
                        m.final_quality_score,
                        c.topic,
                        c.subtopic
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE m.user_id = %s
                        AND m.timestamp >= %s
                        AND m.quality_score IS NOT NULL
                        AND m.final_quality_score >= %s
                    ORDER BY m.conversation_id, m.timestamp
                """, (user_id, datetime.now() - timedelta(days=days_back), self.min_quality_score))
                
                messages = cursor.fetchall()
                
                # Group messages by conversation
                conversations = {}
                for msg in messages:
                    conv_id = msg['conversation_id']
                    if conv_id not in conversations:
                        conversations[conv_id] = {
                            'topic': msg['topic'],
                            'subtopic': msg['subtopic'],
                            'messages': []
                        }
                    conversations[conv_id]['messages'].append(msg)
                
                # Extract training examples from conversations
                for conv_id, conv_data in conversations.items():
                    messages = conv_data['messages']
                    
                    # Create system prompt based on topic/subtopic
                    system_prompt = self._create_system_prompt(conv_data['topic'], conv_data['subtopic'])
                    
                    # Extract user-assistant pairs
                    for i in range(len(messages) - 1):
                        current_msg = messages[i]
                        next_msg = messages[i + 1]
                        
                        if (current_msg['message_type'] == 'user' and 
                            next_msg['message_type'] == 'assistant' and
                            next_msg['final_quality_score'] >= self.min_quality_score):
                            
                            example = TrainingExample(
                                system_prompt=system_prompt,
                                user_message=current_msg['content'],
                                assistant_response=next_msg['content'],
                                quality_score=next_msg['final_quality_score'],
                                conversation_id=conv_id,
                                timestamp=next_msg['timestamp']
                            )
                            examples.append(example)
                
        except Exception as e:
            print(f"Error extracting training data: {e}")
            
        return examples
    
    def _create_system_prompt(self, topic: Optional[str], subtopic: Optional[str]) -> str:
        """Create system prompt based on conversation topic"""
        base_prompt = "You are an intelligent AI assistant with access to conversation history and context."
        
        if topic:
            if topic == "Programming & Software Development":
                base_prompt += " You specialize in programming, code review, debugging, and software development best practices."
            elif topic == "Creative & Writing":
                base_prompt += " You excel at creative writing, storytelling, content creation, and artistic expression."
            elif topic == "Business & Professional":
                base_prompt += " You provide expert business advice, professional communication, and strategic insights."
            elif topic == "Education & Learning":
                base_prompt += " You are an educational mentor who explains complex topics clearly and provides learning guidance."
            elif topic == "Technology & Innovation":
                base_prompt += " You stay current with technology trends and provide insights on innovation and tech developments."
        
        if subtopic:
            base_prompt += f" The current conversation focuses on {subtopic}."
            
        base_prompt += " Provide helpful, accurate, and contextually relevant responses."
        
        return base_prompt
    
    def export_jsonl(self, examples: List[TrainingExample], filename: str) -> bool:
        """Export training examples to JSONL format for OpenAI fine-tuning"""
        try:
            with open(filename, 'w') as f:
                for example in examples:
                    training_record = {
                        "messages": [
                            {"role": "system", "content": example.system_prompt},
                            {"role": "user", "content": example.user_message},
                            {"role": "assistant", "content": example.assistant_response}
                        ]
                    }
                    f.write(json.dumps(training_record) + '\n')
            
            print(f"✅ Exported {len(examples)} training examples to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting JSONL: {e}")
            return False
    
    async def prepare_training_data(self, user_id: str, output_file: str = "training_data.jsonl") -> Dict:
        """Prepare training data for a specific user"""
        print(f"📊 Extracting training data for user {user_id}...")
        
        # Extract training examples
        examples = await self.extract_training_data(user_id)
        
        if len(examples) < self.min_examples:
            return {
                "status": "insufficient_data",
                "examples_found": len(examples),
                "min_required": self.min_examples,
                "message": f"Need at least {self.min_examples} high-quality examples for training"
            }
        
        # Sort by quality score (highest first)
        examples.sort(key=lambda x: x.quality_score or 0, reverse=True)
        
        # Split into train/validation (80/20)
        split_idx = int(len(examples) * 0.8)
        train_examples = examples[:split_idx]
        val_examples = examples[split_idx:]
        
        # Export training data
        train_file = f"train_{output_file}"
        val_file = f"val_{output_file}"
        
        train_success = self.export_jsonl(train_examples, train_file)
        val_success = self.export_jsonl(val_examples, val_file)
        
        if train_success and val_success:
            return {
                "status": "success",
                "total_examples": len(examples),
                "train_examples": len(train_examples),
                "val_examples": len(val_examples),
                "avg_quality_score": sum(ex.quality_score for ex in examples) / len(examples),
                "train_file": train_file,
                "val_file": val_file
            }
        else:
            return {
                "status": "export_failed",
                "message": "Failed to export training data"
            }
    
    async def analyze_training_potential(self, user_id: str) -> Dict:
        """Analyze whether a user has sufficient data for training"""
        examples = await self.extract_training_data(user_id)
        
        # Quality analysis
        quality_distribution = {}
        topic_distribution = {}
        
        for example in examples:
            # Quality score buckets
            score_bucket = f"{int(example.quality_score * 10) / 10:.1f}"
            quality_distribution[score_bucket] = quality_distribution.get(score_bucket, 0) + 1
        
        return {
            "total_examples": len(examples),
            "training_ready": len(examples) >= self.min_examples,
            "quality_distribution": quality_distribution,
            "avg_quality": sum(ex.quality_score for ex in examples) / len(examples) if examples else 0,
            "date_range": {
                "earliest": min(ex.timestamp for ex in examples).isoformat() if examples else None,
                "latest": max(ex.timestamp for ex in examples).isoformat() if examples else None
            }
        }
    
    async def fine_tune_model(self, train_file: str, val_file: str, model_name: str = "gpt-4o-mini-2024-07-18") -> Dict:
        """Start OpenAI fine-tuning job"""
        try:
            # Upload training file
            print(f"📤 Uploading training file: {train_file}")
            with open(train_file, 'rb') as f:
                training_file = self.openai_client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            
            # Upload validation file
            print(f"📤 Uploading validation file: {val_file}")
            with open(val_file, 'rb') as f:
                validation_file = self.openai_client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            
            # Create fine-tuning job
            print(f"🚀 Starting fine-tuning job with model: {model_name}")
            fine_tuning_job = self.openai_client.fine_tuning.jobs.create(
                training_file=training_file.id,
                validation_file=validation_file.id,
                model=model_name,
                hyperparameters={
                    "n_epochs": 3,  # Adjust based on data size
                    "batch_size": 1,
                    "learning_rate_multiplier": 0.1
                }
            )
            
            return {
                "status": "started",
                "job_id": fine_tuning_job.id,
                "model": model_name,
                "training_file_id": training_file.id,
                "validation_file_id": validation_file.id
            }
            
        except Exception as e:
            print(f"❌ Fine-tuning error: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def check_training_status(self, job_id: str) -> Dict:
        """Check status of fine-tuning job"""
        try:
            job = self.openai_client.fine_tuning.jobs.retrieve(job_id)
            
            result = {
                "status": job.status,
                "model": job.model,
                "created_at": job.created_at,
                "finished_at": job.finished_at,
                "trained_tokens": job.trained_tokens,
                "result_files": job.result_files
            }
            
            if job.status == "succeeded":
                result["fine_tuned_model"] = job.fine_tuned_model
            elif job.status == "failed":
                result["error"] = job.error
                
            return result
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def get_all_users_training_potential(self) -> List[Dict]:
        """Get training potential for all users"""
        results = []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all users with messages
                cursor.execute("""
                    SELECT DISTINCT user_id 
                    FROM messages 
                    WHERE quality_score IS NOT NULL
                """)
                
                users = cursor.fetchall()
                
                for user_row in users:
                    user_id = user_row['user_id']
                    analysis = await self.analyze_training_potential(user_id)
                    analysis['user_id'] = user_id
                    results.append(analysis)
                    
        except Exception as e:
            print(f"Error analyzing users: {e}")
            
        return results

# Global instance
custom_model_trainer = CustomModelTrainer()

async def analyze_user_training_potential(user_id: str) -> Dict:
    """Analyze training potential for a specific user"""
    return await custom_model_trainer.analyze_training_potential(user_id)

async def prepare_user_training_data(user_id: str) -> Dict:
    """Prepare training data for a specific user"""
    return await custom_model_trainer.prepare_training_data(user_id)

async def start_fine_tuning(train_file: str, val_file: str) -> Dict:
    """Start fine-tuning process"""
    return await custom_model_trainer.fine_tune_model(train_file, val_file)

async def check_fine_tuning_status(job_id: str) -> Dict:
    """Check fine-tuning job status"""
    return await custom_model_trainer.check_training_status(job_id)
"""
Hybrid Background RIAI Service (Production-Ready, Moat-Aligned)

Purpose:
- Robust, cache-aware R(t) evaluation pipeline for assistant responses.
- Clean separation of signals:
  - R(t): model-based response quality (1..10, cached by content hash and evaluator_version)
  - H(t): explicit human feedback from UI buttons (great response, not helpful, copy, that worked)
  - Final score: f(R(t), H(t)) computed centrally by HybridIntelligentMemorySystem
- Bounded, resilient concurrency with backoff and observability.
- Optional post-hoc micro-adjustment using next user reply, only if NO explicit human feedback exists.
- SDK/Service reliability: deterministic, auditable, and stable.

Compatibility:
- Works with the new `hybrid_intelligent_memory.py` replacement you received.
- Does not change DB schema; assumes tables: intelligent_memories, response_cache.
- Assumes `hybrid_intelligent_memory.hybrid_intelligent_memory_system` exposes:
  - update_memory_quality_score(memory_id, r_t_score)
  - update_final_quality_score(memory_id, user_id)

Environment:
- RIAI_BATCH_SIZE (default 20)
- RIAI_PROCESS_INTERVAL_SEC (default 1800)
- RIAI_MAX_CONCURRENCY (default 5)
- RIAI_ENABLE_USER_FEEDBACK_ADJUSTMENT (default "true")
- RIAI_EVALUATION_MODEL (default "mistralai/mistral-small-3.2-24b-instruct")
- RIAI_EVALUATOR_VERSION (default "v1")
- DATABASE_URL
- Optional per-button score overrides:
  - FEEDBACK_SCORE_GREAT (default 9.0)
  - FEEDBACK_SCORE_WORKED (default 10.0)
  - FEEDBACK_SCORE_COPY (default 7.0)
  - FEEDBACK_SCORE_NOT_HELPFUL (default 2.0)

Notes:
- Cites relevant guidance on stateful memory architectures and persistent evaluation pipelines:
  - Stateful continuity benefits in multi-turn systems: [dev.to](https://dev.to/tlrag/an-architectural-paradigm-for-stateful-learning-and-cost-efficient-ai-3jg3)
  - Externalizing long-term memory cleanly (process-level guidance): [community.openai.com](https://community.openai.com/t/building-your-external-memory-system-how-to-when-user-memory-is-full/1287792#post_1)
  - Multi-agent memory systems trend and local privacy: [arxiv.org](https://arxiv.org/abs/2507.07957)
"""

import asyncio
import hashlib
import os
import re
import time
from typing import List, Dict, Optional, Any, Union, Tuple, Callable

import psycopg2
from psycopg2.extras import RealDictCursor
import httpx

import hybrid_intelligent_memory  # module import to access the global instance safely
from model_services import ModelService


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name, str(default)).lower()
    return val in ("1", "true", "yes", "y", "on")


class HybridBackgroundRIAIService:
    """Production background R(t) evaluator with cache, bounded concurrency, and feedback-aware adjustment."""

    def __init__(self):
        # Access the global instance via the module to avoid circular timing issues
        self.memory_system = hybrid_intelligent_memory.hybrid_intelligent_memory_system
        self.model_service = ModelService()
        self.is_running = False

        # Configurable settings via env
        self.batch_size = _env_int("RIAI_BATCH_SIZE", 20)
        self.process_interval = _env_int("RIAI_PROCESS_INTERVAL_SEC", 1800)  # 30 min
        self.max_concurrency = _env_int("RIAI_MAX_CONCURRENCY", 5)
        self.enable_user_feedback_adjustment = _env_bool("RIAI_ENABLE_USER_FEEDBACK_ADJUSTMENT", True)

        # Model and evaluator versioning
        self.evaluation_model = os.getenv("RIAI_EVALUATION_MODEL", "mistralai/mistral-small-3.2-24b-instruct")
        # Bump when prompt/model changes to avoid stale cache usage
        self.evaluator_version = os.getenv("RIAI_EVALUATOR_VERSION", "v1")

        # UI button to score mapping (H(t) is handled elsewhere; this is for reference/backfills)
        self.feedback_scores = {
            "great_response": _env_float("FEEDBACK_SCORE_GREAT", 9.0),
            "that_worked": _env_float("FEEDBACK_SCORE_WORKED", 10.0),
            "copied": _env_float("FEEDBACK_SCORE_COPY", 7.0),
            "not_helpful": _env_float("FEEDBACK_SCORE_NOT_HELPFUL", 2.0),
        }

        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            print("WARN RIAI: DATABASE_URL is not set. DB operations will fail.")

        # Semaphore for bounded concurrency
        self._sem = asyncio.Semaphore(self.max_concurrency)

        # Backoff settings
        self._backoff_initial = 0.8
        self._backoff_max = 8.0
        self._backoff_factor = 2.0

    # ----------------- DB connection helpers -----------------

    def get_connection(self):
        """Get PostgreSQL connection (sync)"""
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg2.connect(self.database_url)

    async def _db_query(self, func: Callable, *args, **kwargs):
        """Run a DB operation in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(func, *args, **kwargs)

    # ----------------- Cache operations -----------------

    def generate_response_hash(self, content: str) -> str:
        """Generate hash for response content to enable caching (md5 ok for non-crypto)"""
        return hashlib.md5((content or "").encode()).hexdigest()

    def _db_get_cached_score_sync(self, response_hash: str, evaluator_version: str) -> Optional[float]:
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT r_t_score FROM response_cache
                WHERE response_hash = %s AND evaluator_version = %s
                """,
                (response_hash, evaluator_version),
            )
            row = cursor.fetchone()
            return row["r_t_score"] if row else None
        except psycopg2.Error as e:
            print(f"WARN RIAI cache read error: {e}")
            return None
        finally:
            try:
                if cursor:
                    cursor.close()
            except psycopg2.Error:
                pass
            try:
                if conn:
                    conn.close()
            except psycopg2.Error:
                pass

    async def get_cached_score(self, response_hash: str, evaluator_version: str) -> Optional[float]:
        return await self._db_query(self._db_get_cached_score_sync, response_hash, evaluator_version)

    def _db_store_cached_score_sync(self, response_hash: str, evaluator_version: str, r_t_score: float):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO response_cache (response_hash, evaluator_version, r_t_score, cached_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (response_hash, evaluator_version)
                DO UPDATE SET r_t_score = EXCLUDED.r_t_score,
                              cached_at = CURRENT_TIMESTAMP
                """,
                (response_hash, evaluator_version, r_t_score),
            )
            conn.commit()
        except psycopg2.Error as e:
            print(f"WARN RIAI cache write error: {e}")
        finally:
            try:
                if cursor:
                    cursor.close()
            except psycopg2.Error:
                pass
            try:
                if conn:
                    conn.close()
            except psycopg2.Error:
                pass

    async def store_cached_score(self, response_hash: str, evaluator_version: str, r_t_score: float):
        await self._db_query(self._db_store_cached_score_sync, response_hash, evaluator_version, r_t_score)

    # ----------------- Work discovery -----------------

    def _db_get_unscored_memories_sync(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT id, content, user_id, created_at AS timestamp, conversation_id, message_id,
                       quality_score, human_feedback_score
                FROM intelligent_memories
                WHERE message_type = 'assistant'
                  AND quality_score IS NULL
                  AND content IS NOT NULL
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            memories: List[Dict[str, Any]] = []
            for row in rows:
                memories.append(
                    {
                        "memory_id": str(row["id"]),
                        "content": row["content"],
                        "user_id": row["user_id"],
                        "timestamp": row["timestamp"],
                        "conversation_id": row.get("conversation_id"),
                        "message_id": row.get("message_id"),
                        "quality_score": row.get("quality_score"),
                        "human_feedback_score": row.get("human_feedback_score"),
                    }
                )
            return memories
        except psycopg2.Error as e:
            print(f"WARN RIAI get_unscored_memories error: {e}")
            return []
        finally:
            try:
                if cursor:
                    cursor.close()
            except psycopg2.Error:
                pass
            try:
                if conn:
                    conn.close()
            except psycopg2.Error:
                pass

    async def get_unscored_memories(self, limit: int = 20) -> List[Dict[str, Any]]:
        return await self._db_query(self._db_get_unscored_memories_sync, limit)

    # ----------------- User reply lookup -----------------

    def _db_get_recent_user_reply_sync(
        self,
        conversation_id: Optional[str],
        after_message_id: Optional[int],
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the next user message in the same conversation after the assistant message_id, if available.
        Falls back to most recent user message in that conversation.
        """
        if not conversation_id:
            return None
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            row = None
            if after_message_id is not None:
                cursor.execute(
                    """
                    SELECT id, content, created_at
                    FROM intelligent_memories
                    WHERE conversation_id = %s
                      AND user_id = %s
                      AND message_type = 'user'
                      AND message_id > %s
                    ORDER BY message_id ASC
                    LIMIT 1
                    """,
                    (conversation_id, user_id, after_message_id),
                )
                row = cursor.fetchone()

            if not row:
                cursor.execute(
                    """
                    SELECT id, content, created_at
                    FROM intelligent_memories
                    WHERE conversation_id = %s
                      AND user_id = %s
                      AND message_type = 'user'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (conversation_id, user_id),
                )
                row = cursor.fetchone()

            if row and row.get("content"):
                return {"id": str(row["id"]), "content": row["content"], "created_at": row["created_at"]}
            return None
        except psycopg2.Error as e:
            print(f"WARN RIAI get_recent_user_reply error: {e}")
            return None
        finally:
            try:
                if cursor:
                    cursor.close()
            except psycopg2.Error:
                pass
            try:
                if conn:
                    conn.close()
            except psycopg2.Error:
                pass

    async def get_recent_user_reply(
        self, conversation_id: Optional[str], after_message_id: Optional[int], user_id: str
    ) -> Optional[Dict[str, Any]]:
        return await self._db_query(self._db_get_recent_user_reply_sync, conversation_id, after_message_id, user_id)

    # ----------------- Utility: check existing human feedback -----------------

    def _db_has_human_feedback_sync(self, memory_id: str) -> bool:
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT human_feedback_score
                FROM intelligent_memories
                WHERE id = %s
                """,
                (memory_id,),
            )
            row = cursor.fetchone()
            if not row:
                return False
            return row[0] is not None
        except psycopg2.Error as e:
            print(f"WARN RIAI has_human_feedback error: {e}")
            return False
        finally:
            try:
                if cursor:
                    cursor.close()
            except psycopg2.Error:
                pass
            try:
                if conn:
                    conn.close()
            except psycopg2.Error:
                pass

    async def has_human_feedback(self, memory_id: str) -> bool:
        return await self._db_query(self._db_has_human_feedback_sync, memory_id)

    # ----------------- User feedback heuristics -----------------

    def simple_user_feedback_analysis(self, user_text: str) -> Dict[str, Any]:
        """
        Heuristic analysis of user reply sentiment and feedback cues.
        Returns dict with sentiment in {-1, 0, +1}, caps_ratio, signals, and suggested delta.
        Only used when there is NO explicit human feedback for the memory.
        """
        if not user_text:
            return {"sentiment": 0, "caps_ratio": 0.0, "signals": [], "delta": 0.0}

        text = user_text.strip()
        text_lower = text.lower()
        words = re.findall(r"[A-Za-z]+", text)
        caps_words = [w for w in words if len(w) >= 2 and w.isupper()]
        caps_ratio = (len(caps_words) / max(1, len(words))) if words else 0.0

        positive_cues = [
            "thank",
            "thanks",
            "great",
            "awesome",
            "helpful",
            "perfect",
            "works",
            "good job",
            "nice",
            "that fixed it",
            "this solved it",
        ]
        negative_cues = [
            "not helpful",
            "wrong",
            "bad",
            "useless",
            "frustrat",
            "angry",
            "annoy",
            "broken",
            "doesn't work",
            "doesnt work",
            "fail",
            "didn't work",
            "didnt work",
        ]
        question_cues = ["?", "how do i", "why", "what about", "does this", "can you"]
        frustration_caps = caps_ratio >= 0.3

        signals: List[str] = []
        sentiment = 0
        delta = 0.0

        if any(cue in text_lower for cue in positive_cues):
            signals.append("positive_ack")
            sentiment += 1
            delta += 0.7

        if any(cue in text_lower for cue in negative_cues) or frustration_caps:
            signals.append("frustration")
            sentiment -= 1
            delta -= 1.0 if frustration_caps else 0.7

        if any(cue in text_lower for cue in question_cues):
            signals.append("followup_question")
            delta -= 0.2

        # Very short user reply like "ok", "k"
        if len(text) <= 3 and text_lower in {"k", "ok"}:
            signals.append("short_ack")
            delta -= 0.2

        # Clamp delta for stability
        delta = max(-2.0, min(1.5, delta))
        sentiment = max(-1, min(1, sentiment))

        return {"sentiment": sentiment, "caps_ratio": caps_ratio, "signals": signals, "delta": delta}

    async def classify_issue_with_model(self, ai_response: str, user_reply: str) -> Optional[str]:
        """
        Optional: ask the model to briefly classify the issue when negative user sentiment is detected.
        Outputs one of: inaccuracy, unclear, insufficient detail, off-topic, tone, other.
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a post-hoc evaluator. Given an AI response and the user's follow-up reply, "
                        "output a single short reason tag for why the user might be unhappy. Choose only one from: "
                        "inaccuracy, unclear, insufficient detail, off-topic, tone, other. Respond with just the tag."
                    ),
                },
                {
                    "role": "user",
                    "content": f"AI response:\n{ai_response}\n\nUser reply:\n{user_reply}\n\nReason tag:",
                },
            ]
            # Simple backoff on transient errors
            for attempt in range(3):
                try:
                    text = await self.model_service.chat_completion(messages=messages, model=self.evaluation_model)
                    tag = (text or "").strip().lower()
                    m = re.search(r"(inaccuracy|unclear|insufficient detail|off-topic|tone|other)", tag)
                    if m:
                        return m.group(1)
                    return None
                except (httpx.HTTPError, asyncio.TimeoutError) as e:
                    delay = min(self._backoff_initial * (self._backoff_factor ** attempt), self._backoff_max)
                    print(f"WARN RIAI classify_issue retry {attempt+1}: {e}; sleeping {delay:.2f}s")
                    await asyncio.sleep(delay)
            return None
        except Exception as e:
            print(f"WARN RIAI classify_issue_with_model error: {e}")
            return None

    # ----------------- Evaluation core -----------------

    def _parse_score(self, text: str) -> Optional[float]:
        if not text:
            return None
        s = text.strip()
        try:
            return float(s)
        except ValueError:
            pass
        nums = re.findall(r"\d+\.?\d*", s)
        if nums:
            try:
                return float(nums[0])
            except ValueError:
                return None
        return None

    async def apply_user_feedback_adjustment(self, memory: Dict[str, Any], base_score: float) -> float:
        """
        If enabled and there is NO explicit human feedback on this memory, look at the next user reply and adjust.
        Small bounded adjustments to avoid volatility.
        """
        if not self.enable_user_feedback_adjustment:
            return base_score

        # Skip if explicit human feedback already exists
        try:
            if await self.has_human_feedback(memory["memory_id"]):
                return base_score
        except Exception:
            # If we can't check, fail safe: don't adjust
            return base_score

        try:
            user_reply = await self.get_recent_user_reply(
                conversation_id=memory.get("conversation_id"),
                after_message_id=memory.get("message_id"),
                user_id=memory["user_id"],
            )
            if not user_reply or not user_reply.get("content"):
                return base_score

            analysis = self.simple_user_feedback_analysis(user_reply["content"])
            delta = analysis["delta"]

            if analysis["sentiment"] < 0:
                _ = await self.classify_issue_with_model(memory.get("content") or "", user_reply["content"])

            adjusted = base_score + delta
            return max(1.0, min(10.0, adjusted))
        except (psycopg2.Error, httpx.HTTPError, asyncio.TimeoutError, KeyError, ValueError) as e:
            print(f"WARN RIAI user feedback adjustment error: {e}")
            return base_score

    async def evaluate_single(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single memory; incorporate cache and optional user-feedback-based micro-adjustment.
        Returns result dict with cached flag and r_t_score.
        """
        async with self._sem:
            content = memory.get("content") or ""
            if not content.strip():
                return {
                    "memory_id": memory["memory_id"],
                    "user_id": memory["user_id"],
                    "r_t_score": 5.0,
                    "cached": False,
                }

            response_hash = self.generate_response_hash(content)

            # 1) Cache check
            cached_score = await self.get_cached_score(response_hash, self.evaluator_version)
            if cached_score is not None:
                adjusted = await self.apply_user_feedback_adjustment(memory, cached_score)
                return {
                    "memory_id": memory["memory_id"],
                    "user_id": memory["user_id"],
                    "r_t_score": adjusted,
                    "cached": True,
                }

            # 2) Model evaluation with simple backoff
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI response quality evaluator. Rate the quality of AI responses strictly from 1 to 10. "
                        "Consider accuracy, helpfulness, clarity, and completeness. "
                        "Respond with only a single number (integer or one decimal)."
                    ),
                },
                {"role": "user", "content": f"Rate this AI response:\n\n{content}\n\nScore:"},
            ]

            score = None
            for attempt in range(3):
                try:
                    response_text = await self.model_service.chat_completion(messages=messages, model=self.evaluation_model)
                    score = self._parse_score(response_text)
                    if score is not None:
                        break
                    # Reprompt once if needed on the first failure to parse
                    reprompt = [
                        {"role": "system", "content": "Output only a number 1-10. No extra text."},
                        {"role": "user", "content": content},
                    ]
                    response_text2 = await self.model_service.chat_completion(messages=reprompt, model=self.evaluation_model)
                    score = self._parse_score(response_text2)
                    if score is not None:
                        break
                except (httpx.HTTPError, asyncio.TimeoutError) as e:
                    delay = min(self._backoff_initial * (self._backoff_factor ** attempt), self._backoff_max)
                    print(f"WARN RIAI evaluator retry {attempt+1}: {e}; sleeping {delay:.2f}s")
                    await asyncio.sleep(delay)
                except (KeyError, ValueError) as e:
                    print(f"WARN RIAI evaluator parsing error: {e}")
                    break

            r_t_score = score if score is not None else 5.0
            r_t_score = max(1.0, min(10.0, r_t_score))

            # 3) Cache store
            await self.store_cached_score(response_hash, self.evaluator_version, r_t_score)

            # 4) User feedback micro-adjustment (if no explicit H(t))
            r_t_score = await self.apply_user_feedback_adjustment(memory, r_t_score)

            return {
                "memory_id": memory["memory_id"],
                "user_id": memory["user_id"],
                "r_t_score": r_t_score,
                "cached": False,
            }

    async def evaluate_batch(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate a batch of memories using bounded concurrency."""
        tasks = [self.evaluate_single(m) for m in memories]
        results: List[Union[Dict[str, Any], BaseException]] = await asyncio.gather(*tasks, return_exceptions=True)

        evaluation_results: List[Dict[str, Any]] = []
        for m, res in zip(memories, results):
            if isinstance(res, BaseException):
                print(f"WARN RIAI error evaluating memory {m.get('memory_id')}: {res}")
                evaluation_results.append(
                    {
                        "memory_id": m.get("memory_id"),
                        "user_id": m.get("user_id"),
                        "r_t_score": 5.0,
                        "cached": False,
                    }
                )
            else:
                evaluation_results.append(res)
        return evaluation_results

    # ----------------- Persist results -----------------

    async def update_memory_scores(self, evaluation_results: List[Dict[str, Any]]):
        """Update memories with R(t) scores, then compute final_score with the memory system."""
        for result in evaluation_results:
            memory_id = result["memory_id"]
            user_id = result["user_id"]
            r_t_score = result["r_t_score"]

            success = await self.memory_system.update_memory_quality_score(memory_id, r_t_score)
            if success:
                await self.memory_system.update_final_quality_score(memory_id, user_id)

    # ----------------- Batch processing loop -----------------

    async def process_batch(self) -> Dict[str, int]:
        """Process a batch of unscored memories"""
        start_time = time.time()
        try:
            memories = await self.get_unscored_memories(self.batch_size)
            if not memories:
                print("RIAI: No memories to evaluate")
                return {"total_found": 0, "cached": 0, "evaluated": 0}

            evaluation_results = await self.evaluate_batch(memories)
            await self.update_memory_scores(evaluation_results)

            cached_count = sum(1 for r in evaluation_results if r.get("cached"))
            evaluated_count = sum(1 for r in evaluation_results if not r.get("cached"))

            elapsed = time.time() - start_time
            print(
                f"RIAI: Batch processed in {elapsed:.2f}s: {len(memories)} total, {cached_count} cached, {evaluated_count} evaluated"
            )
            return {"total_found": len(memories), "cached": cached_count, "evaluated": evaluated_count}
        except (psycopg2.Error, httpx.HTTPError, asyncio.TimeoutError, KeyError, ValueError) as e:
            print(f"WARN RIAI process_batch error: {e}")
            return {"total_found": 0, "cached": 0, "evaluated": 0}

    async def start_background_service(self):
        """Start the background R(t) evaluation service"""
        if self.is_running:
            print("RIAI: Service already running")
            return
        self.is_running = True
        print("✅ RIAI background service starting...")
        # Initial warm-up to avoid hammering cold services
        await asyncio.sleep(45)
        print("RIAI: Warm-up complete; beginning batch processing loop.")

        while self.is_running:
            try:
                await self.process_batch()
                await asyncio.sleep(self.process_interval)
            except asyncio.CancelledError:
                print("RIAI: Background service cancelled")
                break
            except (psycopg2.Error, httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError) as e:
                print(f"WARN RIAI background loop error: {e}")
                print("RIAI: continuing after error")
                await asyncio.sleep(60)

        print("RIAI: Background service stopped")

    def stop_background_service(self):
        """Stop the background R(t) evaluation service"""
        self.is_running = False
        print("RIAI: Stop requested")

    def close(self):
        """Close connections"""
        self.stop_background_service()
        if hasattr(self, "memory_system"):
            self.memory_system.close()


# Global instance
hybrid_background_riai_service = HybridBackgroundRIAIService()


# Service management functions
async def start_hybrid_background_riai():
    """Start the hybrid background RIAI service"""
    global hybrid_background_riai_service
    if not hybrid_background_riai_service.is_running:
        await hybrid_background_riai_service.start_background_service()


async def stop_hybrid_background_riai():
    """Stop the hybrid background RIAI service"""
    global hybrid_background_riai_service
    hybrid_background_riai_service.stop_background_service()


async def process_hybrid_riai_batch():
    """Process a single batch of R(t) evaluations"""
    global hybrid_background_riai_service
    return await hybrid_background_riai_service.process_batch()
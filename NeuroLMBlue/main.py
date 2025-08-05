# File: main.py
import os
import uuid
import base64
import hashlib
import asyncio
import httpx
import psycopg2
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Form, Request, UploadFile, File, Path as FPath, Query, Body
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from psycopg2 import Error as PsycopgError

# Optional/background systems (safe fallbacks)
try:
    import hybrid_intelligent_memory
    HybridIntelligentMemorySystem = hybrid_intelligent_memory.HybridIntelligentMemorySystem
    RetrievalPolicy = hybrid_intelligent_memory.RetrievalPolicy
except ImportError as e:
    print(f"[BOOT] Failed to import HybridIntelligentMemorySystem: {e}")
    hybrid_intelligent_memory = None  # type: ignore
    HybridIntelligentMemorySystem = None  # type: ignore
    RetrievalPolicy = None  # type: ignore

try:
    import hybrid_background_riai
    from hybrid_background_riai import (
        start_hybrid_background_riai,
        stop_hybrid_background_riai,
        process_hybrid_riai_batch,
    )
    HAVE_RIAI = True
except ImportError as e:
    print(f"[BOOT] Failed to import RIAI services: {e}")
    start_hybrid_background_riai = None  # type: ignore
    stop_hybrid_background_riai = None   # type: ignore
    process_hybrid_riai_batch = None     # type: ignore
    HAVE_RIAI = False

try:
    from tool_generator import ToolGenerator
    from tool_executor import ToolExecutor
except ImportError as e:
    print(f"[BOOT] Tool generator/executor unavailable: {e}")
    ToolGenerator = None
    ToolExecutor = None

try:
    from custom_model_trainer import (
        analyze_user_training_potential,
        prepare_user_training_data,
        start_fine_tuning,
        check_fine_tuning_status,
    )
    from training_scheduler import (
        start_training_scheduler,
        stop_training_scheduler,
        get_training_status,
        trigger_manual_training,
        get_user_custom_model,
    )
except ImportError as e:
    print(f"[BOOT] Training modules unavailable: {e}")
    analyze_user_training_potential = None
    prepare_user_training_data = None
    start_fine_tuning = None
    check_fine_tuning_status = None
    start_training_scheduler = None
    stop_training_scheduler = None

    def get_training_status() -> Dict[str, bool]:
        return {"running": False}

    def trigger_manual_training() -> Dict[str, bool]:
        return {"triggered": False}

    def get_user_custom_model(user_id: str) -> Optional[str]:
        return None

try:
    from personal_model_manager import PersonalModelManager
except ImportError as e:
    print(f"[BOOT] PersonalModelManager unavailable: {e}")
    PersonalModelManager = None

try:
    from desktop_app_connector import DesktopAppConnector
except ImportError as e:
    print(f"[BOOT] DesktopAppConnector unavailable: {e}")
    DesktopAppConnector = None

# Environment
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Password hashing
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception as e:
    print(f"[BOOT] bcrypt warning: {e}")
    pwd_context = CryptContext(schemes=["bcrypt"])

# FastAPI app
app = FastAPI(title="NeuroLM Memory System", version="1.0.2")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static mounts
Path("static").mkdir(exist_ok=True)
Path("attached_assets").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/attached_assets", StaticFiles(directory="attached_assets"), name="attached_assets")

# Globals
hybrid_memory_system = None
tool_generator = None
tool_executor = None
personal_model_manager = None
desktop_connector = None
_riai_task: Optional[asyncio.Task] = None

# ---------------------- DB Helpers ----------------------
def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL)

async def db_to_thread(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

# ---------------------- Schema Setup ----------------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                first_name VARCHAR(255) NOT NULL,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                feedback_score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                title VARCHAR(255) NOT NULL,
                topic VARCHAR(255),
                sub_topic VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(255) NOT NULL,
                message_type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_files (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                file_type VARCHAR(50),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                id SERIAL PRIMARY KEY,
                source_memory_id VARCHAR(255) NOT NULL,
                linked_topic VARCHAR(255) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intelligent_memories (
                id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                conversation_id VARCHAR(255) NOT NULL,
                message_type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR(1536) NOT NULL,
                message_id INT,
                importance FLOAT,
                r_t_score FLOAT,
                h_t_score FLOAT,
                quality_score FLOAT,
                final_quality_score FLOAT,
                evaluation_model TEXT,
                evaluation_timestamp TIMESTAMP,
                human_feedback_score FLOAT,
                human_feedback_type TEXT,
                human_feedback_timestamp TIMESTAMP,
                uf_score_awarded BOOLEAN DEFAULT FALSE,
                ts tsvector,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS response_cache (
                response_hash TEXT NOT NULL,
                evaluator_version TEXT NOT NULL,
                r_t_score FLOAT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (response_hash, evaluator_version)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS graph_outbox (
                id VARCHAR(255) PRIMARY KEY,
                event_type VARCHAR(255) NOT NULL,
                entity_id VARCHAR(255) NOT NULL,
                payload TEXT NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_msgs_conv ON conversation_messages(conversation_id, created_at DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_files_user ON user_files(user_id, uploaded_at DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_im_user ON intelligent_memories(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_im_type_qual ON intelligent_memories(message_type, quality_score, created_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status_created ON graph_outbox(status, created_at);")
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_im_embedding ON intelligent_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);")
        except PsycopgError as e:
            print(f"[INIT] pgvector IVFFlat index warning: {e}")

        conn.commit()
        print("[INIT] Database tables ensured/migrated.")
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

# ---------------------- Sessions ----------------------
def create_session(user_id: str, username: str, extended: bool = False) -> Optional[str]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + (timedelta(days=30) if extended else timedelta(hours=24))
        cur.execute(
            "INSERT INTO sessions (session_id, user_id, username, expires_at) VALUES (%s, %s, %s, %s)",
            (session_id, user_id, username, expires_at)
        )
        conn.commit()
        return session_id
    except PsycopgError as e:
        print(f"[SESSION] create_session DB error: {e}")
        return None
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        try:
            conn.close()
        except psycopg2.Error:
            pass

def get_session(session_id: str) -> Optional[Dict]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id, username FROM sessions WHERE session_id = %s AND expires_at > NOW()", (session_id,))
        row = cur.fetchone()
        if row:
            return {"user_id": row[0], "username": row[1]}
        return None
    except PsycopgError as e:
        print(f"[SESSION] get_session DB error: {e}")
        return None
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        try:
            conn.close()
        except psycopg2.Error:
            pass

def delete_session(session_id: str) -> bool:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
        conn.commit()
        return True
    except PsycopgError as e:
        print(f"[SESSION] delete_session DB error: {e}")
        return False
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        try:
            conn.close()
        except psycopg2.Error:
            pass

def cleanup_expired_sessions() -> bool:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE expires_at <= NOW()")
        conn.commit()
        return True
    except PsycopgError as e:
        print(f"[SESSION] cleanup DB error: {e}")
        return False
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        try:
            conn.close()
        except psycopg2.Error:
            pass

def get_authenticated_user(request: Request) -> Optional[Dict]:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    return get_session(session_id)

# ---------------------- Bootstrapping ----------------------
@app.on_event("startup")
async def on_startup():
    global hybrid_memory_system, tool_generator, tool_executor, personal_model_manager, desktop_connector, _riai_task

    await db_to_thread(init_db)

    if HybridIntelligentMemorySystem:
        try:
            if (hybrid_intelligent_memory is not None and
                hasattr(hybrid_intelligent_memory, "hybrid_intelligent_memory_system") and
                getattr(hybrid_intelligent_memory, "hybrid_intelligent_memory_system") is not None):
                hybrid_memory_system = hybrid_intelligent_memory.hybrid_intelligent_memory_system
                print("✅ Hybrid intelligent memory system (singleton) bound")
            else:
                hybrid_memory_system = HybridIntelligentMemorySystem()
                print("✅ Hybrid intelligent memory system initialized")
        except Exception as e:
            print(f"[BOOT] Memory system init error: {e}")
            hybrid_memory_system = None

    if hybrid_memory_system and hasattr(hybrid_memory_system, "ensure_text_search_support"):
        try:
            ok = await hybrid_memory_system.ensure_text_search_support()
            if ok:
                print("✅ Text search support ensured")
        except Exception as e:
            print(f"[BOOT] ensure_text_search_support error: {e}")

    if ToolGenerator and ToolExecutor:
        try:
            tool_generator = ToolGenerator()
            tool_executor = ToolExecutor()
            print("✅ Tool generation/execution initialized")
        except Exception as e:
            print(f"[BOOT] Tool init error: {e}")

    if PersonalModelManager:
        try:
            personal_model_manager = PersonalModelManager()
            print("✅ Personal Model Manager initialized")
        except Exception as e:
            print(f"[BOOT] PMM init error: {e}")

    if DesktopAppConnector:
        try:
            desktop_connector = DesktopAppConnector()
            print("✅ Desktop Connector initialized")
        except Exception as e:
            print(f"[BOOT] Desktop connector init error: {e}")

    try:
        if HAVE_RIAI and start_hybrid_background_riai:
            _riai_task = asyncio.create_task(start_hybrid_background_riai())
            print("✅ Hybrid background RIAI service started")
    except Exception as e:
        print(f"[BOOT] RIAI start error: {e}")

    # Start outbox worker for Neo4j synchronization
    try:
        from outbox_worker import start_outbox_worker
        await start_outbox_worker()
        print("✅ Outbox worker started")
    except Exception as e:
        print(f"⚠️  Outbox worker startup failed: {e}")

    # Start error cleanup scheduler
    try:
        from error_cleanup_scheduler import start_error_cleanup_scheduler
        start_error_cleanup_scheduler()
        print("✅ Error cleanup scheduler started")
    except Exception as e:
        print(f"⚠️  Error cleanup scheduler startup failed: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    global _riai_task

    try:
        from outbox_worker import stop_outbox_worker
        await stop_outbox_worker()
        print("✅ Outbox worker stopped")
    except Exception as e:
        print(f"⚠️  Outbox worker shutdown error: {e}")

    try:
        from error_cleanup_scheduler import stop_error_cleanup_scheduler
        stop_error_cleanup_scheduler()
        print("✅ Error cleanup scheduler stopped")
    except Exception as e:
        print(f"⚠️  Error cleanup scheduler shutdown error: {e}")

    try:
        if HAVE_RIAI and stop_hybrid_background_riai:
            await stop_hybrid_background_riai()
            print("✅ Hybrid background RIAI service stopped")
    except Exception as e:
        print(f"[SHUTDOWN] RIAI stop error: {e}")

    if _riai_task and not _riai_task.done():
        try:
            await asyncio.wait_for(_riai_task, timeout=2.0)
        except asyncio.TimeoutError:
            _riai_task.cancel()
            try:
                await _riai_task
            except asyncio.CancelledError:
                pass

    try:
        if hybrid_memory_system and hasattr(hybrid_memory_system, "close"):
            hybrid_memory_system.close()
            print("✅ Hybrid memory system resources closed")
    except Exception as e:
        print(f"[SHUTDOWN] Memory close error: {e}")

# ---------------------- Auth and Registration ----------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_user_in_db(first_name: str, username: str, email: str, password_hash: str) -> bool:
    user_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        if cur.fetchone():
            return False
        cur.execute(
            "INSERT INTO users (id, first_name, username, email, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (user_id, first_name, username, email, password_hash)
        )
        conn.commit()
        return True
    except PsycopgError as e:
        print(f"[AUTH] create_user DB error: {e}")
        return False
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

def verify_user_login(username: str, password: str) -> Optional[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if not row:
            return None
        user_id, stored_hash = row
        if stored_hash.startswith("$2b$"):
            if pwd_context.verify(password, stored_hash):
                return user_id
        else:
            if hashlib.sha256(password.encode()).hexdigest() == stored_hash:
                new_hash = pwd_context.hash(password)
                cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
                conn.commit()
                return user_id
        return None
    except PsycopgError as e:
        print(f"[AUTH] verify_login DB error: {e}")
        return None
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

def get_user_first_name(user_id: str) -> Optional[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None
    except PsycopgError as e:
        print(f"[AUTH] get_first_name DB error: {e}")
        return None
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

# ---------------------- Minimal HTML Routes (UI) ----------------------
@app.get("/")
def serve_chat(request: Request):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return FileResponse("chat.html") if Path("chat.html").exists() else HTMLResponse("<h1>Chat UI not deployed</h1>")

@app.get("/register")
def register_page():
    return FileResponse("static/register.html") if Path("static/register.html").exists() else HTMLResponse("<h1>Register UI not deployed</h1>")

@app.post("/register")
async def register_user(
    first_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    openrouter_key: Optional[str] = Form(""),
    openai_key: Optional[str] = Form("")
):
    if password != confirm_password:
        return HTMLResponse("<script>alert('Passwords do not match'); window.location.href = '/register';</script>")
    password_hash = hash_password(password)
    success = await db_to_thread(create_user_in_db, first_name, username, email, password_hash)
    if not success:
        return HTMLResponse("<script>alert('Username or email already exists.'); window.location.href = '/register';</script>")

    if (openrouter_key and openrouter_key.strip()) or (openai_key and openai_key.strip()):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if row:
                user_id = row[0]
                key = base64.urlsafe_b64encode(hashlib.sha256(user_id.encode()).digest())
                from cryptography.fernet import Fernet
                fernet = Fernet(key)
                payload: Dict[str, str] = {}
                if openrouter_key and openrouter_key.strip():
                    payload["openrouter_key"] = openrouter_key.strip()
                if openai_key and openai_key.strip():
                    payload["openai_key"] = openai_key.strip()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_api_keys (
                        user_id VARCHAR(255) NOT NULL,
                        provider VARCHAR(255) NOT NULL,
                        encrypted_key TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP,
                        PRIMARY KEY (user_id, provider),
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    );
                """)
                for provider, api_key in payload.items():
                    encrypted = fernet.encrypt(api_key.encode()).decode()
                    cur.execute("""
                        INSERT INTO user_api_keys (user_id, provider, encrypted_key, created_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, provider)
                        DO UPDATE SET encrypted_key = EXCLUDED.encrypted_key, updated_at = CURRENT_TIMESTAMP
                    """, (user_id, provider, encrypted))
                conn.commit()
            cur.close()
            conn.close()
        except PsycopgError as e:
            print(f"[REGISTER] API key store DB error: {e}")
        except Exception as e:
            print(f"[REGISTER] API key store error: {e}")
    return HTMLResponse("<script>alert('Account created. Please log in.'); window.location.href = '/login';</script>")

@app.get("/login")
def login_page():
    return FileResponse("static/login.html") if Path("static/login.html").exists() else HTMLResponse("<h1>Login UI not deployed</h1>")

@app.post("/login")
async def login_user(username: str = Form(...), password: str = Form(...), remember_me: bool = Form(False)):
    user_id = await db_to_thread(verify_user_login, username, password)
    if not user_id:
        return HTMLResponse("<script>alert('Invalid credentials'); window.location.href = '/login';</script>")
    session_id = await db_to_thread(create_session, user_id, username, remember_me)
    if not session_id:
        return HTMLResponse("<script>alert('Failed to create session'); window.location.href = '/login';</script>")
    resp = RedirectResponse(url="/", status_code=302)
    cookie_params = {
        "httponly": True,
        "secure": False if os.getenv("DEV_INSECURE_COOKIE","0")=="1" else True,
        "samesite": "lax"
    }
    max_age = 30 * 24 * 3600 if remember_me else None
    resp.set_cookie("session_id", session_id, max_age=max_age, **cookie_params)
    return resp

@app.get("/secrets")
def secrets_page(request: Request):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return FileResponse("secrets_manager.html") if Path("secrets_manager.html").exists() else HTMLResponse("<h1>Secrets Manager not deployed</h1>")

@app.get("/personal-models")
def personal_models_page(request: Request):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return FileResponse("personal_models_dashboard.html") if Path("personal_models_dashboard.html").exists() else HTMLResponse("<h1>Personal Models Dashboard not deployed</h1>")

@app.get("/training")
def training_page(request: Request):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return FileResponse("training_dashboard.html") if Path("training_dashboard.html").exists() else HTMLResponse("<h1>Training Dashboard not deployed</h1>")

# ---------------------- Secrets Management API ----------------------
@app.get("/api/secrets/list")
async def list_secrets(request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from secrets_vault import vault
        secrets = vault.list_user_secrets(user["user_id"])
        return {"success": True, "secrets": secrets}
    except Exception as e:
        print(f"[SECRETS] list error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list secrets")

@app.post("/api/secrets/store")
async def store_secret(request: Request, data: dict = Body(...)):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from secrets_vault import vault
        secret_type = data.get("secret_type", "general")
        secret_name = data.get("secret_name")
        secret_value = data.get("secret_value")
        
        if not secret_name or not secret_value:
            raise HTTPException(status_code=400, detail="secret_name and secret_value required")
        
        success = vault.store_secret(user["user_id"], secret_type, secret_name, secret_value)
        if success:
            return {"success": True, "message": "Secret stored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store secret")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SECRETS] store error: {e}")
        raise HTTPException(status_code=500, detail="Failed to store secret")

@app.get("/api/secrets/{secret_type}/{secret_name}")
async def get_secret(request: Request, secret_type: str, secret_name: str):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from secrets_vault import vault
        secret_value = vault.get_secret(user["user_id"], secret_type, secret_name)
        if secret_value is None:
            raise HTTPException(status_code=404, detail="Secret not found")
        return {"success": True, "secret_value": secret_value}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SECRETS] get error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve secret")

@app.delete("/api/secrets/{secret_type}/{secret_name}")
async def delete_secret(request: Request, secret_type: str, secret_name: str):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from secrets_vault import vault
        success = vault.delete_secret(user["user_id"], secret_type, secret_name)
        if success:
            return {"success": True, "message": "Secret deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Secret not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SECRETS] delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete secret")

# ---------------------- Chat and Memory ----------------------
DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-4o-mini")

class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = DEFAULT_MODEL
    conversation_id: Optional[str] = None
    web_search: Optional[bool] = False

class ChatResponse(BaseModel):
    response: str
    memory_stored: bool
    context_used: int
    conversation_id: str
    assistant_message_id: Optional[str] = None
    deletion_info: Optional[Dict] = None

def create_outbox_event(event_type: str, entity_id: str, payload: Dict[str, Any], conn) -> bool:
    """
    Create an outbox event within an existing database connection/transaction.
    This ensures atomicity with the main operation.
    """
    try:
        cursor = conn.cursor()
        event_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO graph_outbox (id, event_type, entity_id, payload, status, attempts)
            VALUES (%s, %s, %s, %s, 'pending', 0)
            """,
            (event_id, event_type, entity_id, json.dumps(payload))
        )
        return True
    except psycopg2.Error as e:
        print(f"⚠️ Failed to create outbox event: {e}")
        return False
    finally:
        try:
            cursor.close()
        except psycopg2.Error:
            pass

def create_conversation(user_id: str, title: Optional[str] = None, topic: Optional[str] = None, sub_topic: Optional[str] = None) -> Optional[str]:
    conversation_id = str(uuid.uuid4())
    title = title or "New Conversation"
    topic = (topic or "general").lower().strip()
    sub_topic = sub_topic.lower().strip() if sub_topic else None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO conversations (id, user_id, title, topic, sub_topic, created_at, updated_at, message_count)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
        """, (conversation_id, user_id, title, topic, sub_topic))
        
        # Create outbox event for conversation upsert
        conversation_payload = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "title": title,
            "topic": topic,
            "sub_topic": sub_topic
        }
        outbox_success = create_outbox_event(
            event_type="conversation_upsert",
            entity_id=conversation_id,
            payload=conversation_payload,
            conn=conn
        )
        
        if not outbox_success:
            print(f"⚠️ Outbox event creation failed for conversation {conversation_id}, rolling back")
            conn.rollback()
            return None
            
        conn.commit()
        return conversation_id
    except PsycopgError as e:
        print(f"[CONV] create DB error: {e}")
        return None
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

def save_conversation_message(conversation_id: str, message_type: str, content: str) -> Optional[int]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO conversation_messages (conversation_id, message_type, content, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
        """, (conversation_id, message_type, content))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Message insert failed")
        msg_id = int(row[0])
        cur.execute("UPDATE conversations SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (conversation_id,))
        conn.commit()
        return msg_id
    except PsycopgError as e:
        print(f"[MSG] save DB error: {e}")
        return None
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

async def maybe_run_background_tools(messages: List[Dict[str, str]], user_id: str) -> Optional[Dict[str, Any]]:
    await asyncio.sleep(0)
    return None

# ---------------------- Slash Commands ----------------------

async def handle_slash_command(command: str, user_id: str, conversation_id: str) -> ChatResponse:
    parts = command.strip().split()
    cmd = parts[0].lower()
    try:
        if cmd == '/files':
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT filename, file_type, uploaded_at FROM user_files WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
            files = cur.fetchall()
            cur.close()
            conn.close()
            if not files:
                response = "No files uploaded yet. Use the + button to upload files."
            else:
                response = "**Your uploaded files:**\n\n"
                for filename, file_type, uploaded_at in files:
                    date = uploaded_at.strftime("%Y-%m-%d %H:%M") if uploaded_at else ""
                    response += f"• `{filename}` ({file_type}) - {date}\n"
                response += f"\nUse `/view [filename]` to display file content."
        elif cmd == '/view':
            if len(parts) < 2:
                response = "Usage: `/view [filename]`"
            else:
                filename = ' '.join(parts[1:])
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT content FROM user_files WHERE user_id = %s AND filename = %s", (user_id, filename))
                row = cur.fetchone()
                cur.close()
                conn.close()
                if row:
                    response = f"**File: {filename}**\n\n```\n{row[0]}\n```"
                else:
                    response = f"File '{filename}' not found. Use `/files` to see available files."
        elif cmd == '/delete':
            if len(parts) < 2:
                response = "Usage: `/delete [filename]`"
            else:
                filename = ' '.join(parts[1:])
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM user_files WHERE user_id = %s AND filename = %s", (user_id, filename))
                deleted = cur.rowcount
                conn.commit()
                cur.close()
                conn.close()
                response = f"File '{filename}' deleted successfully." if deleted > 0 else f"File '{filename}' not found."
        elif cmd == '/search':
            if len(parts) < 2:
                response = "Usage: `/search [term]`"
            else:
                term = ' '.join(parts[1:])
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT filename, file_type, uploaded_at FROM user_files WHERE user_id = %s AND filename ILIKE %s ORDER BY uploaded_at DESC", (user_id, f"%{term}%"))
                files = cur.fetchall()
                cur.close()
                conn.close()
                if not files:
                    response = f"No files found matching '{term}'."
                else:
                    response = f"**Files matching '{term}':**\n\n"
                    for filename, file_type, uploaded_at in files:
                        date = uploaded_at.strftime("%Y-%m-%d %H:%M") if uploaded_at else ""
                        response += f"• `{filename}` ({file_type}) - {date}\n"
        elif cmd == '/download':
            if len(parts) < 2:
                response = "Usage: `/download [filename]`"
            else:
                filename = ' '.join(parts[1:])
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT filename FROM user_files WHERE user_id = %s AND filename = %s", (user_id, filename))
                row = cur.fetchone()
                cur.close()
                conn.close()
                if row:
                    download_url = f"/api/download/{filename}"
                    response = f"**Download ready:** `{filename}`\n\n[Download {filename}]({download_url})"
                else:
                    response = f"File '{filename}' not found. Use `/files` to see available files."
        elif cmd == '/topics':
            conn = get_db_connection()
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT COALESCE(topic,'general') AS topic, COALESCE(sub_topic,'') AS sub_topic
                    FROM conversations
                    WHERE user_id = %s
                    GROUP BY topic, sub_topic
                """, (user_id,))
                topic_map: Dict[str, List[str]] = {}
                for t, s in cur.fetchall():
                    tkey = (t or "general").lower()
                    if tkey not in topic_map:
                        topic_map[tkey] = []
                    s_clean = (s or "").strip()
                    if s_clean and s_clean.lower() not in [x.lower() for x in topic_map[tkey]]:
                        topic_map[tkey].append(s_clean)
                if not topic_map:
                    response = "No topics created yet. Start a conversation with a topic to organize your chats."
                else:
                    response = "**Your Topics:**\n\n"
                    for topic, sub_topics in topic_map.items():
                        response += f"• **{topic}**\n"
                        if sub_topics:
                            for s in sub_topics:
                                response += f"  - {s}\n"
                        else:
                            response += "  - (no sub-topics)\n"
            except PsycopgError as e:
                print(f"[TOPICS] list DB error: {e}")
                response = "Error retrieving topics."
            finally:
                try:
                    cur.close()
                except psycopg2.Error:
                    pass
                conn.close()
        else:
            response = ("**Available commands:**\n\n"
                        "• `/files` - List your uploaded files\n"
                        "• `/view [filename]` - Display file content\n"
                        "• `/delete [filename]` - Delete a file\n"
                        "• `/search [term]` - Search files by name\n"
                        "• `/download [filename]` - Get download link\n"
                        "• `/topics` - Show your conversation topics")

        await db_to_thread(save_conversation_message, conversation_id, 'user', command)
        await db_to_thread(save_conversation_message, conversation_id, 'assistant', response)
        return ChatResponse(
            response=response,
            memory_stored=False,
            context_used=0,
            conversation_id=conversation_id
        )
    except Exception as e:
        return ChatResponse(
            response=f"Error processing command: {str(e)}",
            memory_stored=False,
            context_used=0,
            conversation_id=conversation_id
        )

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_memory(chat_request: ChatMessage, request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["user_id"]

    if chat_request.message.startswith("/"):
        conversation_id = chat_request.conversation_id or await db_to_thread(create_conversation, user_id)
        if not conversation_id:
            return ChatResponse(response="Error creating conversation.", memory_stored=False, context_used=0, conversation_id="")
        return await handle_slash_command(chat_request.message, user_id, conversation_id)

    conversation_id = chat_request.conversation_id or await db_to_thread(create_conversation, user_id)
    if not conversation_id:
        raise HTTPException(status_code=500, detail="Failed to create conversation")

    context = ""
    if hybrid_memory_system:
        try:
            short_policy = RetrievalPolicy(k_recent=4, k_conv=4, k_topic=2, allow_global_fallback=False) if RetrievalPolicy else None
            context = await hybrid_memory_system.retrieve_memory(
                query=chat_request.message,
                user_id=user_id,
                conversation_id=conversation_id,
                policy=short_policy
            )
        except Exception as e:
            print(f"[MEMORY] retrieve error: {e}")
            context = ""

    user_first_name = await db_to_thread(get_user_first_name, user_id)
    requested_model = chat_request.model or DEFAULT_MODEL
    if not await validate_model_access(user_id, requested_model):
        raise HTTPException(status_code=403, detail="Access denied for requested model")

    from model_services import ModelService
    model_service = ModelService()
    system_content = f"""You are a helpful AI assistant for {user_first_name or "the user"}.
Prior memory:
{context or "No previous conversation history available."}
Use the memory to maintain continuity and consistency."""
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": chat_request.message}
    ]

    try:
        response_text = await model_service.chat_completion(
            messages=messages,
            model=requested_model,
            web_search=bool(chat_request.web_search)
        )
    except httpx.HTTPError as e:
        print(f"[LLM] HTTP error: {e}")
        response_text = "I'm having trouble responding right now."
    except asyncio.TimeoutError as e:
        print(f"[LLM] timeout: {e}")
        response_text = "I'm having trouble responding right now."
    except Exception as e:
        print(f"[LLM] error: {e}")
        response_text = "I'm having trouble responding right now."

    user_msg_id = await db_to_thread(save_conversation_message, conversation_id, "user", chat_request.message)
    assistant_msg_id = await db_to_thread(save_conversation_message, conversation_id, "assistant", response_text)
    assistant_memory_id = None
    if hybrid_memory_system:
        try:
            if user_msg_id:
                await hybrid_memory_system.store_memory(
                    content=chat_request.message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message_type="user",
                    message_id=user_msg_id
                )
            if assistant_msg_id:
                assistant_memory_id = await hybrid_memory_system.store_memory(
                    content=response_text,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message_type="assistant",
                    message_id=assistant_msg_id
                )
        except Exception as e:
            print(f"[MEMORY] store error: {e}")

    return ChatResponse(
        response=response_text,
        memory_stored=True,
        context_used=1 if context else 0,
        conversation_id=conversation_id,
        assistant_message_id=assistant_memory_id
    )

@app.post("/api/chat-stream")
async def chat_with_memory_stream(chat_request: ChatMessage, request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["user_id"]

    conversation_id = chat_request.conversation_id or await db_to_thread(create_conversation, user_id)
    if not conversation_id:
        raise HTTPException(status_code=500, detail="Failed to create conversation")

    context = ""
    if hybrid_memory_system:
        try:
            short_policy = RetrievalPolicy(k_recent=4, k_conv=4, k_topic=2, allow_global_fallback=False) if RetrievalPolicy else None
            context = await hybrid_memory_system.retrieve_memory(
                query=chat_request.message,
                user_id=user_id,
                conversation_id=conversation_id,
                policy=short_policy
            )
        except Exception as e:
            print(f"[MEMORY] retrieve error: {e}")

    user_msg_id = await db_to_thread(save_conversation_message, conversation_id, "user", chat_request.message)

    user_first_name = await db_to_thread(get_user_first_name, user_id)
    requested_model = chat_request.model or DEFAULT_MODEL
    if not await validate_model_access(user_id, requested_model):
        raise HTTPException(status_code=403, detail="Access denied for requested model")

    from model_services import ModelService
    model_service = ModelService()
    system_content = f"""You are a helpful AI assistant for {user_first_name or "the user"}.
Prior memory:
{context or "No previous conversation history available."}
Use the memory to maintain continuity and consistency."""
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": chat_request.message}
    ]

    async def event_stream():
        buffer = ""
        full_text_parts: List[str] = []

        def sse_frame(data: str) -> str:
            return f"data: {data}\n\n"

        try:
            async for chunk in model_service.chat_completion_stream(
                messages=messages,
                model=requested_model,
                web_search=bool(chat_request.web_search),
            ):
                if not isinstance(chunk, str):
                    continue
                buffer += chunk

                while True:
                    line_end = buffer.find("\n")
                    if line_end == -1:
                        break
                    line = buffer[:line_end].strip()
                    buffer = buffer[line_end + 1:]

                    if not line or line.startswith(":"):
                        continue

                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            full_text = "".join(full_text_parts)
                            assistant_msg_id = await db_to_thread(save_conversation_message, conversation_id, "assistant", full_text)
                            if hybrid_memory_system and assistant_msg_id:
                                try:
                                    _ = await hybrid_memory_system.store_memory(
                                        content=full_text,
                                        user_id=user_id,
                                        conversation_id=conversation_id,
                                        message_type="assistant",
                                        message_id=assistant_msg_id
                                    )
                                except Exception as e:
                                    print(f"[MEMORY] store (assistant) error: {e}")

                            yield sse_frame("[[STREAM_COMPLETE]]")
                            return

                        try:
                            import json
                            dobj = json.loads(data)
                            delta = ""
                            choices = dobj.get("choices") or []
                            if choices:
                                delta = (choices[0].get("delta") or {}).get("content") or ""
                            if delta:
                                full_text_parts.append(delta)
                                yield sse_frame(delta)
                        except Exception:
                            pass

            full_text = "".join(full_text_parts)
            if full_text:
                assistant_msg_id = await db_to_thread(save_conversation_message, conversation_id, "assistant", full_text)
                if hybrid_memory_system and assistant_msg_id:
                    try:
                        _ = await hybrid_memory_system.store_memory(
                            content=full_text,
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message_type="assistant",
                            message_id=assistant_msg_id
                        )
                    except Exception as e:
                        print(f"[MEMORY] store (assistant) error: {e}")
            yield sse_frame("[[STREAM_COMPLETE]]")
        except Exception as e:
            print(f"[STREAM] error: {e}")
            yield sse_frame("[[STREAM_ERROR]]")

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# ---------------------- Conversations & Topics API (added) ----------------------
def ensure_user(request: Request) -> Dict:
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@app.get("/api/user/name")
async def api_user_name(request: Request):
    user = ensure_user(request)
    user_id = user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT first_name, feedback_score FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return {"first_name": row[0] if row else None, "feedback_score": int(row[1]) if row else 0}
    except PsycopgError as e:
        print(f"[USER] name DB error: {e}")
        return {"first_name": None, "feedback_score": 0}
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

@app.get("/api/topics")
async def api_get_topics(request: Request):
    user = ensure_user(request)
    user_id = user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COALESCE(topic,'general') AS topic, COALESCE(sub_topic,'') AS sub_topic
            FROM conversations
            WHERE user_id = %s
            GROUP BY topic, sub_topic
        """, (user_id,))
        topic_map: Dict[str, List[str]] = {}
        for t, s in cur.fetchall():
            tkey = (t or "general").lower()
            if tkey not in topic_map:
                topic_map[tkey] = []
            s_clean = (s or "").strip()
            if s_clean and s_clean.lower() not in [x.lower() for x in topic_map[tkey]]:
                topic_map[tkey].append(s_clean)
        return topic_map
    except PsycopgError as e:
        print(f"[TOPICS] list DB error: {e}")
        return {}
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

class TopicCreate(BaseModel):
    topic: str

@app.post("/api/topics")
async def api_create_topic(payload: TopicCreate, request: Request):
    user = ensure_user(request)
    user_id = user["user_id"]
    topic = (payload.topic or "general").strip().lower()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic required")
    # Insert a placeholder conversation to ensure topic appears; title indicates placeholder
    conv_id = await db_to_thread(create_conversation, user_id, f"{topic} • topic", topic, None)
    if not conv_id:
        raise HTTPException(status_code=500, detail="Failed to create topic")
    return {"status": "ok", "topic": topic}

class SubtopicCreate(BaseModel):
    sub_topic: str

@app.post("/api/topics/{topic}/subtopics")
async def api_create_subtopic(topic: str = FPath(...), payload: SubtopicCreate = Body(...), request: Request = None):
    user = ensure_user(request)
    user_id = user["user_id"]
    topic = (topic or "").strip().lower()
    sub = (payload.sub_topic or "").strip()
    if not topic or not sub:
        raise HTTPException(status_code=400, detail="Topic and sub_topic required")
    conv_id = await db_to_thread(create_conversation, user_id, f"{topic}/{sub} • subtopic", topic, sub)
    if not conv_id:
        raise HTTPException(status_code=500, detail="Failed to create subtopic")
    return {"status": "ok", "topic": topic, "sub_topic": sub}

@app.delete("/api/topics/{topic}")
async def api_delete_topic(topic: str = FPath(...), request: Request = None):
    user = ensure_user(request)
    user_id = user["user_id"]
    topic = (topic or "").strip().lower()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic required")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM conversations WHERE user_id = %s AND LOWER(COALESCE(topic,'')) = %s", (user_id, topic))
        deleted = cur.rowcount
        conn.commit()
        return {"status": "ok", "deleted": deleted}
    except PsycopgError as e:
        print(f"[TOPICS] delete DB error: {e}")
        raise HTTPException(status_code=500, detail="Delete failed")
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

@app.delete("/api/topics/{topic}/subtopics/{subtopic}")
async def api_delete_subtopic(topic: str = FPath(...), subtopic: str = FPath(...), request: Request = None):
    user = ensure_user(request)
    user_id = user["user_id"]
    topic = (topic or "").strip().lower()
    subtopic = (subtopic or "").strip()
    if not topic or not subtopic:
        raise HTTPException(status_code=400, detail="Topic and subtopic required")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM conversations 
            WHERE user_id = %s AND LOWER(COALESCE(topic,'')) = %s AND COALESCE(sub_topic,'') = %s
        """, (user_id, topic, subtopic))
        deleted = cur.rowcount
        conn.commit()
        return {"status": "ok", "deleted": deleted}
    except PsycopgError as e:
        print(f"[TOPICS] delete sub DB error: {e}")
        raise HTTPException(status_code=500, detail="Delete failed")
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

@app.get("/api/conversations")
async def api_list_conversations(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    topic: Optional[str] = Query(None),
    sub_topic: Optional[str] = Query(None),
):
    user = ensure_user(request)
    user_id = user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        params = [user_id]
        where = ["user_id = %s"]
        if topic:
            where.append("LOWER(COALESCE(topic,'')) = %s")
            params.append(topic.strip().lower())
        if sub_topic is not None:
            where.append("COALESCE(sub_topic,'') = %s")
            params.append(sub_topic.strip())
        where_sql = " AND ".join(where)
        cur.execute(f"""
            SELECT id, title, topic, sub_topic, updated_at, message_count
            FROM conversations
            WHERE {where_sql}
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """, (*params, limit, offset))
        rows = cur.fetchall()
        items = []
        for r in rows:
            items.append({
                "id": r[0],
                "title": r[1],
                "topic": r[2],
                "sub_topic": r[3],
                "updated_at": r[4].isoformat() if r[4] else None,
                "message_count": r[5],
                "last_message": None  # can be enhanced by joining messages
            })
        has_more = len(items) == limit
        next_offset = offset + len(items)
        return {"conversations": items, "has_more": has_more, "next_offset": next_offset}
    except PsycopgError as e:
        print(f"[CONV] list DB error: {e}")
        return {"conversations": [], "has_more": False, "next_offset": offset}
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    sub_topic: Optional[str] = None

@app.post("/api/conversations/new")
async def api_new_conversation(payload: ConversationCreate, request: Request):
    user = ensure_user(request)
    user_id = user["user_id"]
    conv_id = await db_to_thread(
        create_conversation,
        user_id,
        (payload.title or "New Conversation").strip(),
        (payload.topic or "general").strip().lower() if payload.topic else None,
        (payload.sub_topic or "").strip() if payload.sub_topic else None
    )
    if not conv_id:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    return {"id": conv_id}

@app.get("/api/conversations/{conv_id}/messages")
async def api_get_messages(
    request: Request,
    conv_id: str = FPath(...),
    limit: int = Query(30, ge=1, le=200),
    before_id: Optional[int] = Query(None),
):
    user = ensure_user(request)
    user_id = user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Ownership check
        cur.execute("SELECT 1 FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")

        if before_id:
            cur.execute("""
                SELECT id, message_type, content, created_at
                FROM conversation_messages
                WHERE conversation_id = %s AND id < %s
                ORDER BY id DESC
                LIMIT %s
            """, (conv_id, before_id, limit))
        else:
            cur.execute("""
                SELECT id, message_type, content, created_at
                FROM conversation_messages
                WHERE conversation_id = %s
                ORDER BY id DESC
                LIMIT %s
            """, (conv_id, limit))
        rows = cur.fetchall()
        rows.reverse()  # return oldest->newest
        messages = [
            {
                "id": r[0],
                "message_type": r[1],
                "content": r[2],
                "created_at": r[3].isoformat() if r[3] else None
            } for r in rows
        ]
        oldest_id = messages[0]["id"] if messages else None
        has_more = False
        if messages:
            cur.execute("SELECT 1 FROM conversation_messages WHERE conversation_id = %s AND id < %s LIMIT 1", (conv_id, oldest_id))
            has_more = bool(cur.fetchone())
        return {"messages": messages, "has_more": has_more, "oldest_id": oldest_id}
    except PsycopgError as e:
        print(f"[MSG] list DB error: {e}")
        return {"messages": [], "has_more": False, "oldest_id": None}
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

class ConversationTopicUpdate(BaseModel):
    topic: Optional[str] = None
    sub_topic: Optional[str] = None

@app.put("/api/conversations/{conv_id}/topic")
async def api_update_conversation_topic(
    request: Request,
    conv_id: str = FPath(...),
    payload: ConversationTopicUpdate = Body(...)
):
    user = ensure_user(request)
    user_id = user["user_id"]
    topic = (payload.topic or "general").strip().lower() if payload.topic is not None else None
    sub = (payload.sub_topic or "").strip() if payload.sub_topic is not None else None

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT title FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        title = row[0]
        
        cur.execute("""
            UPDATE conversations
            SET topic = %s, sub_topic = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (topic, sub, conv_id))
        
        # Create outbox event for conversation upsert
        conversation_payload = {
            "user_id": user_id,
            "conversation_id": conv_id,
            "title": title,
            "topic": topic,
            "sub_topic": sub
        }
        outbox_success = create_outbox_event(
            event_type="conversation_upsert",
            entity_id=conv_id,
            payload=conversation_payload,
            conn=conn
        )
        
        if not outbox_success:
            print(f"⚠️ Outbox event creation failed for conversation update {conv_id}, rolling back")
            conn.rollback()
            raise HTTPException(status_code=500, detail="Update failed - sync error")
        
        conn.commit()
        return {"status": "ok"}
    except HTTPException:
        raise
    except PsycopgError as e:
        print(f"[CONV] update topic DB error: {e}")
        raise HTTPException(status_code=500, detail="Update failed")
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

@app.delete("/api/conversations/{conv_id}")
async def api_delete_conversation(request: Request, conv_id: str = FPath(...)):
    user = ensure_user(request)
    user_id = user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id))
        deleted = cur.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "ok", "deleted": deleted}
    except PsycopgError as e:
        print(f"[CONV] delete DB error: {e}")
        raise HTTPException(status_code=500, detail="Delete failed")
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

# ---------------------- Models and Access Control ----------------------
async def get_user_api_capabilities(user_id: str) -> Dict:
    await asyncio.sleep(0)
    try:
        from model_services import has_openrouter_key
        has_key = has_openrouter_key(user_id)
        tier = "openrouter" if has_key else "free"
        return {"tier": tier, "has_openrouter": has_key}
    except Exception as e:
        print(f"[CAP] error: {e}")
        return {"tier": "free", "has_openrouter": False}

@app.get("/api/models")
async def get_available_models(request: Request):
    try:
        from model_services import ModelService, filter_models_by_tier
        model_service = ModelService()
        all_models = await model_service.get_models()
        user = get_authenticated_user(request)
        tier = "free"
        if user:
            caps = await get_user_api_capabilities(user["user_id"])
            tier = caps.get("tier", "free") if isinstance(caps, dict) else "free"
        filtered = filter_models_by_tier(all_models, tier)
        filtered.sort(key=lambda x: (x.get("name", "") or "").lower())
        return filtered
    except Exception as e:
        print(f"[MODELS] error: {e}")
        return [
            {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Llama 3.2 3B (Free)"},
            {"id": "google/gemini-2.0-flash-001:free", "name": "Gemini 2.0 Flash (Free)"}
        ]

async def validate_model_access(user_id: str, model_id: str) -> bool:
    try:
        from model_services import get_model_tier
        caps = await get_user_api_capabilities(user_id)
        tier = caps.get("tier", "free") if isinstance(caps, dict) else "free"
        mt = get_model_tier(model_id)
        
        # Simplified logic: OpenRouter key gives access to all models, no key = free only
        if tier == "openrouter":
            return True  # Full access with API key
        else:
            return mt == "free"  # Free models only without key
    except Exception as e:
        print(f"[ACCESS] validate error: {e}")
        return False

# ---------------------- RIAI Test ----------------------
@app.post("/api/test-riai")
async def test_riai_scoring(request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not (HAVE_RIAI and process_hybrid_riai_batch):
        raise HTTPException(status_code=500, detail="RIAI system not available")
    result = await process_hybrid_riai_batch()
    if not isinstance(result, dict):
        total_found = cached = evaluated = 0
    else:
        total_found = int(result.get('total_found') or 0)
        cached = int(result.get('cached') or 0)
        evaluated = int(result.get('evaluated') or 0)
    return {
        "status": "success",
        "riai_results": result,
        "message": f"Background R(t): {total_found} found, {cached} cached, {evaluated} evaluated"
    }

# ---------------------- Feedback Endpoints ----------------------
class FeedbackRequest(BaseModel):
    message_id: str
    feedback_type: str  # 'great_response', 'that_worked', 'not_helpful', 'like', 'dislike'

@app.post("/api/feedback")
async def submit_feedback(feedback_request: FeedbackRequest, request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["user_id"]
    valid = ['great_response', 'that_worked', 'not_helpful', 'like', 'dislike']
    if feedback_request.feedback_type not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid feedback type")
    if not hybrid_memory_system:
        raise HTTPException(status_code=500, detail="Memory system not available")

    feedback_scores = {
        'great_response': 9.0,
        'that_worked': 10.0,
        'like': 8.0,
        'dislike': 2.0,
        'not_helpful': 2.0
    }
    score = feedback_scores[feedback_request.feedback_type]
    ok = await hybrid_memory_system.update_human_feedback_by_node_id(
        node_id=feedback_request.message_id,
        feedback_score=score,
        feedback_type=feedback_request.feedback_type,
        user_id=user_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found or update failed")

    await hybrid_memory_system.update_final_quality_score(feedback_request.message_id, user_id)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT uf_score_awarded FROM intelligent_memories WHERE id = %s AND user_id = %s", (feedback_request.message_id, user_id))
        row = cur.fetchone()
        if row and (row[0] is False):
            cur.execute("UPDATE users SET feedback_score = feedback_score + 1 WHERE id = %s", (user_id,))
            cur.execute("UPDATE intelligent_memories SET uf_score_awarded = TRUE WHERE id = %s AND user_id = %s", (feedback_request.message_id, user_id))
            conn.commit()
        cur.close()
        conn.close()
    except PsycopgError as e:
        print(f"[FEEDBACK] UF score DB error: {e}")
    except Exception as e:
        print(f"[FEEDBACK] UF score update error: {e}")

    return {"status": "success", "message": f"Feedback recorded: {feedback_request.feedback_type}", "h_t_score": score}

class ImplicitFeedbackRequest(BaseModel):
    message_id: str
    action_type: str  # 'copy', 'continue', 'followup'
    feedback_score: Optional[float] = None

@app.post("/api/feedback-implicit")
async def submit_implicit_feedback(payload: ImplicitFeedbackRequest, request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["user_id"]
    if payload.action_type not in ['copy', 'continue', 'followup']:
        raise HTTPException(status_code=400, detail="Invalid action type")
    if not hybrid_memory_system:
        return {"status": "skipped", "message": "Memory system not available"}

    implied_scores = {
        'copy': 7.0,
        'continue': 6.5,
        'followup': 6.0
    }
    h = implied_scores[payload.action_type]

    ok = await hybrid_memory_system.update_human_feedback_by_node_id(
        node_id=payload.message_id,
        feedback_score=h,
        feedback_type=f"implicit_{payload.action_type}",
        user_id=user_id
    )
    if ok:
        await hybrid_memory_system.update_final_quality_score(payload.message_id, user_id)
        return {"status": "success", "message": f"Implicit feedback recorded: {payload.action_type}", "h_t_score": h}
    else:
        return {"status": "skipped", "message": "Message not found or already updated"}

# ---------------------- Files ----------------------
@app.post("/api/upload-file")
async def upload_file(request: Request, file: UploadFile = File(...)):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["user_id"]
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO user_files (user_id, filename, content, file_type) VALUES (%s, %s, %s, %s)", (user_id, file.filename, text, file.content_type))
        conn.commit()
        return {"message": f"File {file.filename} uploaded successfully"}
    except PsycopgError as e:
        print(f"[FILES] upload DB error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

@app.get("/api/download/{filename}")
def download_file(filename: str, request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT content, file_type FROM user_files WHERE user_id = %s AND filename = %s", (user_id, filename))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="File not found")
        content, file_type = row
        headers = {"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": file_type or "application/octet-stream"}
        return Response(content=content, headers=headers)
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

@app.get("/api/user-files")
def get_user_files(request: Request, search: Optional[str] = None):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if search:
            cur.execute("""
                SELECT id, filename, file_type, uploaded_at, LEFT(content, 100) as content_preview
                FROM user_files
                WHERE user_id = %s AND filename ILIKE %s
                ORDER BY uploaded_at DESC
            """, (user_id, f"%{search}%"))
        else:
            cur.execute("""
                SELECT id, filename, file_type, uploaded_at, LEFT(content, 100) as content_preview
                FROM user_files
                WHERE user_id = %s
                ORDER BY uploaded_at DESC
            """, (user_id,))
        files = []
        for row in cur.fetchall():
            preview = row[4] or ""
            files.append({
                "id": row[0],
                "filename": row[1],
                "file_type": row[2],
                "uploaded_at": row[3].isoformat() if row[3] else None,
                "content_preview": (preview + "...") if len(preview) == 100 else preview
            })
        return files
    except PsycopgError as e:
        print(f"[FILES] list DB error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get files")
    finally:
        try:
            cur.close()
        except psycopg2.Error:
            pass
        conn.close()

# ---------------------- Health ----------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "NeuroLM Memory System"}

@app.get("/health/db")
async def health_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT now()")
        db_time = cur.fetchone()[0]
        return {
            "status": "healthy",
            "database_time": db_time.isoformat(),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "database": "postgresql"}
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

# ---------------------- Main ----------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
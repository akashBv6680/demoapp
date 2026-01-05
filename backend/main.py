from fastapi import FastAPI, HTTPException, Depends
from fastapi.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import sqlite3
import json
import os
from typing import Optional

# Initialize FastAPI app
app = FastAPI(title="DemoApp API", version="1.0.0")

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://akashbv6680.github.io",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
DATABASE = "demoapp.db"

# Pydantic Models
class User(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class ChatMessage(BaseModel):
    message: str
    user_id: int

# Database initialization
def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''CREATE TABLE users
                    (id INTEGER PRIMARY KEY,
                     email TEXT UNIQUE,
                     name TEXT,
                     password TEXT,
                     created_at TIMESTAMP)''')
        c.execute('''CREATE TABLE messages
                    (id INTEGER PRIMARY KEY,
                     user_id INTEGER,
                     message TEXT,
                     response TEXT,
                     created_at TIMESTAMP)''')
        c.execute('''CREATE TABLE documents
                    (id INTEGER PRIMARY KEY,
                     user_id INTEGER,
                     filename TEXT,
                     content TEXT,
                     created_at TIMESTAMP)''')
        conn.commit()
        conn.close()

# JWT Token generation
def create_token(email: str, user_id: int) -> str:
    payload = {
        "email": email,
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Verify token
def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# Routes
@app.on_event("startup")
async def startup():
    init_db()

@app.get("/")
async def root():
    return {"message": "DemoApp API is running", "status": "ok"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/auth/signup")
async def signup(request: SignupRequest):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO users (email, name, password, created_at) VALUES (?, ?, ?, ?)",
                  (request.email, request.name, request.password, datetime.now()))
        conn.commit()
        
        # Get the user ID
        c.execute("SELECT id FROM users WHERE email = ?", (request.email,))
        user_id = c.fetchone()[0]
        conn.close()
        
        token = create_token(request.email, user_id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user_id, "email": request.email, "name": request.name}
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT id, name, password FROM users WHERE email = ?", (request.email,))
        user = c.fetchone()
        conn.close()
        
        if not user or user[2] != request.password:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user_id, name = user[0], user[1]
        token = create_token(request.email, user_id)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user_id, "email": request.email, "name": name}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(message: ChatMessage):
    try:
        # Store message
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Simulate AI response
        response_text = f"Response to: {message.message}"
        
        c.execute("INSERT INTO messages (user_id, message, response, created_at) VALUES (?, ?, ?, ?)",
                  (message.user_id, message.message, response_text, datetime.now()))
        conn.commit()
        conn.close()
        
        return {
            "message": message.message,
            "response": response_text,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages/{user_id}")
async def get_messages(user_id: int):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT message, response, created_at FROM messages WHERE user_id = ? ORDER BY created_at DESC",
                  (user_id,))
        messages = c.fetchall()
        conn.close()
        
        return {
            "messages": [
                {
                    "message": msg[0],
                    "response": msg[1],
                    "created_at": msg[2]
                } for msg in messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/upload")
async def upload_document(user_id: int, filename: str, content: str):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO documents (user_id, filename, content, created_at) VALUES (?, ?, ?, ?)",
                  (user_id, filename, content, datetime.now()))
        conn.commit()
        conn.close()
        
        return {"status": "success", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/{user_id}")
async def get_documents(user_id: int):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT id, filename, created_at FROM documents WHERE user_id = ?", (user_id,))
        documents = c.fetchall()
        conn.close()
        
        return {
            "documents": [
                {
                    "id": doc[0],
                    "filename": doc[1],
                    "created_at": doc[2]
                } for doc in documents
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search(user_id: int, query: str):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT filename, content FROM documents WHERE user_id = ? AND content LIKE ?",
                  (user_id, f"%{query}%"))
        results = c.fetchall()
        conn.close()
        
        return {
            "query": query,
            "results": [
                {
                    "filename": r[0],
                    "excerpt": r[1][:200] if len(r[1]) > 200 else r[1]
                } for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import json
import os
import shutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import Message, IdeaAnalysis, FileInput
from websocket_manager import ConnectionManager
from ai_service import analyze_text, analyze_file_content
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from dotenv import load_dotenv
from database import init_db, get_db_connection
import sqlite3

# Load environment variables
load_dotenv()

# Initialize Firebase
if not firebase_admin._apps:
    # Get credentials path from env or default to file
    cred_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
    if not os.path.exists(cred_path):
        print(f"Warning: Firebase credentials not found at {cred_path}")
    else:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()

# Initialize Local DB
@app.on_event("startup")
def startup_db():
    init_db()

# Create uploads directory
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Sync Logic ---
def sync_to_firebase():
    print("Starting sync to Firebase...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sync Messages
    cursor.execute("SELECT * FROM messages WHERE synced = 0")
    unsynced_messages = cursor.fetchall()
    
    for msg in unsynced_messages:
        try:
            chat_id = msg['chat_id']
            # Get Firestore Chat Doc
            chats_ref = db.collection("chats")
            query = chats_ref.where("id", "==", chat_id).limit(1).stream()
            
            for doc in query:
                messages_ref = doc.reference.collection("messages")
                
                msg_data = dict(msg)
                # Remove internal fields
                del msg_data['synced']
                del msg_data['chat_id'] # Firestore structure is hierarchical
                
                # Convert boolean back if needed (SQLite stores 0/1)
                msg_data['isPinned'] = bool(msg_data['isPinned'])
                
                # Add to Firestore
                messages_ref.add(msg_data)
                
                # Update last message
                doc.reference.update({
                    "lastMessage": msg_data.get("text", "Sent a file"),
                    "timestamp": msg_data.get("time")
                })
                
                # Mark as synced in SQLite
                conn.execute("UPDATE messages SET synced = 1 WHERE id = ?", (msg['id'],))
                conn.commit()
                print(f"Synced message {msg['id']}")
                
        except Exception as e:
            print(f"Failed to sync message {msg['id']}: {e}")
            
    conn.close()
    print("Sync complete.")

# --- Helper Functions ---

def get_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def create_user_doc(user_data):
    # Deprecated: Use inline SQL in endpoints + sync
    pass

def update_user_doc(user_id: int, update_data):
    # This should update SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Construct SET clause dynamically
    set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
    values = list(update_data.values())
    values.append(user_id)
    
    cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def get_chat_doc(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        chat = dict(row)
        # Parse JSON fields
        if chat.get("participants"):
            try:
                chat["participants"] = json.loads(chat["participants"])
            except:
                chat["participants"] = []
        return chat
    return None

# --- Endpoints ---



@app.get("/chats")
async def get_chats(user_id: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id:
        # This is tricky because participants is a JSON string.
        # For MVP, we fetch all and filter in Python, or use LIKE.
        # Fetching all is safer for now as we don't expect millions of chats.
        cursor.execute("SELECT * FROM chats")
    else:
        cursor.execute("SELECT * FROM chats")
        
    rows = cursor.fetchall()
    conn.close()
    
    chats = []
    for row in rows:
        chat = dict(row)
        # Parse JSON fields
        if chat.get("participants"):
            try:
                chat["participants"] = json.loads(chat["participants"])
            except:
                chat["participants"] = []
        if chat.get("createdBy"):
            try:
                chat["createdBy"] = json.loads(chat["createdBy"])
            except:
                chat["createdBy"] = None
        
        # Filter if user_id is provided
        if user_id:
            participants = chat.get("participants", [])
            if any(p.get("id") == user_id for p in participants):
                chats.append(chat)
        else:
            chats.append(chat)
            
    return chats

@app.post("/chats")
async def create_chat(chat_data: dict, background_tasks: BackgroundTasks):
    new_id = int(datetime.now().timestamp() * 1000)
    
    new_chat = {
        "id": new_id,
        "name": chat_data["name"],
        "type": chat_data.get("type", "group"),
        "participants": chat_data.get("participants", []),
        "avatar": chat_data.get("avatar", f"https://ui-avatars.com/api/?name={chat_data['name']}&background=random"),
        "members": len(chat_data.get("participants", [])),
        "lastMessage": "Tap to start chatting",
        "timestamp": datetime.now().isoformat(),
        "isPrivate": chat_data.get("isPrivate", False),
        "createdBy": chat_data.get("createdBy", None)
    }
    
    # 1. Save to SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    
    import json
    cursor.execute('''
        INSERT INTO chats (id, name, type, participants, avatar, lastMessage, timestamp, isPrivate, createdBy, synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (
        new_id,
        new_chat["name"],
        new_chat["type"],
        json.dumps(new_chat["participants"]),
        new_chat["avatar"],
        new_chat["lastMessage"],
        new_chat["timestamp"],
        1 if new_chat["isPrivate"] else 0,
        json.dumps(new_chat["createdBy"]) if new_chat["createdBy"] else None
    ))
    conn.commit()
    conn.close()
    
    # 2. Trigger Background Sync
    background_tasks.add_task(sync_to_firebase)
    
    return new_chat

@app.get("/chats/public")
async def get_public_chats():
    chats_ref = db.collection("chats")
    all_chats = [doc.to_dict() for doc in chats_ref.stream()]
    public_chats = [
        c for c in all_chats 
        if c.get("type") == "group" and not c.get("isPrivate", False)
    ]
    return public_chats

@app.post("/chats/join")
async def join_chat(request: dict):
    chat_id = request.get("chat_id")
    user = request.get("user")
    
    chat_doc_data = get_chat_doc(chat_id)
    
    if not chat_doc_data:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    participants = chat_doc_data.get("participants", [])
    if not any(p.get("id") == user["id"] for p in participants):
        participants.append(user)
        
        chats_ref = db.collection("chats")
        query = chats_ref.where("id", "==", chat_id).limit(1).stream()
        for doc in query:
            doc.reference.update({
                "participants": participants,
                "members": len(participants)
            })
            
    return {"message": "Joined chat", "chat": chat_doc_data}

@app.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: int):
    chat_doc_data = get_chat_doc(chat_id)
    if not chat_doc_data:
        return []
    
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    for doc in query:
        messages_ref = doc.reference.collection("messages")
        msgs = [m.to_dict() for m in messages_ref.order_by("id").stream()]
        return msgs
    return []

@app.post("/chats/{chat_id}/messages")
async def add_message(chat_id: int, message: Message, background_tasks: BackgroundTasks):
    # 1. Save to SQLite (Local First)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate ID using timestamp
    new_id = int(datetime.now().timestamp() * 1000)
    
    msg_dict = message.dict()
    msg_dict["id"] = new_id
    msg_dict["isPinned"] = False
    
    cursor.execute('''
        INSERT INTO messages (id, chat_id, text, sender, time, type, fileUrl, fileName, fileSize, isPinned, synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (
        new_id,
        chat_id,
        msg_dict.get("text"),
        msg_dict.get("sender"),
        msg_dict.get("time"),
        msg_dict.get("type"),
        msg_dict.get("fileUrl"),
        msg_dict.get("fileName"),
        msg_dict.get("fileSize"),
        0 # isPinned
    ))
    conn.commit()
    conn.close()
    
    # 2. Trigger Background Sync
    background_tasks.add_task(sync_to_firebase)
    
    return msg_dict

# --- Helper Functions ---

def get_user(user_id: int):
    # Query by integer ID field, not document ID (unless we migrate IDs to strings)
    # For MVP, we'll search the collection. Ideally, use string IDs as doc IDs.
    users_ref = db.collection("users")
    query = users_ref.where("id", "==", user_id).limit(1).stream()
    for doc in query:
        return doc.to_dict()
    return None

def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def create_user_doc(user_data):
    # Use email as doc ID or auto-gen. Let's use auto-gen for now but store ID.
    # To maintain integer IDs for frontend compatibility, we need to track max ID or just use timestamp/random int.
    # For simplicity in this migration, let's just use the provided ID.
    db.collection("users").add(user_data)

def update_user_doc(user_id: int, update_data):
    users_ref = db.collection("users")
    query = users_ref.where("id", "==", user_id).limit(1).stream()
    for doc in query:
        doc.reference.update(update_data)
        return

def get_chat_doc(chat_id: int):
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        data['doc_id'] = doc.id # Store doc_id for subcollection access
        return data
    return None

# --- Endpoints ---

@app.post("/login")
async def login(user_data: dict, background_tasks: BackgroundTasks):
    email = user_data.get("email")
    existing_user = get_user_by_email(email)
    
    if existing_user:
        return existing_user
    
    # New User
    new_id = int(datetime.now().timestamp() * 1000)

    new_user = {
        "id": new_id,
        "name": user_data.get("name", "User"),
        "email": email,
        "avatar": f"https://ui-avatars.com/api/?name={user_data.get('name', 'User')}&background=random",
        "status": "offline",
        "lastSeen": None
    }
    
    # 1. Save to SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (id, name, email, avatar, status, lastSeen, synced)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    ''', (
        new_user["id"],
        new_user["name"],
        new_user["email"],
        new_user["avatar"],
        new_user["status"],
        new_user["lastSeen"]
    ))
    conn.commit()
    conn.close()
    
    # 2. Trigger Sync
    background_tasks.add_task(sync_to_firebase)
    
    return new_user

@app.put("/users/{user_id}")
async def update_user(user_id: int, user_data: dict):
    user = get_user(user_id)
    if not user:
        return {"error": "User not found"}
    
    updates = {}
    if "name" in user_data:
        updates["name"] = user_data["name"]
        updates["avatar"] = f"https://ui-avatars.com/api/?name={user_data['name']}&background=random"
    
    if updates:
        update_user_doc(user_id, updates)
        # Return updated user
        user.update(updates)
        return user
    return user

@app.get("/ideas")
async def get_ideas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ideas ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    ideas = []
    for row in rows:
        idea = dict(row)
        idea["is_analyzed"] = bool(idea["is_analyzed"])
        ideas.append(idea)
    return ideas

@app.post("/ideas")
async def add_idea(idea: dict, background_tasks: BackgroundTasks):
    # idea: {title, content, tags}
    new_id = int(datetime.now().timestamp() * 1000)
    
    # Map frontend fields (title/content) to DB fields (text/category?)
    # Frontend sends: {text, category} based on IdeaHub.jsx?
    # Let's check IdeaHub.jsx. 
    # Actually, let's stick to what the DB has: text, category.
    # If frontend sends title/content, we might need to map.
    # But for now, let's assume frontend sends what we expect or we store it loosely.
    # DB has: text, category.
    # Old code used: title, content, tags.
    # Migration script used: text, category.
    # Let's assume we want text/category.
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ideas (id, text, category, votes, timestamp, is_analyzed, synced)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    ''', (
        new_id,
        idea.get("text") or idea.get("title"), # Fallback
        idea.get("category") or idea.get("content"), # Fallback/Misuse
        0,
        datetime.now().isoformat(),
        0
    ))
    conn.commit()
    conn.close()
    
    background_tasks.add_task(sync_to_firebase)
    
    # Return what frontend expects
    idea["id"] = new_id
    return idea

@app.delete("/ideas/{idea_id}")
async def delete_idea(idea_id: int, background_tasks: BackgroundTasks):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Idea not found")
    conn.commit()
    conn.close()
    
    background_tasks.add_task(sync_to_firebase)
    return {"message": "Idea deleted"}



@app.get("/chats/public")
async def get_public_chats():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Filter for public groups (type='group' and isPrivate=0)
    cursor.execute("SELECT * FROM chats WHERE type = 'group' AND isPrivate = 0")
    rows = cursor.fetchall()
    conn.close()
    
    public_chats = []
    for row in rows:
        chat = dict(row)
        # Parse JSON fields
        if chat.get("participants"):
            try:
                chat["participants"] = json.loads(chat["participants"])
            except:
                chat["participants"] = []
        public_chats.append(chat)
    return public_chats

@app.post("/chats/join")
async def join_chat(request: dict, background_tasks: BackgroundTasks):
    chat_id = request.get("chat_id")
    user = request.get("user")
    
    chat_doc_data = get_chat_doc(chat_id)
    
    if not chat_doc_data:
        # Auto-create if not exists (legacy behavior)
        new_chat = {
            "id": chat_id,
            "name": f"Group {chat_id}",
            "type": "group",
            "participants": [user],
            "avatar": f"https://ui-avatars.com/api/?name=Group {chat_id}&background=random",
            "members": 1,
            "lastMessage": "Tap to start chatting",
            "timestamp": datetime.now().isoformat(),
            "isPrivate": False,
            "createdBy": None
        }
        
        # Save to SQLite
        conn = get_db_connection()
        cursor = conn.cursor()
        import json
        cursor.execute('''
            INSERT INTO chats (id, name, type, participants, avatar, lastMessage, timestamp, isPrivate, createdBy, synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (
            new_chat["id"],
            new_chat["name"],
            new_chat["type"],
            json.dumps(new_chat["participants"]),
            new_chat["avatar"],
            new_chat["lastMessage"],
            new_chat["timestamp"],
            0,
            None
        ))
        conn.commit()
        conn.close()
        
        background_tasks.add_task(sync_to_firebase)
        return {"message": "Joined new chat", "chat": new_chat}
    
    # Update existing chat
    participants = chat_doc_data.get("participants", [])
    if not any(p.get("id") == user["id"] for p in participants):
        participants.append(user)
        
        # Update SQLite
        conn = get_db_connection()
        cursor = conn.cursor()
        import json
        cursor.execute('''
            UPDATE chats 
            SET participants = ?, synced = 0 
            WHERE id = ?
        ''', (json.dumps(participants), chat_id))
        conn.commit()
        conn.close()
        
        background_tasks.add_task(sync_to_firebase)
            
    return {"message": "Joined chat", "chat": chat_doc_data}

@app.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    
    msgs = []
    for row in rows:
        msg = dict(row)
        # Convert boolean fields (SQLite stores as 0/1)
        msg["isPinned"] = bool(msg["isPinned"])
        # Ensure ID is int
        msg["id"] = int(msg["id"])
        msgs.append(msg)
        
    return msgs

@app.post("/chats/{chat_id}/messages")
async def add_message(chat_id: int, message: Message, background_tasks: BackgroundTasks):
    # 1. Save to SQLite (Local First)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate ID using timestamp
    new_id = int(datetime.now().timestamp() * 1000)
    
    msg_dict = message.dict()
    msg_dict["id"] = new_id
    msg_dict["isPinned"] = False
    
    cursor.execute('''
        INSERT INTO messages (id, chat_id, text, sender, time, type, fileUrl, fileName, fileSize, isPinned, synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (
        new_id,
        chat_id,
        msg_dict.get("text"),
        msg_dict.get("sender"),
        msg_dict.get("time"),
        msg_dict.get("type"),
        msg_dict.get("fileUrl"),
        msg_dict.get("fileName"),
        msg_dict.get("fileSize"),
        0 # isPinned
    ))
    conn.commit()
    conn.close()
    
    # 2. Trigger Background Sync
    background_tasks.add_task(sync_to_firebase)
    
    return msg_dict

def sync_clear_messages(chat_id: int):
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    for doc in query:
        messages_ref = doc.reference.collection("messages")
        batch = db.batch()
        count = 0
        for msg in messages_ref.stream():
            batch.delete(msg.reference)
            count += 1
            if count >= 400:
                batch.commit()
                batch = db.batch()
                count = 0
        if count > 0:
            batch.commit()
        
        doc.reference.update({
            "lastMessage": "Chat cleared",
            "timestamp": datetime.now().isoformat()
        })

@app.delete("/chats/{chat_id}/messages")
async def clear_chat_messages(chat_id: int, background_tasks: BackgroundTasks):
    # 1. Delete from SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    
    # Update last message in chat
    cursor.execute('''
        UPDATE chats 
        SET lastMessage = 'Chat cleared', timestamp = ?, synced = 0 
        WHERE id = ?
    ''', (datetime.now().isoformat(), chat_id))
    
    conn.commit()
    conn.close()
    
    # 2. Background Sync
    background_tasks.add_task(sync_clear_messages, chat_id)
    background_tasks.add_task(sync_to_firebase) # For the chat update
    
    return {"message": "Chat cleared"}

def sync_delete_chat(chat_id: int):
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    for doc in query:
        # Delete messages
        messages_ref = doc.reference.collection("messages")
        batch = db.batch()
        for msg in messages_ref.stream():
            batch.delete(msg.reference)
            if len(batch) >= 400:
                batch.commit()
                batch = db.batch()
        if len(batch) > 0:
            batch.commit()
            
        # Delete chat doc
        doc.reference.delete()

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: int, background_tasks: BackgroundTasks):
    # 1. Delete from SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()
    
    # 2. Background Sync
    background_tasks.add_task(sync_delete_chat, chat_id)
    
    return {"message": "Chat deleted"}

@app.post("/chats/{chat_id}/messages/{message_id}/pin")
async def pin_message(chat_id: int, message_id: int):
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    
    for doc in query:
        messages_ref = doc.reference.collection("messages")
        msg_query = messages_ref.where("id", "==", message_id).limit(1).stream()
        
        for msg_doc in msg_query:
            msg_data = msg_doc.to_dict()
            new_status = not msg_data.get("isPinned", False)
            msg_doc.reference.update({"isPinned": new_status})
            
            msg_data["isPinned"] = new_status
            return msg_data
            
    raise HTTPException(status_code=404, detail="Message not found")

@app.put("/chats/{chat_id}/messages/{message_id}")
async def update_message(chat_id: int, message_id: int, updates: dict):
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    
    for doc in query:
        messages_ref = doc.reference.collection("messages")
        msg_query = messages_ref.where("id", "==", message_id).limit(1).stream()
        
        for msg_doc in msg_query:
            msg_doc.reference.update(updates)
            updated_data = msg_doc.to_dict()
            updated_data.update(updates)
            return updated_data
            
    raise HTTPException(status_code=404, detail="Message not found")

@app.delete("/chats/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: int, message_id: int):
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    
    for doc in query:
        messages_ref = doc.reference.collection("messages")
        msg_query = messages_ref.where("id", "==", message_id).limit(1).stream()
        
        for msg_doc in msg_query:
            msg_doc.reference.delete()
            return {"message": "Message deleted"}
            
    raise HTTPException(status_code=404, detail="Message not found")



@app.post("/chats/{chat_id}/participants")
async def add_participant(chat_id: int, user_data: dict):
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    user_to_add = get_user_by_email(email)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")
        
    chats_ref = db.collection("chats")
    query = chats_ref.where("id", "==", chat_id).limit(1).stream()
    
    for doc in query:
        chat_data = doc.to_dict()
        participants = chat_data.get("participants", [])
        
        # Check if already in chat
        if any(p.get("id") == user_to_add["id"] for p in participants):
             raise HTTPException(status_code=400, detail="User already in chat")
             
        participants.append(user_to_add)
        
        doc.reference.update({
            "participants": participants,
            "members": len(participants)
        })
        
        return {"message": "User added", "user": user_to_add}
            
    raise HTTPException(status_code=404, detail="Chat not found")

@app.get("/chats/{chat_id}/participants")
async def get_participants(chat_id: int):
    chat = get_chat_doc(chat_id)
    if chat:
        return chat.get("participants", [])
    return []

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    return {"url": f"http://localhost:8000/uploads/{file.filename}"}

@app.post("/analyze-message")
async def analyze_message_endpoint(analysis_request: IdeaAnalysis):
    is_idea, confidence = analyze_text(analysis_request.text)
    
    if is_idea:
        # Save to Firestore ideas
        new_idea = {
            "title": f"Idea from {analysis_request.sender}",
            "content": analysis_request.text,
            "tags": ["AI Detected"],
            "timestamp": datetime.now().isoformat()
        }
        # Add ID
        ideas_ref = db.collection("ideas")
        count = len(list(ideas_ref.stream()))
        new_idea["id"] = count + 1
        
        db.collection("ideas").add(new_idea)
        
    return {"is_idea": is_idea, "confidence": confidence}

from file_extractor import extract_text

@app.post("/analyze-file")
async def analyze_file_endpoint(file_input: FileInput):
    file_path = f"uploads/{file_input.filename}"
    
    try:
        # Extract text content
        extracted_text = extract_text(file_path)
        
        if not extracted_text or "Unsupported" in extracted_text:
            if not extracted_text:
                extracted_text = f"File: {file_input.filename}"
                
        # Analyze the extracted text
        analysis = analyze_text(extracted_text)
        
        # Force is_idea to True since user explicitly requested it
        analysis.is_idea = True
        
        if analysis.is_idea:
             new_idea = {
                "title": f"File Idea: {file_input.filename}",
                "content": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
                "full_content": extracted_text,
                "tags": ["File", "AI Detected", analysis.category or "General"],
                "timestamp": datetime.now().isoformat(),
                "priority": analysis.priority,
                "viability_score": analysis.viability_score,
                "deadline": analysis.deadline,
                "action_suggestion": analysis.action_suggestion
            }
             ideas_ref = db.collection("ideas")
             count = len(list(ideas_ref.stream()))
             new_idea["id"] = count + 1
             
             db.collection("ideas").add(new_idea)
             
        return analysis
    except Exception as e:
        print(f"Error analyzing file: {e}")
        # Fallback to simple analysis
        return {"is_idea": False, "error": str(e)}


# WebSocket for real-time (Optional: Integrate with Firestore listeners later)
manager = ConnectionManager()

@app.websocket("/ws/{chat_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, user_id: int):
    await manager.connect(websocket, chat_id, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Here we could save to Firestore too, but we use REST for saving currently
            # Just broadcast for now
            await manager.broadcast(data, chat_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id, user_id)

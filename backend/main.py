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
from database import init_db, get_db_connection, get_db_cursor
import psycopg2
from redis_client import redis_client

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

# WebSocket Manager
manager = ConnectionManager()

# Initialize DB & Redis
@app.on_event("startup")
async def startup_event():
    init_db() # Ensure tables exist
    await redis_client.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()

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
    cursor = get_db_cursor(conn)
    
    # Sync Messages
    cursor.execute("SELECT * FROM messages WHERE synced = FALSE")
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
                
                # Mark as synced in Postgres
                conn.cursor().execute("UPDATE messages SET synced = TRUE WHERE id = %s", (msg['id'],))
                conn.commit()
                print(f"Synced message {msg['id']}")
                
        except Exception as e:
            print(f"Failed to sync message {msg['id']}: {e}")
            
    conn.close()
    print("Sync complete.")

# --- Helper Functions ---

def get_user(user_id: int):
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def create_user_doc(user_data):
    # Deprecated: Use inline SQL in endpoints + sync
    pass

def update_user_doc(user_id: int, update_data):
    # This should update Postgres
    conn = get_db_connection()
    cursor = conn.cursor() # Standard cursor for updates is fine
    
    # Construct SET clause dynamically
    set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
    values = list(update_data.values())
    values.append(user_id)
    
    cursor.execute(f"UPDATE users SET {set_clause} WHERE id = %s", values)
    conn.commit()
    conn.close()

def get_chat_doc(chat_id: int):
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM chats WHERE id = %s", (chat_id,))
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



# --- Endpoints ---

@app.get("/chats")
async def get_chats(user_id: int = None):
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    if user_id:
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
    import traceback
    try:
        print(f"Received chat_data: {chat_data}")
        # Use Postgres SERIAL or manual ID? We used timestamp manual ID in SQLite.
        # Postgres supports BIGINT Primary Key, so manual ID is fine.
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
        
        # 1. Save to Postgres
        conn = get_db_connection()
        cursor = conn.cursor()
        
        import json
        cursor.execute('''
            INSERT INTO chats (id, name, type, participants, avatar, lastMessage, timestamp, isPrivate, createdBy, synced)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
        ''', (
            new_id,
            new_chat["name"],
            new_chat["type"],
            json.dumps(new_chat["participants"]),
            new_chat["avatar"],
            new_chat["lastMessage"],
            new_chat["timestamp"],
            new_chat["isPrivate"], # Postgres handles bool natively
            json.dumps(new_chat["createdBy"]) if new_chat["createdBy"] else None
        ))
        conn.commit()
        conn.close()
        
        # 2. Trigger Background Sync
        background_tasks.add_task(sync_to_firebase)
        
        return new_chat
    except Exception as e:
        error_msg = f"Error creating chat: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        with open("backend_debug.txt", "a") as f:
            f.write(f"[{datetime.now()}] {error_msg}\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chats/join")
async def join_chat(request: dict):
    chat_id = request.get("chat_id")
    user = request.get("user")
    
    chat_doc_data = get_chat_doc(chat_id)
    
    if not chat_doc_data:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    participants = chat_doc_data.get("participants", [])
    # Parse if string
    if isinstance(participants, str):
        participants = json.loads(participants)

    if not any(p.get("id") == user["id"] for p in participants):
        participants.append(user)
        
        # Update Postgres. get_chat_doc handles fetch. update needs specific call
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE chats SET participants = %s, synced = FALSE WHERE id = %s", 
                       (json.dumps(participants), chat_id))
        conn.commit()
        conn.close()
            
    return {"message": "Joined chat", "chat": chat_doc_data}

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
    
    # 1. Save to Postgres
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (id, name, email, avatar, status, lastSeen, synced)
        VALUES (%s, %s, %s, %s, %s, %s, FALSE)
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
    cursor = get_db_cursor(conn)
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
    new_id = int(datetime.now().timestamp() * 1000)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ideas (id, text, category, votes, timestamp, is_analyzed, synced)
        VALUES (%s, %s, %s, %s, %s, %s, FALSE)
    ''', (
        new_id,
        idea.get("text") or idea.get("title"), 
        idea.get("category") or idea.get("content"), 
        0,
        datetime.now().isoformat(),
        False
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
    cursor.execute("DELETE FROM ideas WHERE id = %s", (idea_id,))
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
    cursor = get_db_cursor(conn)
    # Filter for public groups (type='group' and isPrivate=FALSE)
    cursor.execute("SELECT * FROM chats WHERE type = 'group' AND isPrivate = FALSE")
    rows = cursor.fetchall()
    conn.close()
    
    public_chats = []
    for row in rows:
        chat = dict(row)
        # Parse JSON fields
        if chat.get("participants") and isinstance(chat["participants"], str):
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
    # 1. Read from Postgres
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT participants FROM chats WHERE id = %s", (chat_id,))
    row = cursor.fetchone()
    
    if not row:
        # If not in SQLite but in Firestore (edge case), we might need to fetch from Firestore.
        # But for "Local First", we assume SQLite is master or synced.
        # If missing in SQLite, we should probably fetch from Firestore or error.
        # Given the hybrid nature, let's try to get from SQLite.
        pass 
    
    participants = []
    if row:
        import json
        try:
            participants = json.loads(row["participants"])
        except:
            participants = []
            
    if not any(p.get("id") == user["id"] for p in participants):
        participants.append(user)
        
        # Update Postgres
        # Logic above reuses conn implicitly if not closed, but here we closed nothing.
        # Actually line 512 closes conn.
        # Let's keep it clean.
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE chats 
            SET participants = %s, synced = FALSE 
            WHERE id = %s
        ''', (json.dumps(participants), chat_id))
        conn.commit()
        
        background_tasks.add_task(sync_to_firebase)
        
    conn.close()
            
    return {"message": "Joined chat", "chat": {"id": chat_id, "participants": participants}}



@app.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: int, user_id: int = None):
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM messages WHERE chat_id = %s ORDER BY id ASC", (chat_id,))
    messages = []
    
    import json
    
    for row in cursor.fetchall():
        msg = dict(row)
        
        # Check 'Delete for Me' logic
        if user_id and msg.get("deleted_for"):
            try:
                deleted_for_list = json.loads(msg["deleted_for"])
                # print(f"DEBUG: msg {msg['id']} deleted_for={deleted_for_list} user_id={user_id}")
                if any(str(u) == str(user_id) for u in deleted_for_list):
                    # print(f"DEBUG: Skipping msg {msg['id']}")
                    continue # Skip this message
            except Exception as e:
                print(f"DEBUG: Error parsing deleted_for: {e}")
                pass
                
        # Parse replyTo JSON if it exists
        if msg.get("replyTo"):
            try:
                msg["replyTo"] = json.loads(msg["replyTo"])
            except:
                msg["replyTo"] = None
        messages.append(msg)
    conn.close()
    return messages

@app.post("/chats/{chat_id}/messages")
async def add_message(chat_id: int, message: Message, background_tasks: BackgroundTasks):
    # 1. Save to Postgres
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate ID using timestamp
    # Postgres supports BIGINT, manual ID is ok.
    new_id = int(datetime.now().timestamp() * 1000)
    
    msg_dict = message.dict()
    
    msg_dict["id"] = new_id
    msg_dict["isPinned"] = False
    
    cursor.execute('''
        INSERT INTO messages (id, chat_id, text, sender, time, type, fileUrl, fileName, fileSize, isPinned, callRoomName, callStatus, isVoice, replyTo, synced)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
    ''', (
        new_id,
        chat_id,
        msg_dict.get("text"),
        msg_dict.get("sender"),
        msg_dict.get("time"),
        msg_dict.get("type"),
        msg_dict.get("fileUrl"),
        msg_dict.get("filename"),
        msg_dict.get("size"),
        False, # isPinned
        msg_dict.get("callRoomName"),
        msg_dict.get("callStatus"),
        msg_dict.get("isVoice", False),
        json.dumps(msg_dict.get("replyTo")) if msg_dict.get("replyTo") else None
    ))
    
    # Self-Healing: Check if sender is in participants, if not add them
    try:
        sender_id = msg_dict.get("sender")
        if sender_id and sender_id != 'me':
             # Try to interpret sender_id as int if possible
             try:
                 sender_int = int(sender_id)
             except:
                 sender_int = sender_id
                 
             # Re-get cursor as dict
             dict_cursor = get_db_cursor(conn)
             dict_cursor.execute("SELECT participants FROM chats WHERE id = %s", (chat_id,))
             chat_row = dict_cursor.fetchone()
             if chat_row:
                 parts = json.loads(chat_row["participants"])
                 if not any(str(p.get("id")) == str(sender_int) for p in parts):
                     # Fetch user query
                     dict_cursor.execute("SELECT * FROM users WHERE id = %s", (sender_int,))
                     user_row = dict_cursor.fetchone()
                     if user_row:
                         user_data = dict(user_row)
                         new_part = {
                             "id": user_data["id"],
                             "name": user_data["name"],
                             "email": user_data["email"],
                             "avatar": user_data["avatar"]
                         }
                         parts.append(new_part)
                         cursor.execute("UPDATE chats SET participants = %s WHERE id = %s", 
                                      (json.dumps(parts), chat_id))
                                      
                         # Broadcast updated participants list
                         await manager.broadcast({
                             "type": "participant_update",
                             "participants": parts
                         }, chat_id)
    except Exception as e:
        print(f"Self-healing participant error: {e}")
        
    conn.commit()
    conn.close()
    
    # 2. Trigger Background Sync
    background_tasks.add_task(sync_to_firebase)
    
    # 3. Broadcast via WebSocket (Uses Redis Pub/Sub internally now)
    await manager.broadcast(msg_dict, chat_id)
    
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
    # 1. Delete from Postgres
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = %s", (chat_id,))
    
    # Update last message in chat
    cursor.execute('''
        UPDATE chats 
        SET lastMessage = 'Chat cleared', timestamp = %s, synced = FALSE 
        WHERE id = %s
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
        # Delete messages first
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
    # 1. Soft/Hard Delete from Postgres
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = %s", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE id = %s", (chat_id,))
    conn.commit()
    conn.close()
    
    # 2. Background Sync
    background_tasks.add_task(sync_delete_chat, chat_id)
    
    return {"message": "Chat deleted"}

@app.post("/chats/{chat_id}/messages/{message_id}/delete_for_me")
async def delete_message_for_me(chat_id: int, message_id: int, request: dict):
    print(f"DEBUG: delete_message_for_me hit. chat_id={chat_id}, msg_id={message_id}, request={request}")
    user_id = request.get("user_id")
    if not user_id:
        print("DEBUG: user_id missing")
        raise HTTPException(status_code=400, detail="user_id required")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch current deleted_for
    cursor.execute("SELECT deleted_for FROM messages WHERE id = %s", (message_id,))
    row = cursor.fetchone()
    if not row:
        print("DEBUG: Message not found")
        conn.close()
        raise HTTPException(status_code=404, detail="Message not found")
        
    current_deleted_for = row[0]
    deleted_list = []
    if current_deleted_for:
        try:
            deleted_list = json.loads(current_deleted_for)
        except:
            deleted_list = []
            
    # 2. Add user_id if not present
    if user_id not in deleted_list:
        deleted_list.append(user_id)
        cursor.execute("UPDATE messages SET deleted_for = %s WHERE id = %s", (json.dumps(deleted_list), message_id))
        conn.commit()
        
    conn.close()
    return {"status": "success", "deleted_for": deleted_list}

@app.post("/chats/{chat_id}/messages/{message_id}/pin")
async def pin_message(chat_id: int, message_id: int):
    # TODO: This endpoint used Firestore only? It should update Postgres too.
    # The original implementation only updated Firestore!
    # I should verify this.
    # Original: chats_ref = db.collection...
    # I should add Postgres update.
    
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT isPinned FROM messages WHERE id = %s", (message_id,))
    row = cursor.fetchone()
    
    new_status = False
    if row:
        new_status = not row["isPinned"]
        cursor.execute("UPDATE messages SET isPinned = %s, synced = FALSE WHERE id = %s", (new_status, message_id))
        conn.commit()
    
    conn.close()
    
    # Also update Firestore (Hybrid)
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
async def update_message(chat_id: int, message_id: int, updates: dict, background_tasks: BackgroundTasks):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Update Postgres
    fields = []
    values = []
    for k, v in updates.items():
        if k in ['text', 'callStatus', 'isPinned', 'replyTo']: # Allowed fields
            fields.append(f"{k} = %s")
            if isinstance(v, (dict, list)):
                values.append(json.dumps(v))
            else:
                values.append(v)
                
    if not fields:
        conn.close()
        return {"error": "No valid fields to update"}
        
    values.append(message_id) # For WHERE clause
    
    cursor.execute(f"UPDATE messages SET {', '.join(fields)} WHERE id = %s", values)
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Message not found in local DB")
        
    conn.commit()
    
    # 2. Fetch updated message
    cursor = get_db_cursor(conn) # Switch to dict cursor
    cursor.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
    row = cursor.fetchone()
    updated_msg = dict(row)
    
    if updated_msg.get("replyTo"):
         try:
             updated_msg["replyTo"] = json.loads(updated_msg["replyTo"])
         except:
             pass
             
    conn.close()
    
    # 3. Broadcast
    await manager.broadcast(updated_msg, chat_id)
    
    # 4. Background Sync (Firestore)
    def sync_update():
        chats_ref = db.collection("chats")
        query = chats_ref.where("id", "==", chat_id).limit(1).stream()
        for doc in query:
            messages_ref = doc.reference.collection("messages")
            msg_query = messages_ref.where("id", "==", message_id).limit(1).stream()
            for msg_doc in msg_query:
                msg_doc.reference.update(updates)
                
    background_tasks.add_task(sync_update)
    
    return updated_msg

@app.delete("/chats/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: int, message_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Soft Delete in Postgres
    updates = {
        "text": "🚫 This message was deleted",
        "type": "text",
        "fileUrl": None,
        "fileName": None, 
        "fileSize": None,
        "callStatus": None,
        "callRoomName": None,
        "isVoice": None,
        "replyTo": None,
        "isDeleted": True 
    }
    
    cursor.execute("""
        UPDATE messages 
        SET text = %s, type = %s, fileUrl = NULL, fileName = NULL, 
            fileSize = NULL, callStatus = NULL, callRoomName = NULL, 
            isVoice = NULL, replyTo = NULL, isDeleted = TRUE
        WHERE id = %s
    """, (updates["text"], updates["type"], message_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Message not found")
        
    conn.commit()
    
    # Fetch updated message for broadcast
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
    updated_msg = dict(cursor.fetchone())
    conn.close()
    
    # 2. Broadcast Update
    await manager.broadcast(updated_msg, chat_id)
    
    # 3. Background Sync (Firestore)
    def sync_soft_delete():
        chats_ref = db.collection("chats")
        query = chats_ref.where("id", "==", chat_id).limit(1).stream()
        for doc in query:
            messages_ref = doc.reference.collection("messages")
            msg_query = messages_ref.where("id", "==", message_id).limit(1).stream()
            for msg_doc in msg_query:
                msg_doc.reference.update(updates)

    sync_soft_delete()
    
    return {"status": "success", "message": "Message deleted"}

@app.post("/chats/{chat_id}/participants")
async def add_participant(chat_id: int, user_data: dict, background_tasks: BackgroundTasks):
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    user_to_add = get_user_by_email(email)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")
        
    # 1. Update Postgres
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    # Get current participants from SQLite
    cursor.execute("SELECT participants FROM chats WHERE id = %s", (chat_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Chat not found")
        
    import json
    current_participants = json.loads(row["participants"])
    
    # Check if already in chat
    if any(p.get("id") == user_to_add["id"] for p in current_participants):
         conn.close()
         raise HTTPException(status_code=400, detail="User already in chat")
         
    current_participants.append(user_to_add)
    
    cursor.execute("UPDATE chats SET participants = %s, synced = FALSE WHERE id = %s", 
                  (json.dumps(current_participants), chat_id))
    conn.commit()
    conn.close()
    
    # 2. Background Sync
    background_tasks.add_task(sync_to_firebase)
    
    return {"message": "User added", "user": user_to_add}

@app.get("/chats/{chat_id}/participants")
async def get_participants(chat_id: int):
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT participants FROM chats WHERE id = %s", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        import json
        try:
            return json.loads(row["participants"])
        except:
            return []
    return []

@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    return {"url": f"/uploads/{file.filename}"}

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


@app.websocket("/ws/{chat_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, user_id: int):
    await manager.connect(websocket, chat_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                
                # 1. Save to Postgres
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Default values
                msg_id = message_data.get("id", int(datetime.now().timestamp() * 1000))
                text = message_data.get("text", "")
                sender = message_data.get("sender", str(user_id)) # Fallback to user_id path param
                time_str = message_data.get("time", datetime.now().strftime("%H:%M"))
                msg_type = message_data.get("type", "text")
                file_url = message_data.get("fileUrl", "")
                file_name = message_data.get("filename", "")
                file_size = message_data.get("size", "")
                
                cursor.execute('''
                    INSERT INTO messages (id, chat_id, text, sender, time, type, fileUrl, fileName, fileSize, synced)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                ''', (
                    msg_id,
                    chat_id,
                    text,
                    sender,
                    time_str,
                    msg_type,
                    file_url,
                    file_name,
                    file_size
                ))
                
                # Update Chat's Last Message
                last_msg_preview = text if msg_type == 'text' else f"Sent a {msg_type}"
                cursor.execute('UPDATE chats SET lastMessage = %s, timestamp = %s WHERE id = %s', 
                               (last_msg_preview, datetime.now().isoformat(), chat_id))
                
                conn.commit()
                conn.close()
                
                # 2. Broadcast to Room (via Redis)
                await manager.broadcast(message_data, chat_id)
                
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {data}")
            except Exception as e:
                print(f"Error processing message: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)

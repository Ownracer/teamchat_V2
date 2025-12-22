from fastapi import WebSocket
from typing import List, Dict
import json
import asyncio
from redis_client import redis_client

class ConnectionManager:
    def __init__(self):
        # Store active connections: chat_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Keep track of redis listener tasks: chat_id -> Task
        self.redis_tasks: Dict[int, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, chat_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
            # Start Redis Listener for this chat if first user
            self.redis_tasks[chat_id] = asyncio.create_task(self.subscribe_to_chat(chat_id))
            
        self.active_connections[chat_id].append(websocket)
        print(f"WS: Client connected to chat {chat_id}. Total: {len(self.active_connections[chat_id])}")

    def disconnect(self, websocket: WebSocket, chat_id: int):
        if chat_id in self.active_connections:
            if websocket in self.active_connections[chat_id]:
                self.active_connections[chat_id].remove(websocket)
                print(f"WS: Client disconnected from chat {chat_id}. Total: {len(self.active_connections[chat_id])}")
            
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
                # Allow task to be cancelled or cleanup if needed
                if chat_id in self.redis_tasks:
                    self.redis_tasks[chat_id].cancel()
                    del self.redis_tasks[chat_id]

    async def subscribe_to_chat(self, chat_id: int):
        redis = redis_client.get_client()
        if not redis:
            print("Redis client not initialized")
            return

        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:{chat_id}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    # Send to all local connections for this chat
                    if chat_id in self.active_connections:
                        for connection in self.active_connections[chat_id]:
                            try:
                                await connection.send_json(data)
                            except Exception as e:
                                print(f"WS: Error sending message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Redis Subscribe Error chat {chat_id}: {e}")
        finally:
            await pubsub.unsubscribe(f"chat:{chat_id}")
            await pubsub.close()

    async def broadcast(self, message: dict, chat_id: int):
        # Instead of local loop, Publish to Redis
        redis = redis_client.get_client()
        if redis:
            await redis.publish(f"chat:{chat_id}", json.dumps(message))
        else:
            print("Redis not connected, skipping publish")

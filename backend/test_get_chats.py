import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_get_chats():
    print(f"Testing get_chats at {BASE_URL}/chats...")
    try:
        res = requests.get(f"{BASE_URL}/chats")
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            chats = res.json()
            print(f"Found {len(chats)} chats.")
            for chat in chats:
                print(f"- {chat.get('name')} (ID: {chat.get('id')})")
        else:
            print("Response Text:", res.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_get_chats()

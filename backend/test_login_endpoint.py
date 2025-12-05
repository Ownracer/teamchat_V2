import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_login():
    print(f"Testing login at {BASE_URL}/login...")
    payload = {
        "email": "test@example.com",
        "name": "Test User"
    }
    try:
        res = requests.post(f"{BASE_URL}/login", json=payload)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            print("Response:", res.json())
        else:
            print("Response Text:", res.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_login()

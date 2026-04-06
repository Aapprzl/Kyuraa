import requests
import json

BASE_URL = "http://127.0.0.1:8766"
TOKEN = "73c6aad46fe246ef"
HEADERS = {"X-API-Key": TOKEN}

def test_switching():
    print(f"--- Testing Provider Switching ---")
    
    # 1. Get current settings
    print("1. Fetching current settings...")
    try:
        r = requests.get(f"{BASE_URL}/settings", headers=HEADERS)
        r.raise_for_status()
        settings = r.json()
        current = settings.get("active_provider")
        print(f"Current: {current}")
        
        # 2. Switch to the other one
        target = "google" if current == "openrouter" else "openrouter"
        print(f"2. Switching to {target}...")
        
        payload = {
            "provider": target,
            "model": "google/gemini-2.0-flash:free" if target == "google" else "qwen/qwen3.6-plus:free",
            "api_key": "********"  # Use masked key to test resolve
        }
        
        r = requests.post(f"{BASE_URL}/settings/validate-and-save", headers=HEADERS, json=payload)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
        
        # 3. Verify
        r = requests.get(f"{BASE_URL}/settings", headers=HEADERS)
        settings = r.json()
        new_active = settings.get("active_provider")
        print(f"3. New active: {new_active}")
        
        if new_active == target:
            print("\nSUCCESS: AI configuration changed successfully!")
        else:
            print("\nFAILED: AI configuration did not change.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_switching()

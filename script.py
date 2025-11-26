import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = "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" # ← your actual API key here


headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "mistralai/mistral-7b-instruct:free",
    "messages": [{"role": "user", "content": "Suggest a birthday gift for a 10-year-old who loves drawing"}],
    "temperature": 0.7
}

response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

print("Status:", response.status_code)
print("Response:", response.text)

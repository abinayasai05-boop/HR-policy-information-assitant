import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("API key not found. Check your .env file.")
    raise SystemExit(1)

try:
    client = genai.Client(api_key=api_key)
    print("Checking available Gemini models...\n")

    for model in client.models.list():
        actions = getattr(model, "supported_actions", []) or []
        if "generateContent" in actions:
            print(model.name)

except Exception as e:
    print("ERROR TYPE:", type(e).__name__)
    print("ERROR DETAILS:", str(e))


import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("ERROR: Gemini API key not found in .env")
    raise SystemExit(1)

try:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=20000),
    )

    print("Testing Gemini connection...")

    response = client.models.generate_content(
        model="gemini-3.7-flash",
        contents="Reply with: Gemini connection successful",
    )

    print("SUCCESS:", response.text)

except Exception as e:
    print("ERROR TYPE:", type(e).__name__)
    print("ERROR DETAILS:", str(e))
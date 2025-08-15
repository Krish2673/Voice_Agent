from google import genai
from backend.utils.config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_llm_response(conversation: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=conversation
    )
    return response.text

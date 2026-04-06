from google import genai
from google.genai import types
import os
import re
import time
from dotenv import load_dotenv

# Load API Keys
load_dotenv()
API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]
# Filter out empty/placeholder keys
API_KEYS = [k for k in API_KEYS if k and k != "YOUR_SECOND_API_KEY_HERE" and k != "YOUR_THIRD_API_KEY_HERE"]

print(f"Loaded {len(API_KEYS)} API key(s)")

# Track which key is currently active
current_key_index = 0

# Request tuning for cloud deployments like Render
KEY_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "12"))
KEY_RETRIES = int(os.getenv("GEMINI_RETRIES_PER_KEY", "2"))
RETRY_DELAY = float(os.getenv("GEMINI_RETRY_DELAY_SECONDS", "1"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# System prompt to get short, voice-friendly responses
SYSTEM_PROMPT = """You are a helpful voice assistant. 
Keep your answers SHORT and CONVERSATIONAL (2-3 sentences max).
Do NOT use markdown, bullet points, numbered lists, or any special formatting.
Speak naturally as if you are talking to someone.
Be concise and direct."""

def clean_for_speech(text):
    """Remove markdown and special characters so pyttsx3 can speak cleanly."""
    text = re.sub(r'\*+', '', text)        # Remove asterisks (bold/italic)
    text = re.sub(r'#+\s*', '', text)      # Remove headings
    text = re.sub(r'`+', '', text)         # Remove code backticks
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links -> just text
    text = re.sub(r'\n+', '. ', text)      # Newlines -> periods
    text = re.sub(r'\s+', ' ', text)       # Collapse whitespace
    return text.strip()

def get_ai_response(prompt):
    """Gets a response from Gemini AI with per-key retries and key rotation."""
    global current_key_index

    if not API_KEYS:
        return "No API keys configured. Please add keys in your .env file."

    total_keys = len(API_KEYS)
    last_error = None

    for attempt in range(total_keys):
        key_num = current_key_index + 1
        key = API_KEYS[current_key_index]

        for retry_index in range(KEY_RETRIES):
            try:
                print(
                    f"Attempt {attempt + 1}/{total_keys}, retry {retry_index + 1}/{KEY_RETRIES} "
                    f"- Key {key_num} (timeout: {KEY_TIMEOUT}s, model: {MODEL_NAME})"
                )
                start_time = time.time()

                # Use SDK-native request timeout to avoid thread issues in web workers
                client = genai.Client(api_key=key, http_options={"timeout": KEY_TIMEOUT})

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        max_output_tokens=150,
                    ),
                )

                elapsed = round(time.time() - start_time, 2)
                print(f"API Key {key_num} succeeded in {elapsed}s")
                return clean_for_speech(response.text)

            except Exception as e:
                elapsed = round(time.time() - start_time, 2)
                error_msg = str(e).lower()

                if "timeout" in error_msg or "timed out" in error_msg:
                    print(f"API Key {key_num} timed out after {elapsed}s")
                    last_error = f"Key {key_num} timed out after {KEY_TIMEOUT}s"
                else:
                    print(f"API Key {key_num} failed: {str(e)}")
                    last_error = str(e)

                if retry_index < KEY_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (retry_index + 1))

        # Switch to next key
        old_key = current_key_index + 1
        current_key_index = (current_key_index + 1) % total_keys
        new_key = current_key_index + 1
        print(f"Switching from Key {old_key} to Key {new_key}...")

    if last_error and "timed out" in last_error.lower():
        return (
            "The AI service is taking too long to respond right now. "
            "Please try again in a few seconds."
        )

    return f"All {total_keys} API keys failed. Last error: {last_error}"

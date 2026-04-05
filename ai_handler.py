from google import genai
from google.genai import types
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
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

print(f"✅ Loaded {len(API_KEYS)} API key(s)")

# Track which key is currently active
current_key_index = 0

# Maximum time (seconds) to wait for each key before switching
KEY_TIMEOUT = 3

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

def _call_gemini(key, prompt):
    """Make a single Gemini API call (runs inside a thread for timeout)."""
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=150
        )
    )
    return response.text

def get_ai_response(prompt):
    """Gets a response from Gemini AI, with 3s timeout per key and auto-switching."""
    global current_key_index

    if not API_KEYS:
        return "No API keys configured. Please add keys in your .env file."

    total_keys = len(API_KEYS)
    last_error = None

    for attempt in range(total_keys):
        key_num = current_key_index + 1
        key = API_KEYS[current_key_index]

        try:
            print(f"🔑 Attempt {attempt + 1}/{total_keys} — Using API Key {key_num} (timeout: {KEY_TIMEOUT}s)...")
            start_time = time.time()

            # Run the API call in a thread with a timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini, key, prompt)
                result = future.result(timeout=KEY_TIMEOUT)

            elapsed = round(time.time() - start_time, 2)
            print(f"✅ API Key {key_num} succeeded in {elapsed}s!")
            return clean_for_speech(result)

        except TimeoutError:
            elapsed = round(time.time() - start_time, 2)
            print(f"⏰ API Key {key_num} TIMED OUT after {elapsed}s!")
            last_error = f"Key {key_num} timed out after {KEY_TIMEOUT}s"

        except Exception as e:
            error_msg = str(e)
            print(f"❌ API Key {key_num} FAILED: {error_msg}")
            last_error = error_msg

        # Switch to next key
        old_key = current_key_index + 1
        current_key_index = (current_key_index + 1) % total_keys
        new_key = current_key_index + 1
        print(f"🔄 Switching from Key {old_key} → Key {new_key}...")

    return f"All {total_keys} API keys failed. Last error: {last_error}"

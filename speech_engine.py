import asyncio
import os
import tempfile

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    import pygame
except ImportError:
    pygame = None

_mixer_ready = False


def _ensure_mixer():
    global _mixer_ready

    if pygame is None or _mixer_ready:
        return _mixer_ready

    try:
        pygame.mixer.init()
        _mixer_ready = True
    except Exception as e:
        print(f"Audio playback unavailable: {e}")

    return _mixer_ready

# ============================================
# VOICE MOODS - Choose your assistant's voice!
# ============================================
VOICE_MOODS = {
    "friendly":  "en-US-JennyNeural",       # Warm, friendly female
    "professional": "en-US-GuyNeural",       # Clear, professional male
    "cheerful":  "en-US-AriaNeural",         # Energetic, cheerful female
    "calm":      "en-US-DavisNeural",        # Calm, relaxed male
    "news":      "en-US-JennyMultilingualNeural",  # News-reader style
    "indian":    "en-IN-NeerjaNeural",       # Indian English female
    "indian_male": "en-IN-PrabhatNeural",    # Indian English male
}

# >>>  SET YOUR PREFERRED VOICE MOOD HERE  <<<
CURRENT_MOOD = "indian"

def toggle_voice():
    """Toggles between girl and boy voice."""
    global CURRENT_MOOD
    if CURRENT_MOOD == "indian":
        CURRENT_MOOD = "indian_male"
    else:
        CURRENT_MOOD = "indian"
    return CURRENT_MOOD

def get_voice():
    """Returns the voice name for the current mood."""
    return VOICE_MOODS.get(CURRENT_MOOD, VOICE_MOODS["friendly"])

async def _speak_async(text):
    """Async function to generate speech using Edge TTS."""
    if edge_tts is None:
        print("Edge TTS is not installed; falling back to text output only.")
        return

    voice = get_voice()
    temp_file = os.path.join(tempfile.gettempdir(), "assistant_voice.mp3")
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(temp_file)
    
    if _ensure_mixer():
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    else:
        print(f"Generated speech audio at {temp_file}, but playback is unavailable.")

def speak(audio):
    """Converts text to natural-sounding speech using Edge TTS."""
    print(f"Assistant [{CURRENT_MOOD}]: {audio}")
    try:
        asyncio.run(_speak_async(audio))
    except Exception as e:
        print(f"Speech error: {e}")

def listen():
    """Listens for user input via microphone and returns recognized text."""
    if sr is None:
        try:
            return input("You: ").strip() or "None"
        except EOFError:
            return "None"

    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Listening...")
            r.pause_threshold = 1
            audio = r.listen(source)
    except Exception as e:
        print(f"Microphone unavailable: {e}")
        try:
            return input("You: ").strip() or "None"
        except EOFError:
            return "None"

    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-in')
        print(f"User said: {query}\n")
    except Exception as e:
        print("Say that again please...")
        return "None"
    return query

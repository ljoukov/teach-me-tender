import replicate
import requests
import os
import subprocess
import time
from dotenv import load_dotenv
import concurrent.futures
import threading

# --- Configuration ---
load_dotenv()
if not os.getenv("REPLICATE_API_TOKEN"):
    raise Exception("Replicate API token not found. Please set it in a .env file.")

VOICES = {"narrator": "Ember", "him": "Orion", "her": "Aurora"}
AUDIO_OUTPUT_DIR = "comic_audio"
TEMP_DIR = "temp_audio_parts"
THREAD_POOL_SIZE = 8
lock = threading.Lock()

# --- Retry Configuration for Network Errors ---
RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 2

# --- Full Comic Script (UPDATED) ---
# Parenthetical comments have been removed from the 'text' fields.
COMIC_SCRIPT = [
    # Frame 1
    [
        {
            "role": "narrator",
            "text": "For gifted software student Tedi, his York University classes were uninspiring. He needed a real-world puzzle.",
        }
    ],
    # Frame 2
    [{"role": "narrator", "text": "And then, he found one."}],
    # Frame 3
    [
        {
            "role": "her",
            "text": "It’s just noise. The dataset is all noise. How can anything this important be so... messy?",
        }
    ],
    # Frame 4
    [
        {
            "role": "him",
            "text": "Is this seat taken? All the other ones have... questionable stains.",
        },
        {
            "role": "her",
            "text": "Oh! No, it’s all yours. Welcome to the disaster zone.",
        },
    ],
    # Frame 5
    [
        {
            "role": "him",
            "text": "That model’s not resolving, is it? The folding prediction is failing.",
        },
        {"role": "her", "text": "You know what that is?"},
        {
            "role": "him",
            "text": "I know a computational bottleneck when I see one. What are you trying to map?",
        },
    ],
    # Frame 6
    [
        {
            "role": "her",
            "text": 'It’s called Apolipoprotein B-one-hundred. It wraps around the "bad cholesterol." It\'s the key that lets the body clear it from the blood. In my family... that key is broken.',
        }
    ],
    # Frame 7
    [
        {"role": "him", "text": "So, the problem is seeing how the key fits the lock."},
        {
            "role": "her",
            "text": "The problem is the key is huge and wobbly. Like a giant piece of wet spaghetti. No software can model it.",
        },
    ],
    # Frame 8
    [
        {
            "role": "narrator",
            "text": "The problem became their world. Days blurred into nights, fueled by cheap coffee and a shared, unspoken goal.",
        }
    ],
    # Frame 9
    [
        {
            "role": "him",
            "text": "It’s no good. The protein is just too big. We’re missing a logical shortcut.",
        },
        {"role": "her", "text": "Maybe... we’re thinking about it wrong."},
    ],
    # Frame 10
    [
        {
            "role": "her",
            "text": "Everyone thinks it's one big, dramatic connection. One site. One clamp. But what if it’s not? What if it’s more like... this.",
        }
    ],
    # Frame 11
    [
        {
            "role": "narrator",
            "text": "It wasn’t one strong connection. It was a hundred tiny, weak ones. Each link just barely holding on... but all of them, together, were strong.",
        }
    ],
    # Frame 12
    [
        {
            "role": "him",
            "text": "Tiny, weak connections... scattered along a line... The noise... it wasn't a bug.",
        }
    ],
    # Frame 13
    [
        {
            "role": "narrator",
            "text": "It was a feature. He realized they weren't modeling a single object, but a distributed system.",
        },
        {"role": "him", "text": "Not one handshake. A dozen, all at once!"},
    ],
    # Frame 14
    [
        {
            "role": "him",
            "text": "I can write this. An algorithm that doesn't look for one perfect fit, but for the most probable sum of many imperfect ones.",
        }
    ],
    # Frame 15
    [
        {
            "role": "narrator",
            "text": "He coded. She guided. Biology and computation, finally speaking the same language.",
        }
    ],
    # Frame 16
    [
        {
            "role": "him",
            "text": "Okay. I’m running it. This will either be the most beautiful thing we’ve ever seen, or it will melt the server.",
        },
        {"role": "her", "text": "Let’s find out."},
    ],
    # Frame 17
    [{"role": "narrator", "text": "The seconds stretched into an eternity."}],
    # Frame 18
    [{"role": "narrator", "text": "And then... clarity."}],
    # Frame 19
    [
        {
            "role": "narrator",
            "text": "There it was. The elegant, sweeping structure. Not a key, but a belt, fastened to its receptor by a dozen tiny clasps. It was perfect.",
        }
    ],
    # Frame 20
    [{"role": "her", "text": "Tedi... look. Right there."}],
    # Frame 21
    [
        {
            "role": "him",
            "text": "It’s at the interface. The known genetic mutations... they’re all clustering right at the connection points.",
        }
    ],
    # Frame 22
    [
        {
            "role": "narrator",
            "text": "It wasn’t just a model. It was an answer. A map to her family's pain, and a path toward healing.",
        }
    ],
    # Frame 23
    [
        {"role": "him", "text": "You were right. It wasn't one big lock and key."},
        {
            "role": "her",
            "text": "It was a chain. It needed someone who could see every single link.",
        },
    ],
    # Frame 24
    [
        {
            "role": "narrator",
            "text": "In the quiet hum of the lab, the solution to a global problem felt like a secret only they shared.",
        }
    ],
    # Frame 25
    [{"role": "her", "text": "Thank you."}],
    # Frame 26
    [
        {
            "role": "narrator",
            "text": "He didn't need to reply. Some things don't need words.",
        }
    ],
    # Frame 27
    [
        {
            "role": "narrator",
            "text": "A single point of warmth and light against the cold Toronto winter.",
        }
    ],
    # Frame 28
    [
        {
            "role": "narrator",
            "text": "Years later, the world would learn of the breakthrough.",
        }
    ],
    # Frame 29
    [
        {
            "role": "narrator",
            "text": "For Tedi, the discovery was always tied to a person, a place, and a simple, elegant chain.",
        }
    ],
    # Frame 30
    [
        {
            "role": "narrator",
            "text": "Some of the most important structures aren't made of proteins. They’re built in the quiet moments between two people, solving a puzzle that matters more than anything.",
        }
    ],
]


def safe_print(*args, **kwargs):
    """A thread-safe print function."""
    with lock:
        print(*args, **kwargs)


def generate_audio_with_retries(role, text):
    """Calls the Replicate API with a retry mechanism for network errors."""
    voice = VOICES.get(role)
    if not voice:
        raise ValueError(f"No voice defined for role: {role}")

    for attempt in range(RETRY_COUNT):
        try:
            output_url = replicate.run(
                "resemble-ai/chatterbox-pro",
                input={
                    "pitch": "medium",
                    "voice": voice,
                    "prompt": text,
                    "temperature": 0.8,
                    "exaggeration": 0.5,
                },
            )
            return output_url
        except Exception as e:
            if "timed out" in str(e).lower() and attempt < RETRY_COUNT - 1:
                delay = RETRY_DELAY_SECONDS * (2**attempt)
                safe_print(
                    f"   - Network timeout for role '{role}'. Retrying in {delay}s... ({attempt + 1}/{RETRY_COUNT})"
                )
                time.sleep(delay)
            else:
                safe_print(
                    f"   - Replicate API call failed permanently for role '{role}': {e}"
                )
                return None
    return None


def download_file(url, destination):
    """Downloads a file from a URL to a local path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        safe_print(f"   - Failed to download {url}: {e}")
        return False


def combine_audio_with_ffmpeg(input_files, output_file):
    """Combines multiple WAV files using ffmpeg and absolute paths."""
    list_filename = os.path.join(
        TEMP_DIR, f"concat_list_{os.path.basename(output_file)}.txt"
    )
    with open(list_filename, "w") as f:
        for filename in input_files:
            absolute_path = os.path.abspath(filename)
            safe_path = absolute_path.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_filename,
        "-c",
        "copy",
        "-y",
        output_file,
    ]

    safe_print(
        f"   - Combining {len(input_files)} parts into {os.path.basename(output_file)}..."
    )
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        safe_print(f"   - FFmpeg Error for {os.path.basename(output_file)}:")
        safe_print(f"   - STDERR: {e.stderr}")
        return False
    finally:
        if os.path.exists(list_filename):
            os.remove(list_filename)


def process_frame_audio(frame_script, index):
    """Worker function to process all audio for a single frame."""
    frame_number = index + 1
    safe_print(f"[Thread] Processing Frame {frame_number:02d}...")

    if not frame_script:
        safe_print(f"[Thread] Frame {frame_number:02d} has no script. Skipping.")
        return

    audio_parts = []
    for i, part in enumerate(frame_script):
        safe_print(
            f"   - Generating audio for frame {frame_number:02d}, part {i + 1} ('{part['role']}')"
        )
        url = generate_audio_with_retries(part["role"], part["text"])
        if url:
            audio_parts.append({"url": url, "index": i})
        else:
            safe_print(
                f"[ERROR] Could not generate required audio for frame {frame_number:02d}. Aborting this frame."
            )
            return

    final_output_path = os.path.join(
        AUDIO_OUTPUT_DIR, f"audio_frame_{frame_number:02d}.wav"
    )

    if len(audio_parts) == 1:
        if download_file(audio_parts[0]["url"], final_output_path):
            safe_print(f"[SUCCESS] Frame {frame_number:02d} audio saved.")
    else:
        temp_files = []
        try:
            for part in audio_parts:
                temp_path = os.path.join(
                    TEMP_DIR,
                    f"temp_frame_{frame_number:02d}_part_{part['index'] + 1}.wav",
                )
                if download_file(part["url"], temp_path):
                    temp_files.append(temp_path)
                else:
                    safe_print(
                        f"[ERROR] Failed to download temp file for frame {frame_number:02d}. Aborting combine."
                    )
                    return

            if len(temp_files) == len(audio_parts):
                if combine_audio_with_ffmpeg(temp_files, final_output_path):
                    safe_print(
                        f"[SUCCESS] Frame {frame_number:02d} audio combined and saved."
                    )
        finally:
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)


def main():
    """Main function to orchestrate the audio generation process."""
    print("--- Starting Final Comic Audio Generation ---")
    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"Audio will be saved to: '{AUDIO_OUTPUT_DIR}'")

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=THREAD_POOL_SIZE
    ) as executor:
        futures = [
            executor.submit(process_frame_audio, script, i)
            for i, script in enumerate(COMIC_SCRIPT)
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                safe_print(f"[FATAL ERROR] A thread raised an unhandled exception: {e}")

    print("\n--- Comic Audio Generation Finished ---")


if __name__ == "__main__":
    main()

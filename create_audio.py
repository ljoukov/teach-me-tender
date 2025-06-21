import replicate
import requests
import os
import subprocess
import time
from dotenv import load_dotenv
import concurrent.futures

# --- Configuration ---

# Load environment variables from .env file (for REPLICATE_API_TOKEN)
load_dotenv()

# Check if the API token is available
if not os.getenv("REPLICATE_API_TOKEN"):
    raise Exception("Replicate API token not found. Please set it in a .env file.")

# Voice mapping for each character role
VOICES = {
    "narrator": "Ember",  # Deep, classic narrator voice
    "him": "Orion",  # Tedi's voice
    "her": "Aurora",  # Her voice
}

# Output directories
AUDIO_OUTPUT_DIR = "comic_audio"
TEMP_DIR = "temp_audio_parts"
THREAD_POOL_SIZE = 8  # Use a thread pool for parallel API calls

# --- Full Comic Script ---
# A list of lists. Each inner list represents a frame and contains
# dicts for each piece of audio ('role' and 'text').

COMIC_SCRIPT = [
    # Frame 1
    [
        {
            "role": "narrator",
            "text": "York University, Toronto. 2015. For Tedi, most of a software engineering degree was learning systems that felt too simple. The real puzzles weren't in the classroom.",
        }
    ],
    # Frame 2
    [{"role": "narrator", "text": "And then, he found one."}],
    # Frame 3
    [
        {
            "role": "her",
            "text": "(Muttering to herself) It’s just noise. The dataset is all noise. How can anything this important be so... messy?",
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
            "text": "(A little startled) Oh! No, it’s all yours. Welcome to the disaster zone.",
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
            "text": "(Frustrated sigh) It’s no good. The protein is just too big. We’re missing a logical shortcut.",
        },
        {"role": "her", "text": "(Quietly) Maybe... we’re thinking about it wrong."},
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
            "text": "(A sudden insight) Tiny, weak connections... scattered along a line... The noise... it wasn't a bug.",
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
        {"role": "her", "text": "(A nervous smile in her voice) Let’s find out."},
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
    [
        {
            "role": "her",
            "text": "(In awe, voice trembling slightly) Tedi... look. Right there.",
        }
    ],
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
    [{"role": "her", "text": "(Softly) Thank you."}],
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
            "text": "But for Tedi, the discovery was always tied to a person, a place, and a simple, elegant chain.",
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


def generate_audio_part(role, text):
    """Calls the Replicate API to generate a single audio clip."""
    voice = VOICES.get(role)
    if not voice:
        raise ValueError(f"No voice defined for role: {role}")

    print(f"   - Generating audio for role '{role}' with voice '{voice}'...")
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
        print(f"   - Replicate API call failed for role '{role}': {e}")
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
        print(f"   - Failed to download {url}: {e}")
        return False


def combine_audio_with_ffmpeg(input_files, output_file):
    """Combines multiple WAV files into one using ffmpeg's concat demuxer."""
    # Create a temporary file list for ffmpeg
    list_filename = os.path.join(TEMP_DIR, f"concat_list_{int(time.time() * 1000)}.txt")
    with open(list_filename, "w") as f:
        for filename in input_files:
            # Ffmpeg requires forward slashes and escaped special characters
            safe_path = filename.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    # Construct and run the ffmpeg command
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
        "-y",  # Overwrite output file if it exists
        output_file,
    ]

    print(
        f"   - Combining {len(input_files)} parts into {os.path.basename(output_file)}..."
    )
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        # Clean up the temporary list file
        os.remove(list_filename)
        return True
    except subprocess.CalledProcessError as e:
        print(f"   - FFmpeg Error for {os.path.basename(output_file)}:")
        print(f"   - STDOUT: {e.stdout}")
        print(f"   - STDERR: {e.stderr}")
        os.remove(list_filename)
        return False


def process_frame_audio(frame_script, index):
    """Worker function to process all audio for a single frame."""
    frame_number = index + 1
    print(f"[Thread] Processing Frame {frame_number:02d}...")

    final_output_path = os.path.join(
        AUDIO_OUTPUT_DIR, f"audio_frame_{frame_number:02d}.wav"
    )

    if not frame_script:
        print(f"[Thread] Frame {frame_number:02d} has no script. Skipping.")
        return

    # Generate all audio parts for the frame
    part_urls = []
    for i, part in enumerate(frame_script):
        url = generate_audio_part(part["role"], part["text"])
        if url:
            part_urls.append((url, i))
        else:
            print(
                f"[Error] Could not generate audio for frame {frame_number:02d}, part {i + 1}."
            )
            return  # Abort processing for this frame if a part fails

    # Handle downloading and combining
    if len(part_urls) == 1:
        # Single audio clip, just download it directly
        url, _ = part_urls[0]
        if download_file(url, final_output_path):
            print(f"[Thread] Frame {frame_number:02d} audio saved successfully.")
    elif len(part_urls) > 1:
        # Multiple clips, download to temp and combine
        temp_files = []
        for url, i in part_urls:
            temp_path = os.path.join(
                TEMP_DIR, f"temp_frame_{frame_number:02d}_part_{i + 1}.wav"
            )
            if download_file(url, temp_path):
                temp_files.append(temp_path)
            else:
                print(
                    f"[Error] Failed to download temp file for frame {frame_number:02d}."
                )
                return  # Abort if download fails

        if len(temp_files) == len(part_urls):
            if combine_audio_with_ffmpeg(temp_files, final_output_path):
                print(
                    f"[Thread] Frame {frame_number:02d} audio combined and saved successfully."
                )
            # Clean up temporary part files
            for temp_file in temp_files:
                os.remove(temp_file)


def main():
    """Main function to orchestrate the audio generation process."""
    print("--- Starting Comic Audio Generation ---")

    # Create output directories if they don't exist
    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"Audio will be saved to: '{AUDIO_OUTPUT_DIR}'")
    print(f"Temporary files will use: '{TEMP_DIR}'")

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=THREAD_POOL_SIZE
    ) as executor:
        # Submit all frames to be processed in parallel
        futures = [
            executor.submit(process_frame_audio, script, i)
            for i, script in enumerate(COMIC_SCRIPT)
        ]

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"[Error] A thread raised an exception: {e}")

    print("\n--- Comic Audio Generation Finished ---")


if __name__ == "__main__":
    main()

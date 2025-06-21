import replicate

if False:
    # Input images:
    # Him (only): https://pixtoon-media.eviworld.com/teach-me-tender/teri.jpeg
    # Her (only): https://pixtoon-media.eviworld.com/teach-me-tender/her.jpeg
    # Both: https://pixtoon-media.eviworld.com/teach-me-tender/both.jpeg
    output_url = replicate.run(
        "black-forest-labs/flux-kontext-pro",
        input={
            "prompt": "Make them outside in a snowy Toronto wearing winter clothes, both smiling and happy, his speech bubble says 'Let's go!'",
            "input_image": "https://pixtoon-media.eviworld.com/teach-me-tender/both.jpeg",
            "aspect_ratio": "match_input_image",
            "output_format": "jpg",
            "safety_tolerance": 6,
        },
    )
    print(output_url)

# Voice:
# Teri: "voice": "Orion"
# Her: "voice": "Aurora"
# Narrator: "voice": "Ember"
output_wav_file_url = replicate.run(
    "resemble-ai/chatterbox-pro",
    input={
        "pitch": "medium",
        "voice": "Orion",
        "prompt": "hello!",
        "temperature": 0.8,
        "exaggeration": 0.5,
    },
)
print(output_wav_file_url)

import replicate
import requests
import os
import concurrent.futures


# Base images for the characters
# The model will use these as a starting point to generate the scenes.
IMAGE_URLS = {
    "him": "https://pixtoon-media.eviworld.com/teach-me-tender/teri.jpeg",
    "her": "https://pixtoon-media.eviworld.com/teach-me-tender/her.jpeg",
    "both": "https://pixtoon-media.eviworld.com/teach-me-tender/both.jpeg",
}

# Output directory for the comic frames
OUTPUT_DIR = "comic_frames"
# Number of parallel threads for API calls
THREAD_POOL_SIZE = 8

# --- Prompts for the Comic Book Story ---
# Each dictionary contains the prompt text and the key for the base image to use.
# These prompts are derived from the 30-panel story script.

COMIC_PROMPTS = [
    # Frame 1-5: The Meeting
    {
        "prompt": "Place him in the back row of a large, modern university lecture hall. He looks bored, his laptop is open with lines of code on screen. Winter is visible outside the windows. Cinematic comic book art style, high detail.",
        "image_key": "him",
    },
    {
        "prompt": "Place her at a cluttered carrel in a vast university library, surrounded by thick biochemistry textbooks. She looks intensely focused and frustrated. Cinematic, warm lighting from a desk lamp.",
        "image_key": "her",
    },
    {
        "prompt": "A close-up on her notes, which are covered in complex molecular diagrams. The title 'Familial Hypercholesterolemia' is circled in red. She is muttering to herself in frustration. Style: Detailed comic book art.",
        "image_key": "her",
    },
    {
        "prompt": "Place them at a library table. He has just approached her and is gesturing to an empty chair, a slight smile on his face. She looks up from her books, startled but with a weary smile. Style: Cinematic comic book art.",
        "image_key": "both",
    },
    {
        "prompt": "Place them sharing a table. He is coding on his laptop while she stares at a chaotic 3D protein model on her own screen. He glances over, looking curious about her work. Style: Realistic comic book art.",
        "image_key": "both",
    },
    # Frame 6-10: The Problem
    {
        "prompt": "Place them in a cozy campus coffee shop booth, steam fogging the window. She is passionately explaining her research, using her hands to describe shapes. He is leaning forward, listening intently. Cinematic style.",
        "image_key": "both",
    },
    {
        "prompt": "Make him the central focus. He is completely engaged, his expression shifting from academic curiosity to deep empathy as she explains her family's medical history. Coffee shop background. High detail comic style.",
        "image_key": "him",
    },
    {
        "prompt": "Place them in a glowing computer lab late at night. A whiteboard behind them is covered in his algorithms and her biological diagrams. They are surrounded by empty pizza boxes and coffee cups, working together. Cinematic comic style.",
        "image_key": "both",
    },
    {
        "prompt": "Place them in the same computer lab. He looks frustrated, running a hand through his hair, staring at a failed simulation on the monitor. She looks on, looking tired but thoughtful. High-contrast lighting from the screen.",
        "image_key": "both",
    },
    {
        "prompt": "A close-up shot focused on her hands. She is unconsciously fidgeting with a delicate, multi-linked silver chain bracelet on her wrist. The background is the soft glow of the lab. Detailed and poignant comic art style.",
        "image_key": "her",
    },
    # Frame 11-15: The Breakthrough
    {
        "prompt": "A highly conceptual shot. Show her delicate silver bracelet draped over the spine of a thick textbook, perfectly tracing its curve. The lighting is dramatic and focused, highlighting the chain. Style: Symbolic comic art.",
        "image_key": "her",
    },
    {
        "prompt": "His eyes are wide with a sudden realization, staring at the bracelet. A 'lightbulb' moment. The background is a blur of the computer lab. Focus on his expressive face. Cinematic comic book style.",
        "image_key": "him",
    },
    {
        "prompt": "Show him turning to a clean whiteboard and sketching frantically. He's drawing not a single object, but a series of connected nodes and flexible paths. She watches him, a glimmer of hope in her eyes. Dynamic comic style.",
        "image_key": "both",
    },
    {
        "prompt": "Intense close-up on him at his keyboard, fingers flying. His face is a mask of pure focus, illuminated by the code on his screen. A reflection of her hopeful face is barely visible in the dark monitor. High-contrast, cinematic lighting.",
        "image_key": "him",
    },
    {
        "prompt": "A time-lapse style image. Show them working in perfect sync, him coding, her pointing to data on a secondary monitor. The sun rises outside the window behind them. Style: Dynamic comic panel.",
        "image_key": "both",
    },
    # Frame 16-20: The Result
    {
        "prompt": "Show them huddled closely together in front of the monitor. His hand is hovering over the 'Enter' key. They both look nervous and hopeful. The scene is lit only by the screen. Tense, cinematic comic style.",
        "image_key": "both",
    },
    {
        "prompt": "The monitor is the focus. A progress bar is at 100%. They are watching it, holding their breath, their faces reflected dimly on the screen. High-detail comic style.",
        "image_key": "both",
    },
    {
        "prompt": "Make the screen the hero of the image. It displays a beautiful, elegant, and clear 3D structure of the ApoB100 protein. Their faces, seen from behind the monitor, are filled with awe and wonder. Glowing, cinematic style.",
        "image_key": "both",
    },
    {
        "prompt": "An emotional close-up on her face. A single tear of joy and relief is rolling down her cheek as she stares at the screen. The blue light from the monitor illuminates her features. Poignant comic book art.",
        "image_key": "her",
    },
    {
        "prompt": "Show her finger pointing to a specific spot on the glowing screen's protein model. He is looking at where she's pointing, his expression one of dawning comprehension. Detailed, focused comic style.",
        "image_key": "both",
    },
    # Frame 21-25: The Connection
    {
        "prompt": "Focus on the screen, showing the 3D model with a label pointing to a mutation cluster at the binding interface. The text 'Known Mutation Cluster: Familial Hypercholesterolemia' is visible. Style: Informative comic panel.",
        "image_key": "both",
    },
    {
        "prompt": "They are sitting in silence, staring at the screen. The weight of their discovery fills the room. The lab around them is dark, with only the monitor illuminating their stunned faces. Atmospheric comic art.",
        "image_key": "both",
    },
    {
        "prompt": "He turns to look at her, his expression soft and full of admiration. The blue light from the screen highlights her profile as she looks back at him, her eyes shining. Intimate, close-up shot. Romantic comic style.",
        "image_key": "both",
    },
    {
        "prompt": "An intimate, quiet shot. Their shoulders are almost touching, their hands resting near each other on the desk. The chaotic lab around them is out of focus. The mood is one of deep connection. Style: Soft, romantic comic art.",
        "image_key": "both",
    },
    {
        "prompt": "Show her leaning her head gently on his shoulder, a gesture of trust and shared exhaustion. They are both still looking at the screen, which illuminates them. Warm, intimate comic book style.",
        "image_key": "both",
    },
    # Frame 26-30: The Aftermath
    {
        "prompt": "He has his arm around her. They are sitting together, bathed in the glow of their shared creation. A peaceful and triumphant moment. Cinematic, romantic comic style.",
        "image_key": "both",
    },
    {
        "prompt": "A shot from outside the lab window, looking in. Snow is falling softly outside. Inside, their two silhouettes are visible, close together in front of the single glowing monitor. A point of warmth in the cold night.",
        "image_key": "both",
    },
    {
        "prompt": "A close-up of a hand holding a modern smartphone. The screen displays a news article with the headline: 'NIH research reveals new insights about how “bad” cholesterol works...'. Style: Modern, clean comic art.",
        "image_key": "him",
    },
    {
        "prompt": "Show him, now looking slightly older and more professional, in a sleek, modern office. He is smiling down at the phone in his hand. On his wrist, he wears a simple, multi-linked silver bracelet. Style: Polished, modern comic art.",
        "image_key": "him",
    },
    {
        "prompt": "A final, conceptual image. A glowing, stylized human heart made from the intertwined 3D protein structures from their discovery. Inside the heart, show the tiny, silhouetted figures of both of them standing together. Metaphorical, beautiful comic art.",
        "image_key": "both",
    },
]


def generate_and_save_image(prompt_data, index, image_urls, output_dir):
    """
    Worker function to be run in a thread.
    Calls the Replicate API and saves the resulting image.
    """
    prompt_text = prompt_data["prompt"]
    image_key = prompt_data["image_key"]
    input_image_url = image_urls[image_key]

    frame_number = index + 1
    output_filename = os.path.join(output_dir, f"frame_{frame_number:02d}.jpg")

    print(f"[Thread] Starting generation for frame {frame_number}...")

    try:
        # Call the Replicate API
        output_url = replicate.run(
            "black-forest-labs/flux-kontext-pro",
            input={
                "prompt": prompt_text + " Make the characters be generally happy",
                "input_image": input_image_url,
                "aspect_ratio": "match_input_image",  # Maintain aspect ratio of base image
                "output_format": "jpg",
                "safety_tolerance": 6,  # Slightly more lenient for artistic styles
                # "prompt_strength": 8.5,  # How much to change the original image
            },
        )

        print(f"[Thread] Frame {frame_number} generated. URL: {output_url}")

        # Download the image from the returned URL
        response = requests.get(output_url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        with open(output_filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"[Thread] Frame {frame_number} saved successfully as {output_filename}")
        return True

    except Exception as e:
        print(f"[Error] Failed to generate or save frame {frame_number}: {e}")
        return False


def create_comic_story(prompts, image_urls, output_dir):
    """
    Main function to orchestrate the comic generation process.
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory '{output_dir}' is ready.")

    # Use a ThreadPoolExecutor to run API calls in parallel
    print(f"Starting comic generation with a thread pool of size {THREAD_POOL_SIZE}...")

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=THREAD_POOL_SIZE
    ) as executor:
        # Create a future for each prompt
        future_to_prompt = {
            executor.submit(
                generate_and_save_image, prompt_data, i, image_urls, output_dir
            ): i
            for i, prompt_data in enumerate(prompts)
        }

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(future_to_prompt):
            index = future_to_prompt[future]
            try:
                future.result()  # You can check the return value here if needed
            except Exception as e:
                print(f"[Main] Frame {index + 1} generated an exception: {e}")

    print("\nComic generation process finished.")


if __name__ == "__main__":
    # create_comic_story(COMIC_PROMPTS, IMAGE_URLS, OUTPUT_DIR)

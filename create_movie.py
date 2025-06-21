import os
import subprocess
import glob
import json
import random
import shutil

# --- Configuration ---
FRAMES_DIR = "comic_frames"
AUDIO_DIR = "comic_audio"
TEMP_VIDEO_DIR = "temp_video_segments"
OUTPUT_FILENAME = "comic_slideshow.mp4"

# Video settings
RESOLUTION = "1024x1024"
FRAME_RATE = 30
TRANSITION_DURATION = 1  # in seconds

# A list of cool ffmpeg xfade transitions.
# See more here: https://ffmpeg.org/ffmpeg-filters.html#xfade
TRANSITIONS = [
    "fade",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "slideup",
    "slidedown",
    "circlecrop",
    "rectcrop",
    "distance",
    "fadegrays",
    "radial",
    "diagtl",
    "diagtr",
    "diagbl",
    "diagbr",
    "dissolve",
]


def check_ffmpeg():
    """Checks if ffmpeg is installed and available in the system's PATH."""
    print("Checking for ffmpeg executable...")
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        print("✅ ffmpeg found.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ERROR: ffmpeg not found.")
        print("Please install ffmpeg and ensure it is in your system's PATH.")
        return False


def get_audio_duration(audio_path):
    """Gets the duration of an audio file using ffprobe."""
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        audio_path,
    ]
    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        print(f"Error getting duration for {audio_path}: {result.stderr}")
        return None

    info = json.loads(result.stdout)
    # Check format duration first, fallback to stream duration
    if "format" in info and "duration" in info["format"]:
        return float(info["format"]["duration"])
    elif "streams" in info and info["streams"] and "duration" in info["streams"][0]:
        return float(info["streams"][0]["duration"])
    else:
        print(f"Could not determine duration for {audio_path}")
        return None


def create_video_segments(image_files, audio_files):
    """Creates individual video clips for each frame-audio pair."""
    print(f"\n--- Step 1: Creating {len(image_files)} individual video segments ---")
    os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)

    segment_paths = []
    for i, (img_path, audio_path) in enumerate(zip(image_files, audio_files)):
        segment_num = i + 1
        output_path = os.path.join(TEMP_VIDEO_DIR, f"segment_{segment_num:02d}.mp4")
        segment_paths.append(output_path)

        duration = get_audio_duration(audio_path)
        if duration is None:
            print(f"Skipping segment {segment_num} due to missing duration.")
            continue

        print(
            f"Creating segment {segment_num}/{len(image_files)} (Duration: {duration:.2f}s)..."
        )

        command = [
            "ffmpeg",
            "-loop",
            "1",  # Loop the input image
            "-i",
            img_path,  # Input image
            "-i",
            audio_path,  # Input audio
            "-c:v",
            "libx264",  # Video codec
            "-tune",
            "stillimage",  # Optimize for static images
            "-c:a",
            "aac",  # Audio codec
            "-b:a",
            "192k",  # Audio bitrate
            "-pix_fmt",
            "yuv420p",  # Pixel format for compatibility
            "-s",
            RESOLUTION,  # Set video size
            "-r",
            str(FRAME_RATE),  # Set frame rate
            "-t",
            str(duration),  # Set duration of the clip
            "-y",  # Overwrite output file if it exists
            output_path,
        ]

        # Run the command, hide output unless there's an error
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"❌ Error creating segment {segment_num}:")
            print(result.stderr.decode())

    print("✅ All video segments created.")
    return segment_paths


def create_final_video(segment_paths):
    """Combines all video segments with transitions into a final movie."""
    print("\n--- Step 2: Combining segments with transitions ---")
    if not segment_paths:
        print("No segments to combine. Aborting.")
        return

    # --- Build the complex ffmpeg command ---
    command = ["ffmpeg"]

    # 1. Add all segments as inputs
    for seg_path in segment_paths:
        command.extend(["-i", seg_path])

    # 2. Build the filter_complex string
    filter_complex = []
    num_segments = len(segment_paths)

    # Video chain
    prev_video_stream = "[0:v]"
    for i in range(1, num_segments):
        transition = random.choice(TRANSITIONS)
        current_video_stream = f"[{i}:v]"
        output_stream = f"[v{i}]"

        # Calculate the start time of the transition
        offset_command = f"xfade=transition={transition}:duration={TRANSITION_DURATION}"

        filter_complex.append(
            f"{prev_video_stream}{current_video_stream}{offset_command}{output_stream}"
        )
        prev_video_stream = output_stream

    # Audio chain
    audio_streams = "".join([f"[{i}:a]" for i in range(num_segments)])
    audio_concat = f"{audio_streams}concat=n={num_segments}:v=0:a=1[outa]"
    filter_complex.append(audio_concat)

    command.extend(["-filter_complex", ";".join(filter_complex)])

    # 3. Map the final output streams
    command.extend(["-map", prev_video_stream, "-map", "[outa]"])

    # 4. Add final output settings
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", OUTPUT_FILENAME])

    print("Executing final render command. This may take a while...")
    # Uncomment the line below to see the full ffmpeg command being executed
    # print(" ".join(command))

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        print(f"✅ Final video successfully created: {OUTPUT_FILENAME}")
    else:
        print("❌ Error during final video rendering:")
        print(result.stderr.decode())


def cleanup():
    """Removes the temporary directory."""
    print("\n--- Step 3: Cleaning up temporary files ---")
    if os.path.exists(TEMP_VIDEO_DIR):
        shutil.rmtree(TEMP_VIDEO_DIR)
        print(f"Removed temporary directory: {TEMP_VIDEO_DIR}")


def main():
    """Main function to orchestrate the video creation process."""
    if not check_ffmpeg():
        return

    # Validate input directories
    if not os.path.isdir(FRAMES_DIR) or not os.path.isdir(AUDIO_DIR):
        print(
            f"Error: Input directories '{FRAMES_DIR}' and/or '{AUDIO_DIR}' not found."
        )
        return

    image_files = sorted(glob.glob(os.path.join(FRAMES_DIR, "*.jpg")))
    audio_files = sorted(glob.glob(os.path.join(AUDIO_DIR, "*.wav")))

    if not image_files or not audio_files or len(image_files) != len(audio_files):
        print(
            "Error: Mismatch in number of image and audio files, or folders are empty."
        )
        print(f"Found {len(image_files)} images and {len(audio_files)} audio files.")
        return

    # --- Run the process ---
    video_segments = create_video_segments(image_files, audio_files)

    if video_segments:
        create_final_video(video_segments)

    cleanup()


if __name__ == "__main__":
    main()

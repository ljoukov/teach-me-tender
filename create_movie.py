import os
import subprocess
import glob
import json
import shutil

# --- Configuration ---
FRAMES_DIR = "comic_frames"
AUDIO_DIR = "comic_audio"
TEMP_VIDEO_DIR = "temp_video_segments"
OUTPUT_FILENAME = "comic_slideshow_final.mp4"  # New name to avoid confusion

# Video settings for each segment
RESOLUTION = "1024x1024"
FRAME_RATE = 30


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
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        info = json.loads(result.stdout)
        if "format" in info and "duration" in info["format"]:
            return float(info["format"]["duration"])
        print(
            f"Warning: Could not determine duration from format for {audio_path}. Trying streams."
        )
        if "streams" in info and info["streams"] and "duration" in info["streams"][0]:
            return float(info["streams"][0]["duration"])
        print(f"Error: Could not determine duration for {audio_path}")
        return None
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error getting duration for {audio_path}: {e}")
        return None


def create_video_segments(image_files, audio_files):
    """Creates individual video clips for each frame-audio pair. This part remains the same."""
    print(f"\n--- Step 1: Creating {len(image_files)} individual video segments ---")
    os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)

    segment_paths = []
    for i, (img_path, audio_path) in enumerate(zip(image_files, audio_files)):
        segment_num = i + 1
        output_path = os.path.join(TEMP_VIDEO_DIR, f"segment_{segment_num:02d}.mp4")

        duration = get_audio_duration(audio_path)
        # Add a small buffer to prevent audio from being cut off early
        if duration is None:
            print(f"Skipping segment {segment_num} due to missing audio duration.")
            continue

        duration += 0.1  # Add 100ms buffer

        print(
            f"Creating segment {segment_num}/{len(image_files)} for {os.path.basename(img_path)} (Duration: {duration:.2f}s)..."
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
            "yuv420p",  # Pixel format for broad compatibility
            "-s",
            RESOLUTION,  # Set video size
            "-r",
            str(FRAME_RATE),  # Set frame rate
            "-shortest",  # Finish encoding when the shortest stream ends (the audio)
            "-t",
            str(duration),  # Explicitly set duration as a fallback
            "-y",  # Overwrite output file
            output_path,
        ]

        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0:
            print(f"❌ Error creating segment {segment_num}:\n{result.stderr.decode()}")
        else:
            segment_paths.append(output_path)

    print("✅ All video segments created.")
    return segment_paths


def create_final_video_simple(segment_paths):
    """
    Combines all video segments using the reliable `concat` filter (hard cuts).
    This function replaces the complex transition logic.
    """
    print("\n--- Step 2: Combining segments with hard cuts (concat filter) ---")
    if not segment_paths:
        print("No valid segments were created. Aborting final video creation.")
        return

    # Create a text file listing all the segment files for ffmpeg's concat demuxer.
    # This is the most robust method for concatenation.
    list_file_path = os.path.join(TEMP_VIDEO_DIR, "concat_list.txt")
    with open(list_file_path, "w") as f:
        for path in segment_paths:
            # Ffmpeg requires forward slashes and escaped special characters
            safe_path = os.path.abspath(path).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_file_path,
        "-c",
        "copy",  # Copy streams without re-encoding, it's fast and preserves quality
        "-y",
        OUTPUT_FILENAME,
    ]

    print("Executing final render command...")
    # print(" ".join(command)) # Uncomment to see the full command

    result = subprocess.run(command, capture_output=True)
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

    if not os.path.isdir(FRAMES_DIR) or not os.path.isdir(AUDIO_DIR):
        print(
            f"Error: Input directories '{FRAMES_DIR}' and/or '{AUDIO_DIR}' not found."
        )
        return

    image_files = sorted(glob.glob(os.path.join(FRAMES_DIR, "*.jpg")))
    audio_files = sorted(glob.glob(os.path.join(AUDIO_DIR, "*.wav")))

    if not image_files or len(image_files) != len(audio_files):
        print(
            "Error: Mismatch in number of image and audio files, or folders are empty."
        )
        return

    video_segments = create_video_segments(image_files, audio_files)
    create_final_video_simple(video_segments)
    cleanup()


if __name__ == "__main__":
    main()

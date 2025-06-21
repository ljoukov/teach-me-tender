import replicate

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

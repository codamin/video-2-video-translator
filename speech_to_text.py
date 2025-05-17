from faster_whisper import WhisperModel

def speech_to_text(audio_file_path):
    """
    Transcribe audio to text using the Whisper model.
    :param audio_file_path: Path to the audio file (WAV format).
    :return: Transcribed text.
    """

    # 1. Define the model size you want to use
    #    Options include: "tiny", "tiny.en", "base", "base.en", "small", "small.en",
    #                     "medium", "medium.en", "large-v1", "large-v2", "large-v3",
    #                     "distil-large-v2", "distil-medium.en", "distil-small.en"
    model_size = "base.en"  # Using a smaller English-specific model for quicker testing

    # 2. Specify your device ("cuda" for GPU, "cpu" for CPU) and compute type
    #    Compute types can be "float16", "int8_float16", "int8" etc., depending on your hardware
    #    and desired speed/accuracy trade-off. "float16" is common for GPUs.
    #    For CPU, you might use "int8" or "float32".
    device = "cpu" # or "cuda" if you have a compatible GPU and CUDA installed
    compute_type = "int8" # or "float16" for GPU

    # 3. Load the model
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"Model '{model_size}' loaded successfully on {device} with compute type {compute_type}.")
    except Exception as e:
        print(f"Error loading model: {e}")
        exit()

    # 4. Specify the path to your .wav file
    audio_file_path = 'resources/sepideh_voice_test.mp3' # Make sure this file exists

    # 5. Transcribe the audio file
    print(f"Transcribing {audio_file_path}...")
    try:
        # The transcribe method takes the audio file path directly
        segments, info = model.transcribe(audio_file_path, beam_size=5)

        # segments is an iterator yielding named tuples with start, end, and text
        # info contains detected language and probability

        print(f"\nDetected language: {info.language} (Probability: {info.language_probability:.2f})")
        print("Transcription:")
        full_transcript = []
        for segment in segments:
            print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
            full_transcript.append(segment.text.strip())

        print("\nFull Transcript:")
        print(" ".join(full_transcript))
        return " ".join(full_transcript)

    except FileNotFoundError:
        print(f"Error: The audio file '{audio_file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        
    return None
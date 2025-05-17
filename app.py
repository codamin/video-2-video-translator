import os
import gradio as gr
from speech_to_text import speech_to_text
from text_to_speech import text_to_speech
from llm import translate_text_to_text
from lipsync import lipsync

# Initialize pipelines (you might need to download models on first run)
# speech_to_text_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-small")
# llm_pipeline = pipeline("text-generation", model="gpt2-medium") # You might want a more instruction-following model
# text_to_speech_pipeline = pipeline("text-to-speech", model="facebook/fastspeech2-en-200_speaker0")



import subprocess

COMMAND = "ffmpeg -i {video_path} -ab 160k -ac 2 -ar 44100 -vn audio/audio.wav"


language_map = {
    "fr": "French",
    "en": "English",
    "es": "Spanish",
    "de": "German",
}

def process_video(video_input):
    print("######", video_input)
    """Process the video to extract audio, transcribe it, generate text, and create speech."""
    subprocess.call(COMMAND.format(video_path=video_input), shell=True)
    #  source_speaker_file = "/Users/mdrpanwar/Downloads/test3.m4a" # en francias
    src_lang = "en" # detect language TODO
    tgt_lang = "fr" # TODO
    target_language = "FR"  # Spanish
    
    
    # extract audio from video
    src_text = speech_to_text("audio/audio.wav", src_language=src_lang)
    tgt_text = translate_text_to_text(src_text, language_map[src_lang], language_map[tgt_lang])
    # text = "Hello, my name is cat and I am a dog" 
    output_speech = text_to_speech(tgt_text, "audio/audio.wav", language=target_language) # takes text, and says t in provided voice
    
    video_outpath = lipsync(video_path=video_input, audio_path=output_speech)
    # output_video = lip_sync(output_speech, source_speaker_file)
    
    os.remove("audio/audio.wav")  # Clean up the temporary audio file
    return video_outpath
   
if __name__ == "__main__":
    iface = gr.Interface(
        fn=process_video,
        inputs=gr.Video(label="Input Video"),
        outputs=[
            gr.Video(label="Lipsynced Translated Video"),
            # gr.Audio(label="Generated Audio"),
            # gr.Textbox(label="Generated Text (from Speech to Text)"),
            # gr.Textbox(label="LLM Output"),
        ],
        live=False,
        title="Video Processing Pipeline",
        description="Upload a video to transcribe its audio, process the text with an LLM, generate speech from the LLM output, and (conceptually) lipsync it back to the original video.",
    )
    
   
    iface.launch(server_port=8000) # Specify the desired port here

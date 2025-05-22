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
    "zh": "Chinese",
    "jp": "Japanese",
}

def process_video(video_input):
    print("######", video_input)
    os.system(f"cp {video_input} video.mp4")
    
    """Process the video to extract audio, transcribe it, generate text, and create speech."""
    subprocess.call(COMMAND.format(video_path=video_input), shell=True)
    #  source_speaker_file = "/Users/mdrpanwar/Downloads/test3.m4a" # en francias
    src_lang = "fr" # detect language TODO
    tgt_lang = "en" # TODO

    # src_lang = "fr"
    # tgt_lang = "en"
    target_language = "EN_NEWEST"  # Spanish
    
    
    # extract audio from video
    src_text = speech_to_text("audio/audio.wav", src_language=src_lang)
    tgt_text = translate_text_to_text(src_text, language_map[src_lang], language_map[tgt_lang])
    print("Translated Text:", tgt_text)
    # text = "Hello, my name is cat and I am a dog" 
    # tgt_tecxt = "Voici la derni_re fois que nous allons enregistrer, veuillez fonctionner car nous allons pr_senter maintenant."
    output_speech = text_to_speech(tgt_text, "audio/audio.wav", language=target_language) # takes text, and says t in provided voice
    
    video_outpath = lipsync(video_path="/mnt/u14157_ic_nlp_001_files_nfs/nlpdata1/home/bkhmsi/vid2vid-translator/video-2-video-translator/video.mp4", audio_path=output_speech)
    # output_video = lip_sync(output_speech, source_speaker_file)
    
    os.remove("audio/audio.wav")  # Clean up the temporary audio file
    return "/mnt/u14157_ic_nlp_001_files_nfs/nlpdata1/home/bkhmsi/vid2vid-translator/video-2-video-translator/results/v15/avatars/avatar_001/vid_output/output.mp4"
   
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
    
   
    iface.launch(server_name="0.0.0.0", server_port=64286) # Specify the desired port here

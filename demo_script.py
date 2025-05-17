from speech_to_text import speech_to_text
from text_to_speech import text_to_speech
from llm import translate_text_to_text

if __name__ == "__main__":
    # Example usage
    source_speaker_file = "/Users/mdrpanwar/Downloads/test3.m4a" # en francias
    src_lang = "fr"
    target_language = "EN_NEWEST"  # Spanish
    
    
    # extract audio from video
    src_text = speech_to_text(source_speaker_file, src_language=src_lang)
    tgt_text = translate_text_to_text(src_text, "French", "English")
    # text = "Hello, my name is cat and I am a dog" 
    output_speech = text_to_speech(tgt_text, source_speaker_file) # takes text, and says t in provided voice
    # output_video = lip_sync(output_speech, source_speaker_file)
    

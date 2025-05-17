from speech_to_text import speech_to_text
from text_to_speech import text_to_speech

if __name__ == "__main__":
    # Example usage
    source_speaker_file = "sepideh_voice_test.mp3" 
    target_language = "es"  # Spanish
    
    # extract audio from video
    text = speech_to_text(f"resources/{source_speaker_file}")
    # translated_text = llm_translate(text, "en", target_language)  
    output_speech = text_to_speech(text, source_speaker_file)
    # output_video = lip_sync(output_speech, source_speaker_file)
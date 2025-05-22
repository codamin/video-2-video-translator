import os
import torch
from melo.api import TTS

import sys
import sys
sys.path.append("OpenVoice")
from openvoice import se_extractor
from openvoice.api import ToneColorConverter

ckpt_converter = 'checkpoints_v2/converter'
device = "cuda:0" if torch.cuda.is_available() else "cpu"
# device = "cpu"
output_dir = 'outputs_v2'

tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')

def text_to_speech(text, source_speaker_file, language="EN_NEWEST"):

    os.makedirs(output_dir, exist_ok=True)

    reference_speaker = source_speaker_file
    target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, vad=True)    

    src_path = f'{output_dir}/tmp.wav'

    # Speed is adjustable
    speed = 1.0

    model = TTS(language=language, device=device)
    speaker_ids = model.hps.data.spk2id
    speaker_key = list(speaker_ids.keys())[0]

    speaker_id = speaker_ids[speaker_key]
    speaker_key = speaker_key.lower().replace('_', '-')
    
    filename = os.path.basename(source_speaker_file)[:-4]
    
    source_se = torch.load(f'checkpoints_v2/base_speakers/ses/{speaker_key}.pth', map_location=device)
    if torch.backends.mps.is_available() and device == 'cpu':
        torch.backends.mps.is_available = lambda: False
        
    model.tts_to_file(text, speaker_id, src_path, speed=speed)
    save_path = f'{output_dir}/output_{filename}_translated.wav'

    # Run the tone color converter
    encode_message = "@MyShell"
    tone_color_converter.convert(
        audio_src_path=src_path, 
        src_se=source_se, 
        tgt_se=target_se, 
        output_path=save_path,
        message=encode_message
    )
    
    return save_path

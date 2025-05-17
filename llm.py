import os
os.environ["TOGETHER_API_KEY"] = "YOUR_KEY_HERE"

from together import Together
client = Together()
model_name = "google/gemma-2b-it"

def translate_text_to_text(source_text, source_language, target_language):
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
            "role": "system",
            "content": f"You are an expert in translation from {source_language} to {target_language}. You are very precise and accurate. \
                Only output the translation, and say nothing more."
            },
            {
            "role": "user",
            "content": source_text
            }
        ],
        stream=False,
        )

    return response.choices[0].message.content

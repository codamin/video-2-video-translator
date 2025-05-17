import os
os.environ["TOGETHER_API_KEY"] = "tgp_v1_-WVlTgjJk3ZFeT8mG-DbvkIXwZ4SL4SJxBsfTZoFFis"

from together import Together
client = Together()
model_name = "mistralai/Mistral-7B-Instruct-v0.2"

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

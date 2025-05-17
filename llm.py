import os
os.environ["TOGETHER_API_KEY"] = "tgp_v1_-WVlTgjJk3ZFeT8mG-DbvkIXwZ4SL4SJxBsfTZoFFis"

from together import Together
client = Together()
model_name = "google/gemma-2b-it"
response = client.chat.completions.create(
    model=model_name,
    messages=[
        {
        "role": "system",
        "content": "You are an expert in translation from English to French. You get a paragraph in English as input and translate it to French. Only output the translation, and say nothing more."
        },
        {
        "role": "user",
        "content": english_text
        }
    ],
    stream=False,
    )

return response.choices[0].message.content
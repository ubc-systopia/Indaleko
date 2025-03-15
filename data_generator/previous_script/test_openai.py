import openai 
from openai import OpenAI
import configparser
import icecream as ic
import os

# Replace "your_api_key_here" with your actual OpenAI API key

api_key_file = '/Users/pearl/Indaleko_updated/Indaleko/config/openai-key.ini'
assert os.path.exists(api_key_file), \
    f"API key file ({api_key_file}) not found"
config = configparser.ConfigParser()
config.read(api_key_file, encoding='utf-8-sig')
key = str(config['openai']['api_key'])

try:
    client = OpenAI(api_key=key)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Say this is a test",
            }
        ],
        model="gpt-3.5-turbo",
        stream = False
    )

    print("API Key is working. Response:")
    print(chat_completion.choices[0].message.content)

except openai.APIConnectionError as e:
    print("Invalid API Key. Please check your key and try again.")
except Exception as e:
    print(f"An error occurred: {e}")
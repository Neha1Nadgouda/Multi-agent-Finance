import os
from openai import OpenAI

def test_openai_connection():
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print("Connection successful!")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"Error connecting to OpenAI: {str(e)}")
        return False

if __name__ == "__main__":
    test_openai_connection() 
from google.generativeai import GenerativeModel
import google.generativeai as genai

# genai.configure(api_key="A")

model = GenerativeModel('gemini-2.0-flash')

response = model.generate_content("What is the capital of Kenya?")
print(response.text)
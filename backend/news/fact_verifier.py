from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def verify_facts(text):

    prompt = f"""
You are a professional fact-checking journalist.

Check the following news content.

Rules:
- Remove unverified claims
- Remove speculation
- Keep only factual information
- If facts conflict, choose the most consistent information

Content:
{text}
"""

    response = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    return response.output_text

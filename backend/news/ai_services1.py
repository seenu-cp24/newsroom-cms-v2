import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def improve_article(text):

    prompt = f"""
    Improve the grammar and clarity of this news article.

    IMPORTANT RULES:
    - Keep the article in the SAME language as the input.
    - Do NOT translate the language.
    - Maintain professional newspaper writing style.

    Article:
    {text}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text


def generate_headline(text):

    prompt = f"""
    Generate a professional newspaper headline for this article.

    IMPORTANT RULES:
    - The headline MUST be in the SAME language as the article.
    - Do NOT translate the language.
    - Keep it suitable for newspaper publishing.

    Article:
    {text}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text

def generate_article_from_notes(notes):

    prompt = f"""
    Convert the following raw information into a professional newspaper article.

    IMPORTANT RULES:
    - Keep the article in the SAME language as the input.
    - Maintain journalistic style.
    - Write a clear and structured news article.
    - Do not translate the language.

    Raw Information:
    {notes}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text

from newspaper import Article


def generate_article_from_urls(urls):

    combined_text = ""

    for url in urls:

        try:
            article = Article(url)
            article.download()
            article.parse()

            combined_text += article.text + "\n\n"

        except:
            continue


    prompt = f"""
    Convert the following information into a professional newspaper article.

    IMPORTANT RULES:
    - Keep the article in the SAME language as the input.
    - Maintain journalistic style.
    - Remove duplicated information.
    - Produce a clean news article suitable for publishing.

    Content:
    {combined_text}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text

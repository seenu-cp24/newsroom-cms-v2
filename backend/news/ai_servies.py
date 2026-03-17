import os
from openai import OpenAI
from django.utils import timezone
from newspaper import Article

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def improve_article(text):
    today = timezone.localtime().strftime("%B %d, %Y")

    prompt = f"""
You are a senior newspaper editor.

Today's Date: {today}

Improve the grammar, clarity and readability of the following article.

Rules:
- Keep the SAME language
- Do NOT translate
- Maintain professional journalism tone
- Do not change factual meaning

Article:
{text}
"""

    response = client.responses.create(
        model="gpt-4.1",
        input=prompt,
        temperature=0.3
    )

    return response.output_text


def generate_headline(text):
    prompt = f"""
You are a professional newspaper headline writer.

Create a powerful news headline for the following article.

Rules:
- Same language as article
- Maximum 12 words
- Strong journalistic tone
- Suitable for front page publishing

Article:
{text}
"""

    response = client.responses.create(
        model="gpt-4.1",
        input=prompt,
        temperature=0.7
    )

    return response.output_text


def generate_article_from_notes(notes):
    today = timezone.localtime().strftime("%B %d, %Y")

    prompt = f"""
You are a professional newsroom journalist.

Date: {today}

Convert the following notes into a structured news article.

Article structure:
1. Headline
2. Lead paragraph
3. Detailed explanation
4. Background information
5. Conclusion

Rules:
- Maintain journalistic tone
- Same language as input
- Clear paragraphs
- Suitable for newspaper publishing
- The article should appear as published on {today}

Notes:
{notes}
"""

    response = client.responses.create(
        model="gpt-4.1",
        input=prompt,
        temperature=0.6
    )

    return response.output_text


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

    today = timezone.localtime().strftime("%B %d, %Y")

    prompt = f"""
You are a professional investigative journalist.

Today's Date: {today}

Combine the following source information into a single
clean newspaper article.

Rules:
- Remove duplicate content
- Maintain factual accuracy
- Create structured paragraphs
- Same language as source
- Produce a clean article suitable for publishing

Source Content:
{combined_text}
"""

    response = client.responses.create(
        model="gpt-4.1",
        input=prompt,
        temperature=0.5
    )

    return response.output_text


def research_news_topic(topic):
    today = timezone.localtime().strftime("%B %d, %Y")

    response = client.responses.create(
        model="gpt-4.1",
        tools=[{"type": "web_search"}],
        input=f"""
Research the latest developments about: {topic}

Date: {today}

Provide:
- Latest news developments
- Key facts
- Background context
- Important people or organizations involved
"""
    )

    return response.output_text


def generate_top_news():
    today = timezone.localtime().strftime("%B %d, %Y")

    response = client.responses.create(
        model="gpt-4.1",
        tools=[{"type": "web_search"}],
        input=f"""
Generate the Top 10 latest news topics for India.

Date: {today}

Provide:
- Headline
- Short summary
- Category (Politics, Economy, Technology, World, Sports)

Make them suitable for a news portal homepage.
"""
    )

    return response.output_text

import requests
from bs4 import BeautifulSoup


def search_news(topic):

    query = topic.replace(" ", "+")

    url = f"https://news.google.com/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers)

    soup = BeautifulSoup(r.text, "html.parser")

    links = []

    for a in soup.select("article a"):

        href = a.get("href")

        if href and "./articles" in href:

            full_link = "https://news.google.com" + href[1:]

            links.append(full_link)

    return links[:10]

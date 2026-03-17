import feedparser
import requests
from bs4 import BeautifulSoup


NEWS_SOURCES = {

    "india": [
        "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "https://www.thehindu.com/news/national/feeder/default.rss"
    ],

    "world": [
        "https://www.thehindu.com/news/international/feeder/default.rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
    ],

    "business": [
        "https://www.thehindu.com/business/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms"
    ],

    "technology": [
        "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",
        "https://feeds.arstechnica.com/arstechnica/technology-lab"
    ],

    "sports": [
        "https://www.thehindu.com/sport/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms"
    ]
}


# Telugu news sites (scraping homepage links)

TELUGU_NEWS_SITES = [
    "https://www.eenadu.net",
    "https://www.andhrajyothy.com"
]


def collect_rss_news():

    urls = []

    for feeds in NEWS_SOURCES.values():

        for feed in feeds:

            try:

                parsed = feedparser.parse(feed)

                for entry in parsed.entries[:5]:
                    urls.append(entry.link)

            except:
                continue

    return urls


def collect_telugu_news():

    urls = []

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for site in TELUGU_NEWS_SITES:

        try:

            r = requests.get(site, headers=headers, timeout=10)

            soup = BeautifulSoup(r.text, "html.parser")

            for link in soup.find_all("a", href=True):

                href = link["href"]

                if "http" in href and len(urls) < 10:

                    urls.append(href)

        except:
            continue

    return urls


def collect_news_urls():

    rss_urls = collect_rss_news()

    telugu_urls = collect_telugu_news()

    all_urls = rss_urls + telugu_urls

    return list(set(all_urls))

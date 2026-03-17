from newspaper import Article


def extract_articles(urls):

    articles = []

    for url in urls:

        try:

            article = Article(url)
            article.download()
            article.parse()

            if len(article.text) > 500:

                articles.append(article.text)

        except:
            continue

    return articles

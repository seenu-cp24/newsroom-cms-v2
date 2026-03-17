from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def remove_duplicate_articles(articles):

    if len(articles) <= 1:
        return articles

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(articles)

    similarity_matrix = cosine_similarity(tfidf_matrix)

    unique_articles = []

    for i, article in enumerate(articles):

        duplicate = False

        for j in range(i):

            if similarity_matrix[i][j] > 0.8:
                duplicate = True
                break

        if not duplicate:
            unique_articles.append(article)

    return unique_articles

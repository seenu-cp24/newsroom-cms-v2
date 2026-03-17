from pytrends.request import TrendReq


def get_trending_topics():

    pytrends = TrendReq()

    trends = pytrends.trending_searches(pn="india")

    topics = trends[0].tolist()

    return topics[:10]

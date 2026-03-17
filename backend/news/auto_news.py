from .ai_services import generate_verified_news
from .models import Article
from django.contrib.auth.models import User


def generate_morning_news():

    article_content = generate_verified_news()

    admin = User.objects.filter(is_superuser=True).first()

    Article.objects.create(
        title="Morning AI News Update",
        content=article_content,
        reporter=admin,
        status="draft"
    )

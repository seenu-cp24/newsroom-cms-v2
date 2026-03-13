from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Editions
class Edition(models.Model):

    name = models.CharField(max_length=200)

    total_pages = models.IntegerField(default=16)

    def __str__(self):
        return self.name


# News Categories
class Category(models.Model):

    name = models.CharField(max_length=200)

    edition = models.ForeignKey(
        Edition,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name


# News Article
class Article(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('subeditor_review', 'SubEditor Review'),
        ('editor_sent_back', 'Sent Back by Editor'),
        ('editor_approved', 'Editor Approved'),
        ('pagination', 'Pagination'),
        ('published', 'Published'),
    ]

    title = models.CharField(max_length=500)

    content = models.TextField()

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    # NEW FIELD (important for edition control)
    edition = models.ForeignKey(
        Edition,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    received_from_edition = models.BooleanField(default=False)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Page number assigned by editor
    page_number = models.IntegerField(
        null=True,
        blank=True
    )

    editor_comment = models.TextField(
        null=True,
        blank=True
    )

    edition_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.title


# Article Images (multiple images per article)
class ArticleImage(models.Model):

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(
        upload_to='article_images/'
    )

    caption = models.CharField(
        max_length=255,
        blank=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Image for {self.article.title}"


# Article Version History
class ArticleVersion(models.Model):

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="versions"
    )

    title = models.CharField(max_length=500)

    content = models.TextField()

    edited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    edited_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Version of {self.article.title} by {self.edited_by.username}"


# Article Activity Log
class ArticleActivity(models.Model):

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    action = models.CharField(max_length=255)

    comment = models.TextField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.article.title} - {self.action}"


# Pagination Page Layout
class PageLayout(models.Model):

    page_number = models.IntegerField()

    slot_number = models.IntegerField()

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE
    )

    layout_date = models.DateField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return f"Page {self.page_number} - Slot {self.slot_number} ({self.layout_date})"

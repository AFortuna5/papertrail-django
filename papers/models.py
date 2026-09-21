from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models


class Paper(models.Model):
    class Language(models.TextChoices):
        PORTUGUESE = "pt", "Português"
        ENGLISH = "en", "Inglês"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="papers"
    )
    title = models.CharField(max_length=200)
    abstract = models.TextField(validators=[MaxLengthValidator(20000)])
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.PORTUGUESE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["owner", "-created_at"], name="paper_owner_created_idx")]

    def __str__(self):
        return self.title


class Review(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="reviews")
    source_hash = models.CharField(max_length=64)
    word_count = models.PositiveIntegerField()
    sentence_count = models.PositiveIntegerField()
    findings = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["paper", "source_hash"], name="unique_review_per_content"
            )
        ]

from django.contrib import admin

from .models import Paper, Review


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "language", "created_at"]
    list_filter = ["language"]
    search_fields = ["title", "owner__username"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["paper", "word_count", "created_at"]
    readonly_fields = [
        "paper",
        "source_hash",
        "word_count",
        "sentence_count",
        "findings",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

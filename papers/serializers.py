from rest_framework import serializers

from .models import Paper, Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "source_hash", "word_count", "sentence_count", "findings", "created_at"]
        read_only_fields = fields


class PaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = ["id", "title", "abstract", "language", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_abstract(self, value):
        if len(value.split()) < 5:
            raise serializers.ValidationError("O resumo deve conter pelo menos 5 palavras.")
        return value

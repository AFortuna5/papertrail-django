from django.contrib.auth import logout
from rest_framework import filters, status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Paper
from .serializers import PaperSerializer, ReviewSerializer
from .services import review_paper


class LoginView(ObtainAuthToken):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    def post(self, request):
        if hasattr(request.user, "auth_token"):
            request.user.auth_token.delete()
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaperViewSet(viewsets.ModelViewSet):
    serializer_class = PaperSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "abstract"]
    ordering_fields = ["created_at", "title"]

    def get_queryset(self):
        # Este filtro também protege detail, update, delete e ações customizadas.
        return Paper.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"], url_path="review", serializer_class=ReviewSerializer)
    def review(self, request, pk=None):
        review, created = review_paper(self.get_object())
        return Response(
            ReviewSerializer(review).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], serializer_class=ReviewSerializer)
    def reviews(self, request, pk=None):
        reviews = self.get_object().reviews.all()
        page = self.paginate_queryset(reviews)
        return self.get_paginated_response(ReviewSerializer(page, many=True).data)

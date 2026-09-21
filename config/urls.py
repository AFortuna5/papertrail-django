from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from papers.views import LoginView, LogoutView, PaperViewSet

router = DefaultRouter()
router.register("papers", PaperViewSet, basename="paper")
urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("admin/", admin.site.urls),
    path("api/auth/token/", LoginView.as_view(), name="token"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]

from django.urls import include, path

urlpatterns = [path("api/mobile/v1/", include("api.mobile_urls"))]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SMSViewSet

# Create a router and register our viewset
router = DefaultRouter()
router.register(r'', SMSViewSet, basename='sms')

urlpatterns = [
    path('', include(router.urls)),
]
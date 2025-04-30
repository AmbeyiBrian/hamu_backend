"""
URL configuration for hamu_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# Import viewsets from apps
from shops.views import ShopViewSet
from customers.views import CustomerViewSet
from packages.views import PackageViewSet
from refills.views import RefillViewSet
from sales.views import SalesViewSet
from credits.views import CreditsViewSet
from expenses.views import ExpensesViewSet
from meter_readings.views import MeterReadingViewSet
from stock.views import StockItemViewSet, StockLogViewSet
from users.views import UserViewSet
from sms.views import SMSViewSet
from analytics.views import AnalyticsViewSet
from notifications.views import NotificationViewSet

# The import below was causing errors - these functions don't exist directly in views.py
# Instead, they are implemented as viewset actions
# from sms.views import (
#     send_custom_sms,
#     send_to_shop_customers,
#     send_to_credit_customers,
#     send_free_refill_sms
# )

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'shops', ShopViewSet, basename='shops')
router.register(r'customers', CustomerViewSet, basename='customers')
router.register(r'packages', PackageViewSet, basename='packages')
router.register(r'refills', RefillViewSet, basename='refills')
router.register(r'sales', SalesViewSet, basename='sales')
router.register(r'credits', CreditsViewSet, basename='credits')
router.register(r'expenses', ExpensesViewSet, basename='expenses')
router.register(r'meter-readings', MeterReadingViewSet, basename='meter-readings')
router.register(r'stock-items', StockItemViewSet, basename='stock-items')
router.register(r'stock-logs', StockLogViewSet, basename='stock-logs')
router.register(r'users', UserViewSet, basename='users')
router.register(r'sms', SMSViewSet)  # Add the SMS viewset to the router
router.register(r'analytics', AnalyticsViewSet, basename='analytics')  # Register analytics viewset
router.register(r'notifications', NotificationViewSet, basename='notifications')  # Register notifications viewset

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # JWT Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/auth/', include('rest_framework.urls')),
    
    # Legacy SMS endpoints for backward compatibility
    path('api/sms/custom/', include('sms.urls')),
    
    # Analytics endpoints
    path('api/analytics/', include('analytics.urls')),
]

# Add media file handling for development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

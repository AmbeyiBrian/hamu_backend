from django.urls import path
from .views import SalesAnalyticsView, CustomerAnalyticsView, InventoryAnalyticsView, FinancialAnalyticsView

urlpatterns = [
    path('sales/', SalesAnalyticsView.as_view(), name='sales-analytics'),
    path('customers/', CustomerAnalyticsView.as_view(), name='customer-analytics'),
    path('inventory/', InventoryAnalyticsView.as_view(), name='inventory-analytics'),
    path('financial/', FinancialAnalyticsView.as_view(), name='financial-analytics'),
]
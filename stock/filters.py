import django_filters
from django.db import models
from django.utils import timezone
from datetime import datetime, time
from .models import StockLog

class StockLogFilter(django_filters.FilterSet):
    """
    Custom filter for StockLog model that adds date range filtering
    with proper timezone handling
    """
    min_date = django_filters.DateFilter(method='filter_min_date')
    max_date = django_filters.DateFilter(method='filter_max_date')
    
    def filter_min_date(self, queryset, name, value):
        """
        Filter by minimum date, converting to timezone-aware datetime
        """
        if value:
            # Create a timezone-aware datetime for the start of the day
            min_datetime = timezone.make_aware(
                datetime.combine(value, time.min)
            )
            return queryset.filter(log_date__gte=min_datetime)
        return queryset

    def filter_max_date(self, queryset, name, value):
        """
        Filter by maximum date, converting to timezone-aware datetime
        """
        if value:
            # Create a timezone-aware datetime for the end of the day
            max_datetime = timezone.make_aware(
                datetime.combine(value, time.max)
            )
            return queryset.filter(log_date__lte=max_datetime)
        return queryset
    
    class Meta:
        model = StockLog
        fields = {
            'shop': ['exact'],
            'stock_item': ['exact'],
            'stock_item__item_name': ['exact'],
            'stock_item__item_type': ['exact'],
            'quantity_change': ['gt', 'lt'],
        }
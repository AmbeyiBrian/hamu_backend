from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from hamu_backend.permissions import IsShopAgentOrDirector, FlexibleJWTAuthentication
from sales.models import Sales
from refills.models import Refills
from customers.models import Customers
from expenses.models import Expenses
from shops.models import Shops
from credits.models import Credits
from stock.models import StockItem, StockLog
from meter_readings.models import MeterReading
from stock.services import StockCalculationService


# Analytics ViewSet for router registration
class AnalyticsViewSet(viewsets.ViewSet):
    """
    API endpoint for analytics data.
    """
    authentication_classes = [FlexibleJWTAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsShopAgentOrDirector]
    
    @action(detail=False, methods=['get'])
    def sales(self, request):
        """Get sales analytics data"""
        # Get time range from query parameters
        time_range = request.query_params.get('time_range', 'month')
        
        # Get shop_id from either query params, data, or 'all' as default
        shop_id = request.query_params.get('shop_id')
        
        # Additional logging to debug parameter handling
        print(f"Sales Analytics - Shop ID from query params: {shop_id}")
        print(f"Sales Analytics - All query params: {request.query_params}")
        
        # If shop_id is None, try to get it from data
        if shop_id is None:
            shop_id = request.data.get('shop_id', 'all')
            print(f"Sales Analytics - Shop ID from request data: {shop_id}")        # Calculate date range based on time_range parameter
        end_date = timezone.now()
        if time_range == 'day':
            # Set start_date to the beginning of today (midnight)
            today = end_date.date()
            start_date = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            # Previous day for comparison
            previous_day = today - timedelta(days=1)
            previous_start_date = timezone.make_aware(datetime.combine(previous_day, datetime.min.time()))
            previous_end_date = start_date
        elif time_range == 'week':
            start_date = end_date - timedelta(days=7)
            previous_start_date = start_date - timedelta(days=7)
            previous_end_date = start_date
        elif time_range == 'month':
            start_date = end_date - timedelta(days=30)
            previous_start_date = start_date - timedelta(days=30)
            previous_end_date = start_date
        elif time_range == 'quarter':
            start_date = end_date - timedelta(days=90)
            previous_start_date = start_date - timedelta(days=90)
            previous_end_date = start_date
        elif time_range == 'year':
            start_date = end_date - timedelta(days=365)
            previous_start_date = start_date - timedelta(days=365)
            previous_end_date = start_date
        else:
            start_date = end_date - timedelta(days=30)  # Default to month
            previous_start_date = start_date - timedelta(days=30)
            previous_end_date = start_date

        # Filter sales by date range
        sales_query = Sales.objects.filter(sold_at__gte=start_date, sold_at__lte=end_date)
        refills_query = Refills.objects.filter(created_at__gte=start_date, created_at__lte=end_date)

        # Filter by shop if specified
        if shop_id and shop_id != 'all':
            sales_query = sales_query.filter(shop_id=shop_id)
            refills_query = refills_query.filter(shop_id=shop_id)

        # Calculate total revenue
        sales_revenue = sales_query.aggregate(total=Sum('cost'))['total'] or 0
        refill_revenue = refills_query.aggregate(total=Sum('cost'))['total'] or 0
        total_revenue = sales_revenue + refill_revenue

        # Calculate sales counts
        sales_count = sales_query.count()
        refill_count = refills_query.count()
        total_sales_count = sales_count + refill_count

        # Calculate previous period data for percentage changes
        previous_sales_query = Sales.objects.filter(sold_at__gte=previous_start_date, sold_at__lte=previous_end_date)
        previous_refills_query = Refills.objects.filter(created_at__gte=previous_start_date, created_at__lte=previous_end_date)

        # Filter by shop if specified
        if shop_id and shop_id != 'all':
            previous_sales_query = previous_sales_query.filter(shop_id=shop_id)
            previous_refills_query = previous_refills_query.filter(shop_id=shop_id)

        # Calculate previous period revenue
        previous_sales_revenue = previous_sales_query.aggregate(total=Sum('cost'))['total'] or 0
        previous_refill_revenue = previous_refills_query.aggregate(total=Sum('cost'))['total'] or 0
        previous_total_revenue = previous_sales_revenue + previous_refill_revenue

        # Calculate previous period sales counts
        previous_sales_count = previous_sales_query.count()
        previous_refill_count = previous_refills_query.count()
        previous_total_sales_count = previous_sales_count + previous_refill_count

        # Calculate percentage changes
        revenue_change_percentage = 0
        sales_count_change_percentage = 0
        
        if previous_total_revenue > 0:
            revenue_change_percentage = round(((total_revenue - previous_total_revenue) / previous_total_revenue) * 100, 1)
        
        if previous_total_sales_count > 0:
            sales_count_change_percentage = round(((total_sales_count - previous_total_sales_count) / previous_total_sales_count) * 100, 1)

        # Calculate sales by payment mode
        sales_by_payment_mode = {
            'MPESA': (sales_query.filter(payment_mode='MPESA').aggregate(total=Sum('cost'))['total'] or 0) +
                    (refills_query.filter(payment_mode='MPESA').aggregate(total=Sum('cost'))['total'] or 0),
            'CASH': (sales_query.filter(payment_mode='CASH').aggregate(total=Sum('cost'))['total'] or 0) +
                   (refills_query.filter(payment_mode='CASH').aggregate(total=Sum('cost'))['total'] or 0),
            'CREDIT': (sales_query.filter(payment_mode='CREDIT').aggregate(total=Sum('cost'))['total'] or 0) +
                     (refills_query.filter(payment_mode='CREDIT').aggregate(total=Sum('cost'))['total'] or 0)
        }

        # Calculate sales by shop
        sales_by_shop = {}
        shops = Shops.objects.all()
        for shop in shops:
            shop_sales = sales_query.filter(shop=shop).aggregate(total=Sum('cost'))['total'] or 0
            shop_refills = refills_query.filter(shop=shop).aggregate(total=Sum('cost'))['total'] or 0
            sales_by_shop[shop.shopName] = shop_sales + shop_refills

        # Calculate daily/weekly/monthly sales for trend analysis
        if time_range == 'day':
            # For a day, get hourly breakdown
            sales_trend = []
            for hour in range(24):
                hour_start = start_date.replace(hour=hour, minute=0, second=0)
                hour_end = start_date.replace(hour=hour, minute=59, second=59)
                hour_sales = sales_query.filter(sold_at__gte=hour_start, sold_at__lte=hour_end)
                hour_refills = refills_query.filter(created_at__gte=hour_start, created_at__lte=hour_end)
                hour_revenue = (hour_sales.aggregate(total=Sum('cost'))['total'] or 0) + (hour_refills.aggregate(total=Sum('cost'))['total'] or 0)
                hour_count = hour_sales.count() + hour_refills.count()
                sales_trend.append({
                    'date': hour_start.strftime('%H:%M'),
                    'revenue': hour_revenue,
                    'count': hour_count
                })
        elif time_range == 'week':
            # For a week, get daily breakdown
            sales_trend = []
            for i in range(7):
                day_date = end_date - timedelta(days=6-i)
                day_start = day_date.replace(hour=0, minute=0, second=0)
                day_end = day_date.replace(hour=23, minute=59, second=59)
                day_sales = sales_query.filter(sold_at__gte=day_start, sold_at__lte=day_end)
                day_refills = refills_query.filter(created_at__gte=day_start, created_at__lte=day_end)
                day_revenue = (day_sales.aggregate(total=Sum('cost'))['total'] or 0) + (day_refills.aggregate(total=Sum('cost'))['total'] or 0)
                day_count = day_sales.count() + day_refills.count()
                sales_trend.append({
                    'date': day_date.strftime('%Y-%m-%d'),
                    'revenue': day_revenue,
                    'count': day_count
                })
        else:
            # For month/quarter/year, get weekly breakdown
            sales_trend = []
            num_weeks = 4  # For month
            if time_range == 'quarter':
                num_weeks = 12
            elif time_range == 'year':
                num_weeks = 52
                
            for i in range(num_weeks):
                week_end = end_date - timedelta(days=7*i)
                week_start = week_end - timedelta(days=6)
                week_sales = sales_query.filter(sold_at__gte=week_start, sold_at__lte=week_end)
                week_refills = refills_query.filter(created_at__gte=week_start, created_at__lte=week_end)
                week_revenue = (week_sales.aggregate(total=Sum('cost'))['total'] or 0) + (week_refills.aggregate(total=Sum('cost'))['total'] or 0)
                week_count = week_sales.count() + week_refills.count()
                sales_trend.append({
                    'date': f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}",
                    'revenue': week_revenue,
                    'count': week_count
                })
            # Reverse to get chronological order
            sales_trend.reverse()

        # Get top selling packages
        top_packages = []
        sales_by_package = {}
        
        # Combine sales and refills by package
        for sale in sales_query:
            package_name = sale.package.description
            if package_name not in sales_by_package:
                sales_by_package[package_name] = {'sales': 0, 'revenue': 0}
            sales_by_package[package_name]['sales'] += sale.quantity
            sales_by_package[package_name]['revenue'] += sale.cost
            
        for refill in refills_query:
            package_name = refill.package.description
            if package_name not in sales_by_package:
                sales_by_package[package_name] = {'sales': 0, 'revenue': 0}
            sales_by_package[package_name]['sales'] += refill.quantity
            sales_by_package[package_name]['revenue'] += refill.cost
        
        # Convert to list and sort by revenue
        for name, data in sales_by_package.items():
            top_packages.append({
                'name': name,
                'sales': data['sales'],
                'revenue': data['revenue']
            })
        
        top_packages.sort(key=lambda x: x['revenue'], reverse=True)
        top_packages = top_packages[:5]  # Limit to top 5
        
        response_data = {
            'period': time_range,
            'total_revenue': total_revenue,
            'refill_revenue': refill_revenue,
            'bottle_sales_revenue': sales_revenue,
            'total_sales_count': total_sales_count,
            'refill_count': refill_count,
            'bottle_sales_count': sales_count,
            'sales_by_payment_mode': sales_by_payment_mode,
            'sales_by_shop': sales_by_shop,
            'daily_sales': sales_trend,
            'top_packages': top_packages,
            'revenue_change_percentage': revenue_change_percentage,
            'sales_count_change_percentage': sales_count_change_percentage
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def customers(self, request):
        """Get customer analytics data"""
        # Get shop_id from either query params, data, or 'all' as default
        shop_id = request.query_params.get('shop_id')
        
        # Additional logging to debug parameter handling
        print(f"Customer Analytics - Shop ID from query params: {shop_id}")
        print(f"Customer Analytics - All query params: {request.query_params}")
        
        # If shop_id is None, try to get it from data
        if shop_id is None:
            shop_id = request.data.get('shop_id', 'all')
            print(f"Customer Analytics - Shop ID from request data: {shop_id}")
        
        # Base customer query
        customers_query = Customers.objects.all()
        
        # Improved filtering logic
        if shop_id and shop_id != 'all':
            try:
                # Try parsing as integer if it's a numeric string
                if shop_id.isdigit():
                    shop_id_int = int(shop_id)
                    customers_query = customers_query.filter(shop_id=shop_id_int)
                else:
                    # If not numeric, use as is (could be a slug or name)
                    customers_query = customers_query.filter(shop_id=shop_id)
                print(f"Filtered customer query with shop_id: {shop_id}")
            except Exception as e:
                print(f"Error filtering customers by shop_id: {e}")
                # Continue with unfiltered query if there's an error
            
        # Calculate total customers
        total_customers = customers_query.count()
        
        # Calculate new customers in the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_customers = customers_query.filter(date_registered__gte=thirty_days_ago).count()
        
        # Calculate active customers (had a refill in the last 30 days)
        active_customer_ids = set()
        refills_query = Refills.objects.filter(created_at__gte=thirty_days_ago)
        if shop_id and shop_id != 'all':
            refills_query = refills_query.filter(shop_id=shop_id)
            
        active_customer_ids.update(refills_query.values_list('customer_id', flat=True).distinct())
        active_customers = len(active_customer_ids)
        
        # Calculate loyalty redemptions
        loyalty_query = refills_query.filter(is_free=True)
        loyalty_redemptions = loyalty_query.count()
        
        # Calculate average time between refills
        avg_time_between_refills = 0
        customers_with_multiple_refills = 0
        
        for customer in customers_query:
            customer_refills = Refills.objects.filter(customer=customer).order_by('created_at')
            if customer_refills.count() >= 2:
                customers_with_multiple_refills += 1
                total_days = 0
                prev_date = None
                for refill in customer_refills:
                    if prev_date:
                        days_diff = (refill.created_at - prev_date).days
                        total_days += days_diff
                    prev_date = refill.created_at
                
                if customers_with_multiple_refills > 0:
                    customer_avg = total_days / (customer_refills.count() - 1)
                    avg_time_between_refills += customer_avg
        
        if customers_with_multiple_refills > 0:
            avg_time_between_refills /= customers_with_multiple_refills
        avg_time_between_refills = round(avg_time_between_refills)
        
        # Calculate credits outstanding
        credits_outstanding = 0
        credits_query = Credits.objects.all()
        if shop_id and shop_id != 'all':
            credits_query = credits_query.filter(shop_id=shop_id)
            
        # Credits given through CREDIT payment mode in sales and refills
        credit_sales = Sales.objects.filter(payment_mode='CREDIT')
        credit_refills = Refills.objects.filter(payment_mode='CREDIT')
        
        if shop_id and shop_id != 'all':
            credit_sales = credit_sales.filter(shop_id=shop_id)
            credit_refills = credit_refills.filter(shop_id=shop_id)
            
        credits_given = (credit_sales.aggregate(total=Sum('cost'))['total'] or 0) + \
                        (credit_refills.aggregate(total=Sum('cost'))['total'] or 0)
                        
        credits_repaid = credits_query.aggregate(total=Sum('money_paid'))['total'] or 0
        credits_outstanding = credits_given - credits_repaid
        
        # Calculate customer growth over the last 4 months
        customer_growth = []
        for i in range(4):
            month_end = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_start = month_end.replace(day=1)
            month_name = month_start.strftime('%b')
            
            month_customers = customers_query.filter(date_registered__lt=month_end).count()
            customer_growth.append({
                'month': month_name,
                'customers': month_customers
            })
        
        customer_growth.reverse()  # Chronological order
        
        # Calculate customer activity levels
        very_active_threshold = 30  # days
        active_threshold = 60  # days
        irregular_threshold = 90  # days
        
        very_active_date = timezone.now() - timedelta(days=very_active_threshold)
        active_date = timezone.now() - timedelta(days=active_threshold)
        irregular_date = timezone.now() - timedelta(days=irregular_threshold)
        
        very_active = 0
        active = 0
        irregular = 0
        inactive = 0
        
        for customer in customers_query:
            latest_refill = Refills.objects.filter(customer=customer).order_by('-created_at').first()
            if not latest_refill:
                inactive += 1
                continue
                
            if latest_refill.created_at >= very_active_date:
                very_active += 1
            elif latest_refill.created_at >= active_date:
                active += 1
            elif latest_refill.created_at >= irregular_date:
                irregular += 1
            else:
                inactive += 1
                
        customer_activity = {
            'Very Active': very_active,
            'Active': active,
            'Irregular': irregular,
            'Inactive': inactive
        }
        
        # Calculate loyalty metrics
        free_refill_interval = 6  # Default, could come from shop settings
        
        # Count customers eligible for free refill (have had enough refills)
        eligible_for_free_refill = 0
        for customer in customers_query:
            # Count refills since last free refill
            last_free_refill = Refills.objects.filter(
                customer=customer,
                is_free=True
            ).order_by('-created_at').first()
            
            if last_free_refill:
                refill_count = Refills.objects.filter(
                    customer=customer,
                    created_at__gt=last_free_refill.created_at,
                    is_free=False
                ).count()
            else:
                refill_count = Refills.objects.filter(
                    customer=customer,
                    is_free=False
                ).count()
                
            if refill_count >= free_refill_interval:
                eligible_for_free_refill += 1
                
        # Calculate average refills per customer
        total_refills = Refills.objects.filter(customer__in=customers_query).count()
        average_refills_per_customer = round(total_refills / total_customers, 1) if total_customers > 0 else 0
        
        # Get number of customers who've redeemed a free refill this month
        this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        redeemed_this_month = Refills.objects.filter(
            customer__in=customers_query,
            is_free=True,
            created_at__gte=this_month_start
        ).values('customer').distinct().count()
        
        loyalty_metrics = {
            'eligible_for_free_refill': eligible_for_free_refill,
            'redeemed_this_month': redeemed_this_month,
            'average_refills_per_customer': average_refills_per_customer
        }
        
        # Get credit analysis
        credit_customers = set(credit_sales.values_list('customer_id', flat=True)).union(
            set(credit_refills.values_list('customer_id', flat=True))
        )
        credit_customers_count = len(credit_customers)
        
        avg_credit_per_customer = round(credits_outstanding / credit_customers_count, 2) if credit_customers_count > 0 else 0
        
        credit_analysis = {
            'total_credit_given': credits_given,
            'total_repaid': credits_repaid,
            'credit_customers': credit_customers_count,
            'avg_credit_per_customer': avg_credit_per_customer
        }
        
        # Get top customers by total spent
        top_customers = []
        for customer in customers_query:
            customer_sales = Sales.objects.filter(customer=customer)
            customer_refills = Refills.objects.filter(customer=customer)
            
            total_spent = (customer_sales.aggregate(total=Sum('cost'))['total'] or 0) + \
                         (customer_refills.aggregate(total=Sum('cost'))['total'] or 0)
                         
            refills_count = customer_refills.count()
            purchases_count = customer_sales.count()
            
            if total_spent > 0:  # Only include customers who've spent something
                top_customers.append({
                    'id': customer.id,
                    'name': customer.names,
                    'phone': customer.phone_number,
                    'refills': refills_count,
                    'purchases': purchases_count,
                    'total_spent': total_spent
                })
                
        top_customers.sort(key=lambda x: x['total_spent'], reverse=True)
        top_customers = top_customers[:10]  # Limit to top 10
        
        response_data = {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'new_customers': new_customers,
            'loyalty_redemptions': loyalty_redemptions,
            'avg_time_between_refills': avg_time_between_refills,
            'credits_outstanding': credits_outstanding,
            'customer_growth': customer_growth,
            'customer_activity': customer_activity,
            'loyalty_metrics': loyalty_metrics,
            'credit_analysis': credit_analysis,
            'top_customers': top_customers
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def inventory(self, request):
        """Get inventory analytics data"""
        # Get shop_id from either query params, data, or 'all' as default
        shop_id = request.query_params.get('shop_id')
        
        # Additional logging to debug parameter handling
        print(f"Shop ID from query params: {shop_id}")
        print(f"All query params: {request.query_params}")
        
        # If shop_id is None, try to get it from data
        if shop_id is None:
            shop_id = request.data.get('shop_id', 'all')
            print(f"Shop ID from request data: {shop_id}")
        
        # Base queries
        stock_items_query = StockItem.objects.all()
        
        # Improved filtering logic
        if shop_id and shop_id != 'all':
            try:
                # Try parsing as integer if it's a numeric string
                if shop_id.isdigit():
                    shop_id_int = int(shop_id)
                    stock_items_query = stock_items_query.filter(shop_id=shop_id_int)
                else:
                    # If not numeric, use as is (could be a slug or name)
                    stock_items_query = stock_items_query.filter(shop_id=shop_id)
                print(f"Filtered query with shop_id: {shop_id}")
            except Exception as e:
                print(f"Error filtering by shop_id: {e}")
                # Continue with unfiltered query if there's an error
        
        # Get all stock items with current quantities
        stock_items = []
        low_stock_items = 0
        total_stock_items = 0
        
        for item in stock_items_query:
            quantity = StockCalculationService.get_current_stock_level(item)
            
            # Use the threshold and reorder_point fields from the stock item
            if quantity <= item.threshold:
                low_stock_items += 1
                
            total_stock_items += quantity
                
            stock_items.append({
                'id': item.id,
                'name': item.item_name,
                'type': item.item_type,
                'quantity': quantity,
                'threshold': item.threshold,
                'reorder_point': item.reorder_point
            })
            
        # Calculate water consumption from meter readings
        water_consumption = 0
        water_wastage = 0
        
        # Get meter readings from the last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)
        meter_readings_query = MeterReading.objects.filter(reading_date__gte=seven_days_ago)
        
        if shop_id and shop_id != 'all':
            meter_readings_query = meter_readings_query.filter(shop_id=shop_id)
            
        # Group by shop and reading_type to calculate differences
        water_consumption_trends = []
        
        # Calculate total water consumption from refills in the last 7 days
        refills_query = Refills.objects.filter(created_at__gte=seven_days_ago)
        if shop_id and shop_id != 'all':
            refills_query = refills_query.filter(shop_id=shop_id)
            
        # Sum water amounts from all refills based on package water_amount
        for refill in refills_query:
            water_amount = refill.package.water_amount if hasattr(refill.package, 'water_amount') else 0
            water_consumption += water_amount * refill.quantity
            
        # Estimate water wastage (5% of consumption for demo)
        water_wastage = round(water_consumption * 0.05)
        
        # Generate daily water consumption for the last 7 days
        for i in range(7):
            day_date = timezone.now().date() - timedelta(days=6-i)
            day_refills = refills_query.filter(created_at__date=day_date)
            
            day_consumption = 0
            for refill in day_refills:
                water_amount = refill.package.water_amount if hasattr(refill.package, 'water_amount') else 0
                day_consumption += water_amount * refill.quantity
                
            water_consumption_trends.append({
                'date': day_date.strftime('%Y-%m-%d'),
                'consumption': day_consumption
            })
            
        # Calculate stock movements for the last 7 days
        stock_movements = []
        
        # Get unique item names and types
        unique_items = set([(item['name'], item['type']) for item in stock_items])
        
        for name, item_type in unique_items:
            # Find the stock item
            stock_item_query = stock_items_query.filter(item_name=name, item_type=item_type)
            if stock_item_query.exists():
                stock_item = stock_item_query.first()
                
                # Get stock logs for this item in the last 7 days
                stock_logs = StockLog.objects.filter(
                    stock_item=stock_item,
                    log_date__gte=seven_days_ago
                )
                
                added = stock_logs.filter(quantity_change__gt=0).aggregate(
                    total=Sum('quantity_change'))['total'] or 0
                    
                removed = abs(stock_logs.filter(quantity_change__lt=0).aggregate(
                    total=Sum('quantity_change'))['total'] or 0)
                    
                net = added - removed
                
                if added > 0 or removed > 0:  # Only include items with movement
                    stock_movements.append({
                        'item': f"{name} {item_type}",
                        'added': added,
                        'removed': removed,
                        'net': net
                    })
        
        # Sort by absolute net change
        stock_movements.sort(key=lambda x: abs(x['net']), reverse=True)
        stock_movements = stock_movements[:5]  # Limit to top 5
        
        response_data = {
            'total_stock_items': total_stock_items,
            'low_stock_items': low_stock_items,
            'water_consumption': water_consumption,
            'water_wastage': water_wastage,
            'stock_items': stock_items,
            'water_consumption_trends': water_consumption_trends,
            'stock_movements': stock_movements
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def financial(self, request):
        """Get financial analytics data"""
        # Get time range from query parameters
        time_range = request.query_params.get('time_range', 'month')
        
        # Get shop_id from either query params, data, or 'all' as default
        shop_id = request.query_params.get('shop_id')
        
        # Additional logging to debug parameter handling
        print(f"Financial Analytics - Shop ID from query params: {shop_id}")
        print(f"Financial Analytics - All query params: {request.query_params}")
        
        # If shop_id is None, try to get it from data
        if shop_id is None:
            shop_id = request.data.get('shop_id', 'all')
            print(f"Financial Analytics - Shop ID from request data: {shop_id}")        # Calculate date range based on time_range parameter
        end_date = timezone.now()
        if time_range == 'day':
            # Set start_date to the beginning of today (midnight)
            today = end_date.date()
            start_date = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        elif time_range == 'week':
            start_date = end_date - timedelta(days=7)
        elif time_range == 'month':
            start_date = end_date - timedelta(days=30)
        elif time_range == 'quarter':
            start_date = end_date - timedelta(days=90)
        elif time_range == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)  # Default to month

        # Filter queries by date range
        sales_query = Sales.objects.filter(sold_at__gte=start_date, sold_at__lte=end_date)
        refills_query = Refills.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        expenses_query = Expenses.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        credits_query = Credits.objects.filter(payment_date__gte=start_date, payment_date__lte=end_date)

        # Filter by shop if specified
        if shop_id and shop_id != 'all':
            sales_query = sales_query.filter(shop_id=shop_id)
            refills_query = refills_query.filter(shop_id=shop_id)
            expenses_query = expenses_query.filter(shop_id=shop_id)
            credits_query = credits_query.filter(shop_id=shop_id)

        # Calculate total revenue
        sales_revenue = sales_query.aggregate(total=Sum('cost'))['total'] or 0
        refill_revenue = refills_query.aggregate(total=Sum('cost'))['total'] or 0
        total_revenue = sales_revenue + refill_revenue

        # Calculate total expenses
        total_expenses = expenses_query.aggregate(total=Sum('cost'))['total'] or 0

        # Calculate gross profit (revenue - direct expenses)
        # For simplicity, we'll assume 30% of expenses are direct costs
        direct_expenses = total_expenses * Decimal('0.3')  # Simplified
        gross_profit = total_revenue - direct_expenses

        # Calculate net profit (gross profit - indirect expenses)
        indirect_expenses = total_expenses * Decimal('0.7')  # Simplified
        net_profit = gross_profit - indirect_expenses

        # Calculate profit margin
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        profit_margin = round(profit_margin, 1)

        # Group expenses by category
        expense_categories = {}
        for expense in expenses_query:
            category = expense.description.split(' - ')[0] if ' - ' in expense.description else 'Other'
            # Simplify categories
            if 'Electricity' in category or 'Water' in category or 'Utility' in category:
                category = 'Utilities'
            elif 'Rent' in category:
                category = 'Rent'
            elif 'Salary' in category or 'Wage' in category or 'Staff' in category:
                category = 'Salaries'
            elif 'Maintenance' in category or 'Repair' in category:
                category = 'Maintenance'
                
            if category not in expense_categories:
                expense_categories[category] = 0
            expense_categories[category] += expense.cost

        # Calculate revenue by shop
        revenue_by_shop = {}
        shops = Shops.objects.all()
        for shop in shops:
            shop_sales = sales_query.filter(shop=shop).aggregate(total=Sum('cost'))['total'] or 0
            shop_refills = refills_query.filter(shop=shop).aggregate(total=Sum('cost'))['total'] or 0
            revenue_by_shop[shop.shopName] = shop_sales + shop_refills

        # Calculate monthly financial trends
        monthly_financials = []
        
        if time_range == 'month':
            # For month, get weekly breakdown
            for i in range(4):  # 4 weeks
                week_end = end_date - timedelta(days=7*i)
                week_start = week_end - timedelta(days=6)
                
                week_sales = sales_query.filter(sold_at__gte=week_start, sold_at__lte=week_end)
                week_refills = refills_query.filter(created_at__gte=week_start, created_at__lte=week_end)
                week_expenses = expenses_query.filter(created_at__gte=week_start, created_at__lte=week_end)
                
                week_revenue = (week_sales.aggregate(total=Sum('cost'))['total'] or 0) + \
                              (week_refills.aggregate(total=Sum('cost'))['total'] or 0)
                              
                week_expense = week_expenses.aggregate(total=Sum('cost'))['total'] or 0
                week_profit = week_revenue - week_expense
                
                monthly_financials.append({
                    'month': f"Week {4-i}",  # Label as Week 1, Week 2, etc.
                    'revenue': week_revenue,
                    'expenses': week_expense,
                    'profit': week_profit
                })
        else:
            # For quarter/year, get monthly breakdown
            num_months = 3  # For quarter
            if time_range == 'year':
                num_months = 12
                
            for i in range(num_months):
                month_end = end_date.replace(day=1) - timedelta(days=1)  # Last day of previous month
                month_end = month_end - timedelta(days=30*i)  # Go back i months
                month_start = month_end.replace(day=1)  # First day of that month
                
                month_sales = sales_query.filter(sold_at__gte=month_start, sold_at__lte=month_end)
                month_refills = refills_query.filter(created_at__gte=month_start, created_at__lte=month_end)
                month_expenses = expenses_query.filter(created_at__gte=month_start, created_at__lte=month_end)
                
                month_revenue = (month_sales.aggregate(total=Sum('cost'))['total'] or 0) + \
                               (month_refills.aggregate(total=Sum('cost'))['total'] or 0)
                               
                month_expense = month_expenses.aggregate(total=Sum('cost'))['total'] or 0
                month_profit = month_revenue - month_expense
                
                monthly_financials.append({
                    'month': month_start.strftime('%b'),  # Month abbreviation
                    'revenue': month_revenue,
                    'expenses': month_expense,
                    'profit': month_profit
                })
                
        # Reverse to get chronological order
        monthly_financials.reverse()

        # Calculate cash flow
        # Cash inflow: sales + refills + credit payments
        cash_inflow = total_revenue + (credits_query.aggregate(total=Sum('money_paid'))['total'] or 0)
        
        # Cash outflow: expenses
        cash_outflow = total_expenses
        
        # Net cash flow
        net_cash_flow = cash_inflow - cash_outflow
        
        cash_flow = {
            'inflow': cash_inflow,
            'outflow': cash_outflow,
            'net': net_cash_flow
        }
        
        # Get recent expenses
        recent_expenses = []
        for expense in expenses_query.order_by('-created_at')[:5]:
            category = expense.description.split(' - ')[0] if ' - ' in expense.description else 'Other'
            # Simplify categories as before
            if 'Electricity' in category or 'Water' in category or 'Utility' in category:
                category = 'Utilities'
            elif 'Rent' in category:
                category = 'Rent'
            elif 'Salary' in category or 'Wage' in category or 'Staff' in category:
                category = 'Salaries'
            elif 'Maintenance' in category or 'Repair' in category:
                category = 'Maintenance'
                
            recent_expenses.append({
                'id': expense.id,
                'date': expense.created_at.strftime('%Y-%m-%d'),
                'description': expense.description,
                'amount': expense.cost,
                'category': category
            })

        response_data = {
            'total_revenue': total_revenue,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'total_expenses': total_expenses,
            'profit_margin': profit_margin,
            'expense_categories': expense_categories,
            'revenue_by_shop': revenue_by_shop,
            'monthly_financials': monthly_financials,
            'cash_flow': cash_flow,
            'recent_expenses': recent_expenses
        }
        
        return Response(response_data)


# Keep the existing individual APIView classes for backward compatibility
class SalesAnalyticsView(APIView):
    """
    API endpoint for sales analytics data.
    """
    authentication_classes = [FlexibleJWTAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsShopAgentOrDirector]

    def get(self, request):
        # Create a ViewSet instance and delegate to it
        viewset = AnalyticsViewSet()
        viewset.request = request
        return viewset.sales(request)


class CustomerAnalyticsView(APIView):
    """
    API endpoint for customer analytics data.
    """
    authentication_classes = [FlexibleJWTAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsShopAgentOrDirector]

    def get(self, request):
        # Create a ViewSet instance and delegate to it
        viewset = AnalyticsViewSet()
        viewset.request = request
        return viewset.customers(request)


class InventoryAnalyticsView(APIView):
    """
    API endpoint for inventory analytics data.
    """
    authentication_classes = [FlexibleJWTAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsShopAgentOrDirector]

    def get(self, request):
        # Create a ViewSet instance and delegate to it
        viewset = AnalyticsViewSet()
        viewset.request = request
        return viewset.inventory(request)


class FinancialAnalyticsView(APIView):
    """
    API endpoint for financial analytics data.
    """
    authentication_classes = [FlexibleJWTAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsShopAgentOrDirector]

    def get(self, request):
        # Create a ViewSet instance and delegate to it
        viewset = AnalyticsViewSet()
        viewset.request = request
        return viewset.financial(request)

from django.shortcuts import render
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, F, Q
from .models import Refills
from .serializers import RefillSerializer
from hamu_backend.permissions import IsShopAgentOrDirector
from sms.utils import send_free_refill_notification


class RefillViewSet(viewsets.ModelViewSet):
    """
    API endpoint for customer refills management.
    Directors can see all refills across shops.
    Shop agents can only view refills from their shop.
    """
    serializer_class = RefillSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['customer__names', 'customer__phone_number', 'agent_name']
    ordering_fields = ['created_at', 'payment_mode', 'cost']
    filterset_fields = ['shop', 'customer', 'payment_mode', 'is_free']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all refills across all shops
            return Refills.objects.all().select_related('shop', 'customer', 'package')
        else:
            # Agents only see refills from their shop
            return Refills.objects.filter(shop=user.shop).select_related('shop', 'customer', 'package')
    
    def perform_create(self, serializer):
        """Automatically set shop and agent_name for agent users"""
        user = self.request.user
        if user.user_class != 'Director' and not serializer.validated_data.get('shop'):
            serializer.validated_data['shop'] = user.shop
            
        if not serializer.validated_data.get('agent_name'):
            serializer.validated_data['agent_name'] = user.names
            
        # Save the refill record
        refill = serializer.save()
        
        # SMS notifications are now handled in the RefillSerializer.create() method
        # to avoid duplicate messages
    
    @action(detail=False, methods=['get'])
    def eligible_for_free(self, request):
        """
        List customers who are eligible for a free refill based on total refill quantity.
        
        For every freeRefillInterval refills (e.g., 8), a customer becomes eligible for 1 free refill.
        This works based on the total quantity of refills, regardless of whether they were free or paid.
        
        Query parameters:
            customer_id: Optional. Filter results to a specific customer.
            shop_id: Optional. Filter results to customers of a specific shop.
        """
        user = self.request.user
        customer_id = request.query_params.get('customer_id')
        shop_id = request.query_params.get('shop_id')
        
        # For each customer, get their total refill quantities
        from django.db import connection
        
        # Base query focusing on total quantities only
        base_query = """
            WITH CustomerRefillStats AS (
                SELECT 
                    r.customer_id,
                    c.names as customer_name,
                    c.phone_number,
                    s.id as shop_id,
                    s."shopName" as shop_name,
                    s."freeRefillInterval",
                    SUM(r.quantity) as total_quantity
                FROM refills_refills r
                JOIN customers_customers c ON r.customer_id = c.id
                JOIN shops_shops s ON c.shop_id = s.id
                WHERE r.customer_id IS NOT NULL
        """
        
        # Add filters if provided
        if customer_id:
            base_query += f" AND r.customer_id = {customer_id}"
        
        if shop_id:
            base_query += f" AND s.id = {shop_id}"
            
        if user.user_class != 'Director':
            # Non-directors can only see their shop's data
            if user.shop:
                base_query += f" AND s.id = {user.shop.id}"
        
        base_query += """
                GROUP BY r.customer_id, c.names, c.phone_number, s.id, s."shopName", s."freeRefillInterval"
            )
            SELECT 
                customer_id,
                customer_name,
                phone_number,
                shop_id,
                shop_name,
                "freeRefillInterval",
                total_quantity,
                FLOOR(total_quantity / "freeRefillInterval") as earned_free_refills,
                total_quantity % "freeRefillInterval" as refills_since_last_free,
                CASE WHEN "freeRefillInterval" > 0 
                    THEN "freeRefillInterval" - (total_quantity % "freeRefillInterval")
                    ELSE 0 END as refills_until_next_free
            FROM CustomerRefillStats
            WHERE "freeRefillInterval" > 0
        """
        
        # Show customers who have earned free refills (earned_free_refills > 0),
        # not just those who are at exact thresholds
        if not customer_id:
            base_query += ' AND FLOOR(total_quantity / "freeRefillInterval") > 0'
        
        # Add ordering
        base_query += ' ORDER BY shop_name, customer_name'
        
        # Use raw SQL for better performance with large datasets
        with connection.cursor() as cursor:
            cursor.execute(base_query)
            columns = [col[0] for col in cursor.description]
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
        
        return Response(results)
    
    @action(detail=False, methods=['post'])
    def notify_eligible_customers(self, request):
        """Send SMS notifications to all customers eligible for free refills"""
        eligible_customers = self.eligible_for_free(request).data
        
        notification_count = 0
        for customer_data in eligible_customers:
            from customers.models import Customers
            customer = Customers.objects.get(id=customer_data['customer_id'])
            send_free_refill_notification(customer, is_thankyou=False)
            notification_count += 1
        
        return Response({
            'success': True,
            'notifications_sent': notification_count
        })
    
    @action(detail=False, methods=['get'])
    def customer_loyalty_info(self, request):
        """
        Calculate how many free refills a customer is entitled to for a specific transaction.
        
        For every freeRefillInterval refills (e.g., 8), a customer gets 1 free refill.
        This is calculated purely based on the total number of refills, not distinguishing
        between free or paid refills.
        
        Query parameters:
            customer_id: Required. The ID of the customer.
            package_id: Required. The ID of the package being refilled.
            quantity: Optional. The requested quantity for the transaction (default: 1).
            
        Returns:
            JSON with free refill eligibility, breakdown of free vs paid quantities,
            and the calculated cost.
        """
        from packages.models import Packages
        from customers.models import Customers
        from django.db.models import Sum
        
        # Get parameters from request
        customer_id = request.query_params.get('customer_id')
        package_id = request.query_params.get('package_id')
        quantity = int(request.query_params.get('quantity', 1))
        
        # Validate required parameters
        if not customer_id or not package_id:
            return Response(
                {"detail": "customer_id and package_id are required parameters"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Fetch customer and package
            customer = Customers.objects.select_related('shop').get(id=customer_id)
            package = Packages.objects.get(id=package_id)
            
            # Get the shop's free refill interval
            free_refill_interval = customer.shop.freeRefillInterval
            
            # Get the sum of all refill quantities for this customer and this package
            total_refill_quantity_result = Refills.objects.filter(
                customer=customer,
                package=package
            ).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            # Calculate free quantity based on the new logic
            free_quantity = 0
            refills_until_next_free = 0
            
            if free_refill_interval > 0:
                # Calculate totals before and after this transaction
                total_before = total_refill_quantity_result
                total_after = total_refill_quantity_result + quantity
                
                # How many free refills should be earned after this transaction
                # based on crossing thresholds
                thresholds_before = total_before // free_refill_interval
                thresholds_after = total_after // free_refill_interval
                
                # Free quantity is the number of new thresholds crossed in this transaction
                free_quantity = thresholds_after - thresholds_before
                
                # Cap free quantity by the requested quantity
                free_quantity = min(free_quantity, quantity)
                
                # Calculate how many refills until the next free one
                refills_until_next_free = free_refill_interval - (total_after % free_refill_interval)
                if refills_until_next_free == free_refill_interval:
                    refills_until_next_free = 0
                
                print(f"Total before: {total_before}, Total after: {total_after}")
                print(f"Thresholds before: {thresholds_before}, Thresholds after: {thresholds_after}")
                print(f"Free quantity: {free_quantity}, Refills until next: {refills_until_next_free}")
            
            # Calculate paid quantity (requested quantity minus free quantity)
            paid_quantity = quantity - free_quantity
            
            # Calculate cost based on paid quantity only
            cost = package.price * paid_quantity
            
            # Prepare response
            result = {
                'customer_id': int(customer_id),
                'package_id': int(package_id),
                'shop_id': customer.shop.id,
                'free_refill_interval': free_refill_interval,
                'paid_refills_count': total_refill_quantity_result,
                'requested_quantity': quantity,
                'free_quantity': free_quantity,
                'paid_quantity': paid_quantity,
                'unit_price': float(package.price),
                'total_cost': float(cost),
                'refills_until_next_free': refills_until_next_free
            }
            
            return Response(result)
            
        except Customers.DoesNotExist:
            return Response(
                {"detail": f"Customer with ID {customer_id} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Packages.DoesNotExist:
            return Response(
                {"detail": f"Package with ID {package_id} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

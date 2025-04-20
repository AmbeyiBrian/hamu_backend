from django.shortcuts import render
from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from django.conf import settings
from hamu_backend.permissions import IsShopAgentOrDirector
from customers.models import Customers
from shops.models import Shops
from .models import SMS
from .serializers import (
    SMSSerializer, 
    SMSSendToCustomerSerializer,
    SMSSendCustomSerializer,
    SMSSendToShopCustomersSerializer,
    SMSSendToCreditCustomersSerializer,
    SMSSendFreeRefillSerializer
)
from .utils import (
    send_batch_sms, 
    send_free_refill_notification,
    send_shop_customers_sms,
    send_credit_customers_sms
)


class SMSViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing SMS logs.
    """
    queryset = SMS.objects.all()
    serializer_class = SMSSerializer
    permission_classes = [IsShopAgentOrDirector]
    
    def get_queryset(self):
        user = self.request.user
        # Directors can see all SMS logs, agents can only see their shop's logs
        if user.user_class == 'Director':
            return SMS.objects.all().order_by('-sent_at')
        else:
            return SMS.objects.filter(sender=user).order_by('-sent_at')
    
    @action(detail=False, methods=['post'])
    def send_custom(self, request):
        """
        Send a custom SMS to specified recipients.
        """
        serializer = SMSSendCustomSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        recipients = serializer.validated_data['recipients']
        message = serializer.validated_data['message']
        
        # Check if we're sending to too many recipients at once
        if len(recipients) > 1000:
            return Response({
                'error': 'Maximum 1000 recipients allowed per request'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            responses = send_batch_sms(recipients, message)
            
            # Log each SMS sent
            sms_logs = []
            for recipient in recipients:
                sms = SMS.objects.create(
                    target_phone=recipient,
                    sender=request.user,
                    message_body=message
                )
                sms_logs.append(SMSSerializer(sms).data)
                
            return Response({
                'success': True,
                'sms_logs': sms_logs
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def send_to_customer(self, request):
        """
        Send an SMS to a specific customer.
        """
        serializer = SMSSendToCustomerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        customer_id = serializer.validated_data['customer_id']
        message = serializer.validated_data['message']
        
        try:
            customer = Customers.objects.get(id=customer_id)
            
            # Check if current user has permission for this customer
            user = request.user
            if user.user_class != 'Director' and user.shop.id != customer.shop.id:
                return Response({
                    'error': 'You do not have permission to send SMS to this customer'
                }, status=status.HTTP_403_FORBIDDEN)
            
            phone_number = customer.phone_number
            response = send_batch_sms([phone_number], message)
            
            # Log the SMS
            sms = SMS.objects.create(
                target_phone=phone_number,
                sender=request.user,
                message_body=message
            )
            
            return Response({
                'success': True,
                'customer': customer.names,
                'phone': phone_number,
                'sms': SMSSerializer(sms).data
            })
        except Customers.DoesNotExist:
            return Response({
                'error': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def send_to_shop_customers(self, request):
        """
        Send an SMS to all customers of a specific shop.
        """
        serializer = SMSSendToShopCustomersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        shop_id = serializer.validated_data['shop_id']
        message = serializer.validated_data['message']
        
        try:
            shop = Shops.objects.get(id=shop_id)
            
            # Check if current user has permission for this shop
            user = request.user
            if user.user_class != 'Director' and user.shop.id != shop.id:
                return Response({
                    'error': 'You do not have permission to send SMS to this shop\'s customers'
                }, status=status.HTTP_403_FORBIDDEN)
            
            responses = send_shop_customers_sms(shop, message)
            
            # Log the SMS for each customer
            sms_logs = []
            for customer in shop.customers.all():
                if customer.phone_number:
                    sms = SMS.objects.create(
                        target_phone=customer.phone_number,
                        sender=request.user,
                        message_body=message
                    )
                    sms_logs.append(SMSSerializer(sms).data)
            
            return Response({
                'success': True,
                'shop': shop.shopName,
                'customer_count': len(sms_logs),
                'sms_logs': sms_logs[:10]  # Return just first 10 for brevity
            })
        except Shops.DoesNotExist:
            return Response({
                'error': 'Shop not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def send_to_credit_customers(self, request):
        """
        Send an SMS to all customers with credits.
        """
        serializer = SMSSendToCreditCustomersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        message = serializer.validated_data['message']
        
        try:
            from credits.models import Credits
            from django.db.models import Count
            
            # Get customers with at least one credit
            customers_with_credits = Credits.objects.values('customer__phone_number').annotate(
                credit_count=Count('id')
            ).filter(credit_count__gt=0)
            
            recipients = [item['customer__phone_number'] for item in customers_with_credits if item['customer__phone_number']]
            responses = send_batch_sms(recipients, message)
            
            # Log the SMS for each customer
            sms_logs = []
            for phone in recipients:
                sms = SMS.objects.create(
                    target_phone=phone,
                    sender=request.user,
                    message_body=message
                )
                sms_logs.append(SMSSerializer(sms).data)
            
            return Response({
                'success': True,
                'recipients_count': len(recipients),
                'sms_logs': sms_logs[:10]  # Return just first 10 for brevity
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def send_free_refill_sms(self, request):
        """
        Send a free refill notification to a specific customer.
        """
        serializer = SMSSendFreeRefillSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        customer_id = serializer.validated_data['customer_id']
        is_thankyou = serializer.validated_data.get('is_thankyou', False)
        
        try:
            customer = Customers.objects.get(id=customer_id)
            
            # Check if current user has permission for this customer
            user = request.user
            if user.user_class != 'Director' and user.shop.id != customer.shop.id:
                return Response({
                    'error': 'You do not have permission to send SMS to this customer'
                }, status=status.HTTP_403_FORBIDDEN)
            
            response = send_free_refill_notification(customer, is_thankyou=is_thankyou)
            
            # Log the SMS
            shop_name = customer.shop.shopName
            if is_thankyou:
                message = (f"Dear {customer.names}, thank you for your loyalty to {shop_name}. "
                      f"We hope you enjoyed your free refill! We appreciate your business.")
            else:
                message = (f"Dear {customer.names}, congratulations! Your next refill at "
                      f"{shop_name} is FREE! Visit us soon to claim your reward. Thank you for your loyalty.")
            
            sms = SMS.objects.create(
                target_phone=customer.phone_number,
                sender=request.user,
                message_body=message
            )
            
            return Response({
                'success': True,
                'customer': customer.names,
                'is_thankyou': is_thankyou,
                'sms': SMSSerializer(sms).data
            })
        except Customers.DoesNotExist:
            return Response({
                'error': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.shortcuts import render
from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .serializers import (
    UserSerializer, 
    ChangePasswordSerializer, 
    RequestPasswordResetSerializer, 
    VerifyResetCodeSerializer, 
    ResetPasswordSerializer
)
from hamu_backend.permissions import IsDirector, IsShopAgentOrDirector
from sms.utils import send_sms
from django.conf import settings

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management.
    Directors can see and manage all users.
    Shop agents can only view/edit their own profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsShopAgentOrDirector]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['names', 'phone_number', 'email']
    ordering_fields = ['names', 'date_joined']
    filterset_fields = ['shop', 'user_class', 'is_active']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_class == 'Director':
            # Directors see all users
            return User.objects.all().select_related('shop')
        else:
            # Agents only see themselves
            return User.objects.filter(id=user.id).select_related('shop')
    
    def get_permissions(self):
        """
        Override permissions:
        - List/detail: IsShopAgentOrDirector
        - Create/Update/Delete: IsDirector
        - Password reset actions: AllowAny
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsDirector]
        elif self.action in ['request_password_reset', 'verify_reset_code', 'reset_password']:
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        """Blacklist the refresh token to logout"""
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"success": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """Change the user's password"""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Password changed successfully"},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def request_password_reset(self, request):
        """
        Request a password reset by providing a phone number.
        Sends an SMS with a reset code.
        """
        serializer = RequestPasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            result = serializer.save()
            user = result['user']
            code = result['code']
            
            # Message for SMS
            message = f"Your Hamu Water password reset code is: {code}. This code will expire in 30 minutes."
            
            # Check if SMS credentials are configured
            sms_api_key = getattr(settings, 'SMS_API_KEY', '')
            sms_email = getattr(settings, 'SMS_EMAIL', '')
            
            if sms_api_key and sms_email:
                # Send SMS with the reset code
                try:
                    messages = [{
                        "numbers": user.phone_number,
                        "message": message
                    }]
                    
                    # Send the SMS
                    send_sms(
                        api_key=sms_api_key,
                        email=sms_email,
                        messages=messages
                    )
                    
                    return Response(
                        {"detail": "Password reset code has been sent to your phone number"},
                        status=status.HTTP_200_OK
                    )
                except Exception as e:
                    # Log the error but don't reveal too much in the response
                    print(f"SMS sending error: {str(e)}")
                    return Response(
                        {"error": "Failed to send SMS. Please try again later."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                # For development environments without SMS credentials
                print(f"SMS credentials not configured. Code for {user.phone_number}: {code}")
                return Response(
                    {
                        "detail": "Password reset code generated. In production, this would be sent via SMS.",
                        "code": code  # Only include the code in development mode
                    },
                    status=status.HTTP_200_OK
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_reset_code(self, request):
        """Verify a password reset code"""
        serializer = VerifyResetCodeSerializer(data=request.data)
        
        if serializer.is_valid():
            return Response(
                {"detail": "Code is valid"},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def reset_password(self, request):
        """Reset a password with a valid code"""
        serializer = ResetPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Password has been reset successfully"},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
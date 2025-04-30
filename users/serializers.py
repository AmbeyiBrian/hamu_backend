from rest_framework import serializers
from django.contrib.auth import get_user_model
from shops.serializers import ShopSerializer
from django.contrib.auth.password_validation import validate_password
from .models import PasswordResetCode

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    shop_details = ShopSerializer(source='shop', read_only=True)
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'names', 'phone_number', 'password', 
                  'user_class', 'shop', 'shop_details', 'date_joined', 
                  'last_login', 'is_active']
        extra_kwargs = {
            'shop': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        
        if password:
            user.set_password(password)
        
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for key, value in validated_data.items():
            setattr(instance, key, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate_new_password(self, value):
        user = self.context['request'].user
        validate_password(value, user)
        return value
    
    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class RequestPasswordResetSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    
    def validate_phone_number(self, value):
        try:
            self.user = User.objects.get(phone_number=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this phone number")
        
    def save(self):
        # Generate the reset code for the user
        reset_code = PasswordResetCode.generate_code(self.user)
        return {
            'user': self.user,
            'code': reset_code.code
        }


class VerifyResetCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(required=True)
    
    def validate(self, data):
        # Find the user
        try:
            self.user = User.objects.get(phone_number=data['phone_number'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'phone_number': 'No user found with this phone number'})
        
        # Find the latest unused reset code for this user
        try:
            self.reset_code = PasswordResetCode.objects.filter(
                user=self.user,
                is_used=False
            ).latest('created_at')
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError({'code': 'No valid reset code found. Please request a new one.'})
        
        # Check if the code is correct and valid
        if self.reset_code.code != data['code']:
            raise serializers.ValidationError({'code': 'Incorrect reset code'})
        
        if not self.reset_code.is_valid():
            raise serializers.ValidationError({'code': 'Reset code has expired. Please request a new one.'})
        
        return data


class ResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
    def validate(self, data):
        # Validate the code first
        verify_serializer = VerifyResetCodeSerializer(data={
            'phone_number': data['phone_number'],
            'code': data['code']
        })
        
        if verify_serializer.is_valid():
            self.user = verify_serializer.user
            self.reset_code = verify_serializer.reset_code
            
            # Validate the new password
            try:
                validate_password(data['new_password'], self.user)
            except Exception as e:
                raise serializers.ValidationError({'new_password': list(e)})
                
            return data
        else:
            raise serializers.ValidationError(verify_serializer.errors)
    
    def save(self):
        # Set the new password
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
        
        # Mark the code as used
        self.reset_code.mark_as_used()
        
        return self.user
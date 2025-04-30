from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin # Added PermissionsMixin
from shops.models import Shops
import random
from datetime import datetime, timedelta

# --- accountsManager ---
class AccountsManager(BaseUserManager): # Renamed to PascalCase
    def create_user(self, phone_number, names, user_class, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Users must have a phone number')
        if not names:
            raise ValueError('Users must have names')

        # Normalize phone number if needed here
        user = self.model(
            phone_number=phone_number,
            names=names,
            user_class=user_class,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, names, password=None, **extra_fields):
        # Superusers don't necessarily need a business 'user_class' like Agent/Director
        # Set flags directly. Assign a default shop if necessary or handle permissions differently.
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_class', Users.UserClass.DIRECTOR) # Default to Director if needed
        # Removed setting user_class='Administrator' as it wasn't a defined choice
        # If superusers MUST have a class, add 'Admin' to UserClass choices or assign 'Director'.
        # extra_fields.setdefault('user_class', Users.UserClass.DIRECTOR) # Example if needed

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Create user without explicitly setting user_class unless required by logic
        user = self.create_user(
            phone_number=phone_number,
            names=names,
            password=password,
            user_class=extra_fields.pop('user_class', 'Director'), # Pass user_class only if provided
             **extra_fields
        )
        return user


# --- Users Model ---
# Added PermissionsMixin for standard Django permissions handling
class Users(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for Agents and Directors.
    """
    class UserClass(models.TextChoices):
        AGENT = 'Agent', 'Agent'
        DIRECTOR = 'Director', 'Director'
        # Add ADMIN if superusers should have this role explicitly
        # ADMIN = 'Admin', 'Administrator'

    names = models.CharField(max_length=50, verbose_name='Full Names') # Changed verbose_name
    phone_number = models.CharField(max_length=15, unique=True)
    # Use TextChoices for user_class
    user_class = models.CharField(
        max_length=20,
        choices=UserClass.choices,
        null=True, # Allow null for superusers if they don't fit Agent/Director role
        blank=True
    )
    # Use PROTECT or SET_NULL based on requirements if a shop is deleted
    shop = models.ForeignKey(Shops, on_delete=models.PROTECT, null=True, blank=True, related_name='staff') # Allow users not assigned to a shop initially?
    # Consider removing pass_reset_code and using Django's built-in password reset mechanism
    # pass_reset_code = models.IntegerField(default=10001)

    date_joined = models.DateTimeField(verbose_name='Date joined', auto_now_add=True) # Use auto_now_add
    last_login = models.DateTimeField(verbose_name='Last login', auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text='Designates whether the user can log into the admin site.') # Standard Django field
    is_superuser = models.BooleanField(default=False) # Standard Django field

    objects = AccountsManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['names'] # user_class might not be required if superusers don't have one

    def __str__(self):
        return f"{self.names} ({self.phone_number})"

    # has_perm and has_module_perms are handled by PermissionsMixin if using standard Django permissions
    # def has_perm(self, perm, obj=None):
    #     "Does the user have a specific permission?"
    #     # Simplest possible answer: Yes, always for admins/superusers
    #     return self.is_superuser or self.is_staff

    # def has_module_perms(self, app_label):
    #     "Does the user have permissions to view the app `app_label`?"
    #     # Simplest possible answer: Yes, always for admins/superusers
    #     return True

    class Meta:
        verbose_name_plural = 'Users'
        ordering = ['names']


# --- Password Reset Model ---
class PasswordResetCode(models.Model):
    """
    Model to store password reset codes sent via SMS
    """
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='reset_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    @classmethod
    def generate_code(cls, user, expiry_minutes=30):
        """Generate a new 6-digit code and save it"""
        # Invalidate any existing codes for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Generate a new random 6-digit code
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Calculate expiry time
        expires_at = datetime.now() + timedelta(minutes=expiry_minutes)
        
        # Create and save the new code
        reset_code = cls(
            user=user,
            code=code,
            expires_at=expires_at
        )
        reset_code.save()
        
        return reset_code
    
    def is_valid(self):
        """Check if the code is still valid (not expired, not used)"""
        now = datetime.now()
        return not self.is_used and now < self.expires_at.replace(tzinfo=None)
    
    def mark_as_used(self):
        """Mark this code as used"""
        self.is_used = True
        self.save()
    
    class Meta:
        verbose_name = 'Password Reset Code'
        verbose_name_plural = 'Password Reset Codes'
        ordering = ['-created_at']
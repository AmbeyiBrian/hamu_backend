from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils import timezone
from decimal import Decimal
import uuid
import logging
from datetime import timedelta

# Setup logging - separate log files for errors and full logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('migration')

# Create error-only logger
error_logger = logging.getLogger('migration_errors')
error_logger.setLevel(logging.WARNING)
error_handler = logging.FileHandler("migration_errors.txt")
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
error_logger.addHandler(error_handler)
error_logger.propagate = False  # Prevent duplicate logs

class Command(BaseCommand):
    help = 'Migrate data from version 1 database to version 2 schema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run in test mode (no actual database changes)',
        )
        parser.add_argument(
            '--modules',
            type=str,
            help='Comma-separated list of modules to migrate (e.g., users,shops,packages)',
        ) 

    def handle(self, *args, **options):
        test_mode = options.get('test', False)
        selected_modules = options.get('modules', '').split(',') if options.get('modules') else None
        if test_mode:
            self.stdout.write(self.style.WARNING('Running in TEST mode - no actual database changes will be made'))
          # Configure which modules to include in the migration
        modules = {
            'sales': self.migrate_sales,
            'packages': self.migrate_packages,
            'users': self.migrate_users,
            'shops': self.migrate_shops,
            'customers': self.migrate_customers,
            'refills': self.migrate_refills,
            'credits': self.migrate_credits,
            'expenses': self.migrate_expenses,
            'meter_readings': self.migrate_meter_readings,
            'stock': self.migrate_stock,
            # 'sms': self.migrate_sms,
        }
        
        # Determine which modules to run
        modules_to_run = {}
        if selected_modules:
            for module in selected_modules:
                if module.strip() in modules:
                    modules_to_run[module.strip()] = modules[module.strip()]
                else:
                    self.stdout.write(self.style.ERROR(f"Unknown module: {module}"))
        else:
            modules_to_run = modules
        
        # Run each migration function
        for name, func in modules_to_run.items():
            self.stdout.write(self.style.NOTICE(f"Migrating {name}..."))
            try:
                if test_mode:
                    with transaction.atomic():
                        func()
                        # Since we're in test mode, roll back all changes
                        transaction.set_rollback(True)
                        self.stdout.write(self.style.SUCCESS(f"Test migration of {name} would succeed"))
                else:
                    with transaction.atomic():
                        func()
                        self.stdout.write(self.style.SUCCESS(f"Successfully migrated {name}"))
            except Exception as e:
                logger.exception(f"Error migrating {name}")
                self.stdout.write(self.style.ERROR(f"Failed to migrate {name}: {str(e)}"))    
    
    def fetch_data(self, table_name):
        """Fetch data from version 1 database"""
        with connections['old_db'].cursor() as cursor:
            # Quote the table name to preserve case sensitivity
            try:
                cursor.execute(f'SELECT * FROM "{table_name}"')
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            except Exception as e:
                # If quoted version fails, try unquoted as a fallback
                self.stdout.write(self.style.WARNING(f"First attempt to fetch {table_name} failed: {str(e)}"))
                try:
                    cursor.execute(f"SELECT * FROM {table_name}")
                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                except Exception as e2:
                    self.stdout.write(self.style.ERROR(f"Could not fetch data for {table_name}: {str(e2)}"))
                    raise
    
    def migrate_users(self):
        """Migrate Users and create PasswordResetCode records"""
        from users.models import Users
        from django.contrib.auth.hashers import make_password
        
        # This assumes you've created the PasswordResetCode model in your users app
        try:
            from users.models import PasswordResetCode
        except ImportError:
            logger.warning("PasswordResetCode model not found. Skipping password reset migration.")
            PasswordResetCode = None
        
        old_users = self.fetch_data('users_users')
        logger.info(f"Found {len(old_users)} users to migrate")
        
        for old_user in old_users:
            # Check if user already exists
            if Users.objects.filter(id=old_user['id']).exists():
                logger.info(f"User {old_user['names']} already exists - updating")
                user = Users.objects.get(id=old_user['id'])
            else:
                logger.info(f"Creating new user {old_user['names']}")
                user = Users(id=old_user['id'])
            
            # Map fields
            user.password = old_user['password']  # Assuming password hashes are compatible
            user.names = old_user['names']
            user.phone_number = old_user['phone_number']
            user.user_class = old_user['user_class']
            user.shop_id = old_user['shop_id']
            user.date_joined = old_user['date_joined']
            user.last_login = old_user['last_login']
            
            # Map is_admin to appropriate field(s)
            is_admin = old_user.get('is_admin', False)
            user.is_active = old_user.get('is_active', True)
            user.is_staff = is_admin
            user.is_superuser = is_admin
            
            user.save()
            logger.info(f"Saved user {user.names}")
            
            # Migrate password reset code if applicable
            if PasswordResetCode is not None and old_user.get('pass_reset_code'):
                PasswordResetCode.objects.create(
                    user=user,
                    code=str(old_user['pass_reset_code']),
                    created_at=timezone.now(),
                    expires_at=timezone.now() + timedelta(days=1),
                    is_used=False
                )
                logger.info(f"Created password reset code for {user.names}")
    
    def migrate_shops(self):
        """Migrate Shops table"""
        from shops.models import Shops
        
        old_shops = self.fetch_data('shops_shops')
        logger.info(f"Found {len(old_shops)} shops to migrate")
        
        for old_shop in old_shops:
            # Check if shop already exists
            if Shops.objects.filter(id=old_shop['id']).exists():
                logger.info(f"Shop {old_shop['shopName']} already exists - skipping")
                continue
                
            shop = Shops(
                id=old_shop['id'],
                shopName=old_shop['shopName'],
                freeRefillInterval=old_shop['freeRefillInterval'],
                phone_number=old_shop['phone_number']
            )
            shop.save()
            logger.info(f"Migrated shop {shop.shopName}")
    
    def migrate_customers(self):
        """Migrate Customers table"""
        from customers.models import Customers
        
        old_customers = self.fetch_data('customers_customers')
        logger.info(f"Found {len(old_customers)} customers to migrate")
        
        for old_customer in old_customers:
            # Check if customer already exists by shop and phone number
            if Customers.objects.filter(
                shop_id=old_customer['shop_id'],
                phone_number=old_customer['phone_number']
            ).exists():
                logger.info(f"Customer {old_customer['names']} already exists - skipping")
                continue
                
            customer = Customers(
                shop_id=old_customer['shop_id'],
                names=old_customer['names'],
                phone_number=old_customer['phone_number'],
                apartment_name=old_customer['apartment_name'],
                room_number=old_customer['room_number'],
                date_registered=old_customer.get('date', timezone.now())  # Field was renamed
            )
            customer.save()
            logger.info(f"Migrated customer {customer.names}")
    
    def migrate_packages(self):
        """Migrate Packages table"""
        from packages.models import Packages
        from decimal import Decimal, InvalidOperation
        
        old_packages = self.fetch_data('packages_packages')
        logger.info(f"Found {len(old_packages)} packages to migrate")
        
        for old_package in old_packages:
            # Convert water amount string to decimal
            water_amount_str = old_package.get('waterAmount', '0')
            try:
                # Extract numeric part from string (e.g. '20L' -> '20')
                water_amount = Decimal(''.join(c for c in water_amount_str if c.isdigit() or c == '.'))
            except InvalidOperation:
                water_amount = Decimal('0')
                logger.warning(f"Could not convert water amount '{water_amount_str}' to decimal, using 0")
            
            # Check if package already exists
            if Packages.objects.filter(id=old_package['id']).exists():
                logger.info(f"Package {old_package['description']} already exists - updating")
                package = Packages.objects.get(id=old_package['id'])
            else:
                logger.info(f"Creating package {old_package['description']}")
                package = Packages(id=old_package['id'])
            package.shop_id = old_package['shop_id']
            package.sale_type = old_package.get('saleType', '')  # Field was renamed
              # Set default bottle_type to 'DISPOSABLE' if it's empty
            bottle_type = old_package.get('bottleType', '')
            
            # Convert to uppercase and map to valid choices
            if not bottle_type or bottle_type.strip() == '':
                bottle_type = 'DISPOSABLE'
                logger.info(f"Setting default bottle_type='DISPOSABLE' for package {old_package['id']}")
            else:
                # Map common variations to valid choices
                bottle_type = bottle_type.strip().upper()
                
                # Map specific variations if needed
                if bottle_type == 'DISPOSABLE' or 'DISPOSABLE' in bottle_type:
                    bottle_type = 'DISPOSABLE'
                elif bottle_type == 'HARD' or 'HARD' in bottle_type:
                    bottle_type = 'HARD'
                elif bottle_type == 'REFILL' or 'REFILL' in bottle_type:
                    bottle_type = 'REFILL'
                elif 'LOYAL' in bottle_type and 'MBURU' in bottle_type:
                    bottle_type = 'LOYAL_CUSTOMER_MBURU'
                elif 'LOYAL' in bottle_type:
                    bottle_type = 'LOYAL_CUSTOMER'
                elif bottle_type == 'DIRECTOR' or 'DIRECTOR' in bottle_type:
                    bottle_type = 'DIRECTOR'
                elif bottle_type == 'BUNDLE' or 'BUNDLE' in bottle_type:
                    bottle_type = 'BUNDLE'
                else:
                    # Default to DISPOSABLE if not recognized
                    bottle_type = 'DISPOSABLE'
                    logger.warning(f"Unrecognized bottle_type '{old_package.get('bottleType', '')}' for package {old_package['id']} - defaulting to 'DISPOSABLE'")
                
                logger.info(f"Mapped bottle_type from '{old_package.get('bottleType', '')}' to '{bottle_type}' for package {old_package['id']}")
            
            package.bottle_type = bottle_type
            package.water_amount_label = water_amount
            package.description = old_package['description']
            package.price = Decimal(old_package['price'])  # Convert int to decimal
            package.date_updated = old_package.get('dateUpdated', timezone.now())  # Field was renamed
            package.created_at = old_package.get('dateUpdated', timezone.now())  # Use existing date or now
            
            package.save()
            logger.info(f"Migrated package {package.description}")    
    def migrate_sales(self):
        """Migrate Sales table"""
        from sales.models import Sales
        from customers.models import Customers
        from packages.models import Packages
        from decimal import Decimal
        
        old_sales = self.fetch_data('sales_sales')
        logger.info(f"Found {len(old_sales)} sales to migrate")
        
        for old_sale in old_sales:
            # Check if ID is valid (must be a number)
            try:
                sale_id = int(old_sale['id'])
            except (ValueError, TypeError):
                logger.error(f"Invalid sale ID: {old_sale['id']} - skipping this record")
                continue
                
            # Skip if already migrated
            if Sales.objects.filter(id=sale_id).exists():
                logger.info(f"Sale ID {sale_id} already exists - skipping")
                continue
                
            # Find the matching package
            package = None
            package_name = old_sale.get('package', '').strip().upper()
            water_amount = old_sale.get('waterAmount', 0)
            shop_id = old_sale['shop_id']
              # Try to find packages for this shop with sale_type='SALE' only
            packages = Packages.objects.filter(shop_id=shop_id, sale_type='SALE', )
            logger.info(f"Found {len(packages)} 'SALE' type packages for shop ID {shop_id} to match against")
            
            # Method 1: Try to find an exact match based on package_name
            # Since package_name is description+bottle_type in the old DB
            if package_name and packages:
                for pkg in packages:
                    # Create a combined string similar to how it would be in the old DB
                    combined_pkg_name = f"{pkg.description} {pkg.bottle_type}".strip().upper()
                    if package_name == combined_pkg_name:
                        package = pkg
                        logger.info(f"Found exact package match for sale ID {old_sale['id']}: {pkg.description} {pkg.bottle_type}")
                        break
            
            # Method 2: Try finding by partial match if exact match failed
            if not package and package_name and packages:
                for pkg in packages:
                    combined_pkg_name = f"{pkg.description} {pkg.bottle_type}".strip().upper()
                    if package_name in combined_pkg_name or combined_pkg_name in package_name:
                        package = pkg
                        logger.info(f"Found partial package match for sale ID {old_sale['id']}: {package_name} -> {pkg.description} {pkg.bottle_type}")
                        break
                       
            # Method 3: Try matching by water amount if previous methods failed
            if not package and packages:
                for pkg in packages:
                    if str(water_amount) in pkg.description or str(water_amount) in str(pkg.water_amount_label):
                        package = pkg
                        logger.info(f"Found package by water amount for sale ID {old_sale['id']}: {water_amount} -> {pkg.description}")
                        break
            
            # Method 4: Fallback to first available package
            if not package:                
                error_msg = f"Could not find matching package for sale ID {old_sale['id']} - using first available"
                logger.warning(error_msg)
                error_logger.warning(error_msg)
                package = Packages.objects.filter(shop_id=shop_id).first()
                if not package:
                    error_msg = f"No packages found for shop ID {shop_id} - skipping sale {old_sale['id']}"
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    continue
              # Make sure customer_id is a valid integer            # If customer_id is None, create a sale without a customer
            customer_id = None
            
            if old_sale.get('customer_id'):
                try:
                    customer_id = int(old_sale['customer_id'])
                    
                    # Check if the customer exists
                    if not Customers.objects.filter(id=customer_id).exists():
                        logger.warning(f"Customer ID {customer_id} does not exist - trying to find by phone number")
                        
                        # Customer ID might actually be a phone number - try to find the customer by phone
                        phone_number = str(old_sale['customer_id'])
                        matching_customers = Customers.objects.filter(phone_number=phone_number, shop_id=shop_id)
                        
                        if matching_customers.exists():
                            customer_id = matching_customers.first().id
                            logger.info(f"Found customer by phone number {phone_number} -> ID {customer_id}")
                        else:
                            # Customer not found but we will proceed without a customer
                            customer_id = None
                            logger.info(f"No customer found for ID/phone {old_sale['customer_id']} - creating sale without customer")
                except (ValueError, TypeError):
                    # Customer ID is not a valid integer, so it might be a phone number
                    phone_number = str(old_sale['customer_id'])
                    matching_customers = Customers.objects.filter(phone_number=phone_number, shop_id=shop_id)
                    
                    if matching_customers.exists():
                        customer_id = matching_customers.first().id
                        logger.info(f"Found customer by phone number {phone_number} -> ID {customer_id}")
                    else:
                        # Customer not found but we will proceed without a customer
                        customer_id = None
                        logger.info(f"No customer found for phone {phone_number} - creating sale without customer")
            else:
                # No customer_id provided in the original sale - this is normal
                logger.info(f"No customer specified for sale ID {old_sale['id']} - creating sale without customer")
            
            sale = Sales(
                id=old_sale['id'],
                customer_id=customer_id,  # Use the validated/resolved customer ID
                shop_id=old_sale['shop_id'],
                package=package,
                quantity=old_sale['quantity'],
                payment_mode=old_sale.get('paymentMode', ''),  # Field was renamed
                cost=Decimal(old_sale['cost']),  # Convert int to decimal
                delivered=old_sale['delivered'],
                sold_at=old_sale.get('dateSold', timezone.now()),  # Field was renamed
                agent_name=old_sale.get('agent_name', '')
            )
            sale.save()
            logger.info(f"Migrated sale ID {sale.id}")    
    def migrate_refills(self):
        """Migrate Refills table"""
        from refills.models import Refills
        from customers.models import Customers
        from packages.models import Packages
        from decimal import Decimal, InvalidOperation
        
        old_refills = self.fetch_data('refills_refills')
        logger.info(f"Found {len(old_refills)} refills to migrate")
        
        for old_refill in old_refills:
            # Check if ID is valid (must be a number)
            try:
                refill_id = int(old_refill['id'])
            except (ValueError, TypeError):
                error_msg = f"Invalid refill ID: {old_refill['id']} - skipping this record"
                logger.error(error_msg)
                error_logger.error(error_msg)
                continue
                
            # Skip if already migrated
            if Refills.objects.filter(id=refill_id).exists():
                logger.info(f"Refill ID {refill_id} already exists - skipping")
                continue
                
            # Verify customer exists - for refills, customer is required
            if not old_refill.get('customer_id'):
                error_msg = f"Missing customer ID for refill ID {refill_id} - skipping refill"
                logger.error(error_msg)
                error_logger.error(error_msg)
                continue
                  # Treat customer_id as a string (phone number) and find matching customer
            phone_number = str(old_refill.get('customer_id', '')).strip()
            shop_id = old_refill['shop_id']
            
            # First, try finding customer by phone number
            matching_customers = Customers.objects.filter(phone_number=phone_number, shop_id=shop_id)
            
            if matching_customers.exists():
                customer = matching_customers.first()
                customer_id = customer.id
                logger.info(f"Found customer for refill ID {refill_id} by phone number {phone_number} -> ID {customer_id}")
            else:
                # If that fails, try to interpret it as an ID directly
                try:
                    customer_id = int(phone_number)
                    if Customers.objects.filter(id=customer_id).exists():
                        logger.info(f"Found customer for refill ID {refill_id} by direct ID {customer_id}")
                    else:
                        error_msg = f"Cannot find customer with phone or ID {phone_number} for refill ID {refill_id} - skipping refill"
                        logger.error(error_msg)
                        error_logger.error(error_msg)
                        continue
                except (ValueError, TypeError):
                    # Neither a valid phone number nor a valid ID
                    error_msg = f"Cannot find customer with phone {phone_number} for refill ID {refill_id} - skipping refill"
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    continue
                      # Find the matching package by description only - specifically filter by REFILL sale_type
            package = None
            package_name = old_refill.get('package', '').strip().upper()
            shop_id = old_refill['shop_id']
            
            # Try to find packages for this shop with sale_type='REFILL'
            packages = Packages.objects.filter(shop_id=shop_id, sale_type='REFILL')
            logger.info(f"Found {len(packages)} 'REFILL' type packages for shop ID {shop_id} to match against")
            
            # Method 1: Try to find an exact match based on description only
            if package_name and packages:
                for pkg in packages:
                    pkg_description = pkg.description.strip().upper()
                    if package_name == pkg_description:
                        package = pkg
                        logger.info(f"Found exact package match for refill ID {refill_id}: {pkg.description}")
                        break
            
            # Method 2: Try finding by partial match if exact match failed
            if not package and package_name and packages:
                for pkg in packages:
                    pkg_description = pkg.description.strip().upper()
                    if package_name in pkg_description or pkg_description in package_name:
                        package = pkg
                        logger.info(f"Found partial package match for refill ID {refill_id}: {package_name} -> {pkg.description}")
                        break
            
            # Method 3: Last resort - use any refill package
            if not package:
                error_msg = f"Could not find matching package for refill ID {refill_id} - using first available REFILL package"
                logger.warning(error_msg)
                error_logger.warning(error_msg)
                package = Packages.objects.filter(shop_id=shop_id, sale_type='REFILL').first()
                
                # If no REFILL packages, try any package
                if not package:
                    package = Packages.objects.filter(shop_id=shop_id).first()
                    if not package:
                        error_msg = f"No packages found for shop ID {shop_id} - skipping refill {refill_id}"
                        logger.error(error_msg)
                        error_logger.error(error_msg)
                        continue
              # Handle free refills logic
            try:
                number_of_free = int(old_refill.get('number_of_free', 0))
            except (ValueError, TypeError):
                number_of_free = 0
                logger.warning(f"Invalid number_of_free value for refill ID {refill_id} - using 0")
            
            try:
                quantity = int(old_refill.get('quantity', 1))
                if quantity < 1:
                    quantity = 1
                    logger.warning(f"Invalid quantity value for refill ID {refill_id} - using 1")
            except (ValueError, TypeError):
                quantity = 1
                logger.warning(f"Invalid quantity value for refill ID {refill_id} - using 1")
                
            is_free = False
            is_partially_free = False
            free_quantity = 0
            paid_quantity = quantity
            
            if number_of_free > 0:
                if number_of_free >= quantity:
                    is_free = True
                    free_quantity = quantity
                    paid_quantity = 0
                    logger.info(f"Refill ID {refill_id} is completely free ({quantity} bottles)")
                else:
                    is_partially_free = True
                    free_quantity = number_of_free
                    paid_quantity = quantity - number_of_free
                    logger.info(f"Refill ID {refill_id} is partially free ({free_quantity} free, {paid_quantity} paid)")
            
            # Convert cost to decimal 
            try:
                cost = Decimal(old_refill.get('cost', 0))
            except (ValueError, TypeError, InvalidOperation):
                cost = Decimal('0')
                logger.warning(f"Invalid cost value for refill ID {refill_id} - using 0")
            
            # Get delivered status (0 or 1)
            try:
                delivered = int(old_refill.get('delivered', 0))
                if delivered not in [0, 1]:
                    delivered = 0
            except (ValueError, TypeError):
                delivered = 0
                
            refill = Refills(
                id=refill_id,
                customer_id=customer_id,  # Using the validated customer ID
                shop_id=old_refill['shop_id'],
                package=package,
                quantity=quantity,
                payment_mode=old_refill.get('paymentMode', ''),  # Field was renamed
                cost=cost,
                is_free=is_free,
                is_partially_free=is_partially_free,
                free_quantity=free_quantity,
                paid_quantity=paid_quantity,
                loyalty_refill_count=0,  # Initialize new field
                delivered=delivered,
                created_at=old_refill.get('date', timezone.now()),  # Field was renamed
                agent_name=old_refill.get('agent_name', '')
            )
            
            refill.save()
            logger.info(f"Migrated refill ID {refill.id}")
            
            # Increment success counter for summary report
            if not hasattr(self, 'refills_migrated'):
                self.refills_migrated = 0
            self.refills_migrated += 1
    def migrate_credits(self):
        """Migrate Credits table"""
        from credits.models import Credits
        from customers.models import Customers
        from decimal import Decimal, InvalidOperation
        
        old_credits = self.fetch_data('credits_credits')
        logger.info(f"Found {len(old_credits)} credits to migrate")
        
        for old_credit in old_credits:
            # Check if ID is valid (must be a number)
            try:
                credit_id = int(old_credit['id'])
            except (ValueError, TypeError):
                error_msg = f"Invalid credit ID: {old_credit['id']} - skipping this record"
                logger.error(error_msg)
                error_logger.error(error_msg)
                continue
                
            # Skip if already migrated
            if Credits.objects.filter(id=credit_id).exists():
                logger.info(f"Credit ID {credit_id} already exists - skipping")
                continue
                
            # Verify customer exists - for credits, customer is required
            if not old_credit.get('customer_id'):
                error_msg = f"Missing customer ID for credit ID {credit_id} - skipping credit"
                logger.error(error_msg)
                error_logger.error(error_msg)
                continue
                
            # Treat customer_id as a phone number and find matching customer
            phone_number = str(old_credit.get('customer_id', '')).strip()
            shop_id = old_credit['shop_id']
            
            # First, try finding customer by phone number
            matching_customers = Customers.objects.filter(phone_number=phone_number, shop_id=shop_id)
            
            if matching_customers.exists():
                customer = matching_customers.first()
                customer_id = customer.id
                logger.info(f"Found customer for credit ID {credit_id} by phone number {phone_number} -> ID {customer_id}")
            else:
                # If that fails, try to interpret it as an ID directly
                try:
                    customer_id = int(phone_number)
                    if Customers.objects.filter(id=customer_id).exists():
                        logger.info(f"Found customer for credit ID {credit_id} by direct ID {customer_id}")
                    else:
                        error_msg = f"Cannot find customer with phone or ID {phone_number} for credit ID {credit_id} - skipping credit"
                        logger.error(error_msg)
                        error_logger.error(error_msg)
                        continue
                except (ValueError, TypeError):
                    # Neither a valid phone number nor a valid ID
                    error_msg = f"Cannot find customer with phone {phone_number} for credit ID {credit_id} - skipping credit"
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    continue
            
            # Convert money_paid to decimal
            try:
                money_paid = Decimal(old_credit.get('money_paid', 0))
            except (ValueError, TypeError, InvalidOperation):
                money_paid = Decimal('0')
                logger.warning(f"Invalid money_paid value for credit ID {credit_id} - using 0")
            
            # Create the credit record
            credit = Credits(
                id=credit_id,
                customer_id=customer_id,  # Using the validated/resolved customer ID
                shop_id=old_credit['shop_id'],
                money_paid=money_paid,
                payment_mode=old_credit.get('payment_mode', ''),
                payment_date=old_credit.get('date', timezone.now()),  # Field was renamed
                agent_name=old_credit.get('agent', ''),  # Field was renamed
                created_at=old_credit.get('date', timezone.now()),
                modified_at=old_credit.get('date', timezone.now())
            )
            credit.save()
            logger.info(f"Migrated credit ID {credit.id}")
            
            # Increment success counter for summary report
            if not hasattr(self, 'credits_migrated'):
                self.credits_migrated = 0
            self.credits_migrated += 1
    
    def migrate_expenses(self):
        """Migrate Expenses table"""
        from expenses.models import Expenses
        from decimal import Decimal
        
        old_expenses = self.fetch_data('expenses_expenses')
        logger.info(f"Found {len(old_expenses)} expenses to migrate")
        
        for old_expense in old_expenses:
            # Skip if already migrated
            if Expenses.objects.filter(id=old_expense['id']).exists():
                logger.info(f"Expense ID {old_expense['id']} already exists - skipping")
                continue
                
            expense = Expenses(
                id=old_expense['id'],
                shop_id=old_expense['shop_id'],
                description=old_expense['description'],
                cost=Decimal(old_expense.get('cost', 0)),
                # Skip receipt if not available in old data
                agent_name=old_expense['agent_name'],  # Default value
                created_at=old_expense['dateTime']  # Default to now since field may not exist in v1
            )
            expense.save()
            logger.info(f"Migrated expense ID {expense.id}")        
            
    def migrate_meter_readings(self):
        """Migrate MeterReading table"""
        from meter_readings.models import MeterReading
        from django.db.utils import IntegrityError
        from django.db import transaction
        
        # First, fetch and prepare meter readings from the old database
        # This avoids making queries after an error might occur
        old_readings = []
        
        # Try different methods to access the table with special handling for case sensitivity
        # Use a separate connection and transaction for fetching data
        try:
            with connections['old_db'].cursor() as cursor:
                try:
                    # Try with quotes which preserves case in PostgreSQL
                    cursor.execute('SELECT * FROM "metreReading_meterreading"')
                    columns = [col[0] for col in cursor.description]
                    old_readings = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    logger.info(f"Successfully fetched meter readings with quoted table name")
                except Exception as e1:
                    logger.warning(f"Failed to fetch meter readings with quoted name: {str(e1)}")
                    try:
                        # Try without quotes (might work in some database configurations)
                        cursor.execute('SELECT * FROM metreReading_meterreading')
                        columns = [col[0] for col in cursor.description]
                        old_readings = [dict(zip(columns, row)) for row in cursor.fetchall()]
                        logger.info(f"Successfully fetched meter readings with unquoted table name")
                    except Exception as e2:
                        # Last resort - try fetching all table names to see what's actually there
                        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                        tables = [row[0] for row in cursor.fetchall()]
                        meter_tables = [t for t in tables if 'meter' in t.lower() or 'reading' in t.lower()]
                        logger.warning(f"Available meter-related tables: {meter_tables}")
                        
                        if meter_tables:
                            # Try the first matching table
                            cursor.execute(f'SELECT * FROM "{meter_tables[0]}"')
                            columns = [col[0] for col in cursor.description]
                            old_readings = [dict(zip(columns, row)) for row in cursor.fetchall()]
                            logger.info(f"Used fallback table {meter_tables[0]}")
                        else:
                            logger.error("No meter-related tables found!")
                            return
            
            if not old_readings:
                logger.error("Could not fetch any meter readings data")
                return
                
            logger.info(f"Found {len(old_readings)} meter readings to migrate")
            
            # Create a set of existing reading IDs to avoid querying during migration
            existing_ids = set()
            with transaction.atomic():
                existing_ids = set(MeterReading.objects.values_list('id', flat=True))
            logger.info(f"Found {len(existing_ids)} existing meter readings in the database")
            
            # Create a set of unique constraints to check for duplicates
            existing_constraints = set()
            with transaction.atomic():
                existing_readings = MeterReading.objects.values('shop_id', 'reading_date', 'reading_type')
                for reading in existing_readings:
                    key = (reading['shop_id'], reading['reading_date'], reading['reading_type'])
                    existing_constraints.add(key)
            logger.info(f"Found {len(existing_constraints)} unique reading constraints in the database")
              # Process each meter reading in a separate transaction for safety
            success_count = 0
            failure_count = 0
            skipped_count = 0
            
            # Write detailed pre-migration analysis to log file
            logger.info("====== PRE-MIGRATION ANALYSIS =====")
            shop_reading_counts = {}
            date_distribution = {}
            
            for reading in old_readings:
                shop_id = reading['shop_id']
                date_time = reading.get('date', timezone.now())
                reading_date = date_time.date() if hasattr(date_time, 'date') else timezone.now().date()
                reading_type = reading.get('reading_type', 'unknown')
                
                # Count by shop
                if shop_id not in shop_reading_counts:
                    shop_reading_counts[shop_id] = 0
                shop_reading_counts[shop_id] += 1
                
                # Count by date
                date_str = str(reading_date)
                if date_str not in date_distribution:
                    date_distribution[date_str] = 0
                date_distribution[date_str] += 1
            
            logger.info(f"Readings by shop: {shop_reading_counts}")
            logger.info(f"Readings by date: {date_distribution}")
            logger.info("================================")
            
            for old_reading in old_readings:
                try:
                    with transaction.atomic():
                        # Skip if already migrated
                        if old_reading['id'] in existing_ids:
                            logger.info(f"Reading ID {old_reading['id']} already exists - skipping")
                            skipped_count += 1
                            continue
                        
                        # Split date and time if they were stored together
                        date_time = old_reading.get('date', timezone.now())
                        shop_id = old_reading['shop_id']
                        reading_type = old_reading.get('reading_type', 'unknown')
                        reading_date = date_time.date() if hasattr(date_time, 'date') else timezone.now().date()
                        reading_time = date_time.time() if hasattr(date_time, 'time') else timezone.now().time()
                          # Check for unique constraint violation before saving
                        constraint_key = (shop_id, reading_date, reading_type)
                        if constraint_key in existing_constraints:
                            # Handle duplicate by modifying the date slightly to make it unique
                            # Keep track of how many duplicates we've seen for this date
                            logger.warning(f"Duplicate reading found for shop {shop_id} on {reading_date} of type {reading_type} - modifying to make unique")
                            
                            # Create a unique ID for this reading by adding a small time offset
                            # Instead of changing to a completely different date, add a tiny offset to the original date
                            duplicate_found = False
                            
                            # Try date offsets from -15 days to +15 days from original reading date
                            for offset in range(-15, 16):
                                if offset == 0:  # Skip the original date which we know conflicts
                                    continue
                                    
                                # Calculate new date based on the ORIGINAL reading date, not today's date
                                new_date = (reading_date + timedelta(days=offset))
                                new_key = (shop_id, new_date, reading_type)
                                
                                if new_key not in existing_constraints:
                                    reading_date = new_date
                                    logger.info(f"Modified reading date from {old_reading.get('date').date() if hasattr(old_reading.get('date'), 'date') else 'unknown'} to {reading_date} (offset {offset} days) to avoid unique constraint violation")
                                    duplicate_found = True
                                    break
                            
                            if not duplicate_found:
                                # Try more desperate measures - change the reading type slightly
                                modified_type = f"{reading_type} (ID:{old_reading['id']})"
                                new_key = (shop_id, reading_date, modified_type)
                                if new_key not in existing_constraints:
                                    reading_type = modified_type
                                    logger.info(f"Modified reading type to '{reading_type}' to avoid unique constraint violation")
                                else:
                                    # Last resort - skip this reading
                                    logger.error(f"Cannot find unique combination for reading ID {old_reading['id']} - skipping")
                                    failure_count += 1
                                    continue
                          # Override auto_now_add fields by directly creating the model without auto_now_add
                        # This requires a specialized approach to bypass the auto_now_add constraint
                        reading = MeterReading(
                            id=old_reading['id'],
                            shop_id=shop_id,
                            agent_name=old_reading.get('agent_name', 'System Migration'),
                            value=float(old_reading.get('value', 0)),
                            # Skip meter_photo if not available in old data
                            reading_type=reading_type,
                        )
                        
                        # Bypass auto_now_add for reading_date and reading_time
                        reading.reading_date = reading_date  # Use the original date
                        reading.reading_time = reading_time  # Use the original time
                        
                        reading.save()
                        
                        # Update our tracking sets with the new reading
                        existing_ids.add(old_reading['id'])
                        existing_constraints.add((shop_id, reading_date, reading_type))
                        
                        logger.info(f"Migrated meter reading ID {reading.id}")
                        success_count += 1
                
                except IntegrityError as e:
                    # Catch and log any integrity errors
                    error_msg = f"IntegrityError for reading ID {old_reading['id']}: {str(e)}"
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    failure_count += 1
                
                except Exception as e:
                    # Catch and log any other exceptions
                    error_msg = f"Failed to save meter reading ID {old_reading['id']}: {str(e)}"
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    failure_count += 1
            
            logger.info(f"Meter readings migration summary: {success_count} migrated, {skipped_count} skipped, {failure_count} failed")
            
        except Exception as e:
            logger.exception(f"Error in meter readings migration: {str(e)}")
            error_logger.exception(f"Error in meter readings migration: {str(e)}")
            raise
    def migrate_stock(self):
        """Migrate Stock data to new StockItem and StockLog models"""
        from stock.models import StockItem, StockLog
        
        # Step 1: First migrate StockItem records from the old StockItem table
        try:
            old_stock_items_def = self.fetch_data('stock_stockitem')
            logger.info(f"Found {len(old_stock_items_def)} StockItem definitions to migrate")
            
            # Create a mapping of old item definitions to new StockItem objects
            item_mapping = {}  # Will store {(shop_id, item, type): stock_item_id}
            
            for old_item_def in old_stock_items_def:
                # Get necessary fields
                shop_id = old_item_def.get('shop_id')
                item_name = old_item_def.get('item', '').strip()
                item_type = old_item_def.get('type', '').strip()
                director = old_item_def.get('director', 'System Migration')
                
                if not item_name:
                    logger.warning(f"StockItem with ID {old_item_def.get('id')} has empty name - skipping")
                    continue
                
                # Map old item names to the new enum values
                mapped_item_name = self.map_stock_item_name(item_name)
                mapped_item_type = self.map_stock_item_type(item_name, item_type)
                
                # Skip if already migrated (check by shop, name, and type)
                existing_items = StockItem.objects.filter(
                    shop_id=shop_id, 
                    item_name=mapped_item_name,
                    item_type=mapped_item_type
                )
                
                if existing_items.exists():
                    stock_item = existing_items.first()
                    logger.info(f"Stock item {mapped_item_name}/{mapped_item_type} already exists for shop {shop_id} - using existing")
                else:
                    # Create new StockItem
                    stock_item = StockItem(
                        shop_id=shop_id,
                        item_name=mapped_item_name,
                        item_type=mapped_item_type,
                        unit='piece',  # Default unit
                        threshold=200,  # Default threshold
                        reorder_point=300,  # Default reorder point
                        created_at=old_item_def.get('date', timezone.now())
                    )
                    stock_item.save()
                    logger.info(f"Created stock item {mapped_item_name}/{mapped_item_type} for shop {shop_id}")
                
                # Store mapping for use with stock logs
                item_mapping[(shop_id, item_name, item_type)] = stock_item.id
            
            # Step 2: Migrate Stock records to StockLog entries
            old_stock_logs = self.fetch_data('stock_stock')
            logger.info(f"Found {len(old_stock_logs)} Stock records to migrate to StockLog")
            
            for old_stock in old_stock_logs:
                shop_id = old_stock.get('shop_id')
                item_name = old_stock.get('item', '').strip()
                bottle_type = old_stock.get('bottleType', '').strip()
                quantity = old_stock.get('quantity', 0)
                director = old_stock.get('director', 'Unknown')
                log_date = old_stock.get('date', timezone.now())
                
                # Try to find matching StockItem
                stock_item = None
                
                # First try exact match
                key = (shop_id, item_name, bottle_type)
                if key in item_mapping:
                    stock_item_id = item_mapping[key]
                    stock_item = StockItem.objects.get(id=stock_item_id)
                else:
                    # Try finding by mapped values
                    mapped_item_name = self.map_stock_item_name(item_name)
                    mapped_item_type = self.map_stock_item_type(item_name, bottle_type)
                    
                    matching_items = StockItem.objects.filter(
                        shop_id=shop_id,
                        item_name=mapped_item_name,
                        item_type=mapped_item_type
                    )
                    
                    if matching_items.exists():
                        stock_item = matching_items.first()
                    else:
                        # Create missing stock item as fallback
                        logger.warning(f"Creating missing StockItem for {mapped_item_name}/{mapped_item_type} in shop {shop_id}")
                        stock_item = StockItem(
                            shop_id=shop_id,
                            item_name=mapped_item_name,
                            item_type=mapped_item_type,
                            unit='piece',
                            threshold=200,
                            reorder_point=300,
                            created_at=log_date
                        )
                        stock_item.save()
                
                # Create StockLog entry
                if stock_item and quantity:
                    # Check if this specific log entry already exists
                    existing_log = StockLog.objects.filter(
                        stock_item=stock_item,
                        shop_id=shop_id,
                        quantity_change=quantity,
                        director_name=director,
                        log_date=log_date
                    )
                    
                    if not existing_log.exists():
                        StockLog.objects.create(
                            stock_item=stock_item,
                            quantity_change=quantity,  # Initial quantity is a positive addition
                            notes=f'Migrated from version 1: {item_name} {bottle_type}',
                            shop_id=shop_id,
                            director_name=director,
                            log_date=log_date
                        )
                        logger.info(f"Created stock log for {stock_item.item_name}/{stock_item.item_type} with quantity {quantity}")
                
            logger.info(f"Successfully migrated {len(old_stock_items_def)} StockItems and {len(old_stock_logs)} StockLogs")
            
        except Exception as e:
            logger.exception("Error migrating stock data")
            raise
    
    def map_stock_item_name(self, old_name):
        """Map old stock item names to new enum values"""
        old_name = old_name.strip().lower()
        if 'bottle' in old_name:
            return 'Bottle'
        elif 'cap' in old_name:
            return 'Cap'
        elif 'label' in old_name:
            return 'Label'
        elif 'shrink' in old_name or 'wrap' in old_name:
            return 'Shrink Wrap'
        elif 'bundle' in old_name:
            return 'Water Bundle'
        else:
            return old_name.title()  # Default to title-cased version of the name
    
    def map_stock_item_type(self, item_name, item_type):
        """Map old stock item types to new enum values"""
        item_name = item_name.strip().lower()
        item_type = item_type.strip()
        
        # For bottles, use the bottleType field
        if 'bottle' in item_name:
            if not item_type:  # If type is empty, try to extract from name
                if '0.5' in item_name or '0,5' in item_name or '500ml' in item_name:
                    return '0.5L'
                elif '1l' in item_name or '1 l' in item_name:
                    return '1L'
                elif '1.5' in item_name or '1,5' in item_name:
                    return '1.5L'
                elif '2l' in item_name or '2 l' in item_name:
                    return '2L'
                elif '5l' in item_name or '5 l' in item_name:
                    return '5L'
                elif '10l' in item_name or '10 l' in item_name:
                    return '10L'
                elif '20l' in item_name or '20 l' in item_name:
                    if 'hard' in item_name:
                        return '20L Hard'
                    return '20L'
                else:
                    return '20L'  # Default
            else:
                # Map bottle type based on standard sizes
                item_type = item_type.lower()
                if '0.5' in item_type or '0,5' in item_type or '500ml' in item_type:
                    return '0.5L'
                elif '1l' in item_type or '1 l' in item_type:
                    return '1L'
                elif '1.5' in item_type or '1,5' in item_type:
                    return '1.5L'
                elif '2l' in item_type or '2 l' in item_type:
                    return '2L'
                elif '5l' in item_type or '5 l' in item_type:
                    return '5L'
                elif '10l' in item_type or '10 l' in item_type:
                    return '10L'
                elif '20l' in item_type or '20 l' in item_type:
                    if 'hard' in item_type:
                        return '20L Hard'
                    return '20L'
                else:
                    return item_type  # Use as-is if no mapping found
        
        # For caps, labels, shrink wraps, etc.
        elif 'cap' in item_name:
            return '10/20L'  # Default cap type
        elif 'label' in item_name:
            if '5l' in item_name or '5 l' in item_name or '5l' in item_type:
                return '5L'
            elif '10l' in item_name or '10 l' in item_name or '10l' in item_type:
                return '10L'
            elif '20l' in item_name or '20 l' in item_name or '20l' in item_type:
                return '20L'
            else:
                return '20L'  # Default
        elif 'shrink' in item_name or 'wrap' in item_name or 'bundle' in item_name:
            # Try to extract bundle sizes from type or name
            if '12x1' in item_name or '12x1' in item_type:
                return '12x1L'
            elif '24x0.5' in item_name or '24x0.5' in item_type or '24x0,5' in item_name or '24x0,5' in item_type:
                return '24x0.5L'
            elif '8x1.5' in item_name or '8x1.5' in item_type or '8x1,5' in item_name or '8x1,5' in item_type:
                return '8x1.5L'
            else:
                return '12x1L'  # Default
        else:
            # If no specific mapping, return original type or default
            return item_type if item_type else 'Default'
    
    def migrate_sms(self):
        """Migrate SMS table"""
        from sms.models import SMS
        from users.models import Users
        
        old_sms = self.fetch_data('sms_sms')
        logger.info(f"Found {len(old_sms)} SMS to migrate")
        
        for old_message in old_sms:
            # Skip if already migrated
            if SMS.objects.filter(id=old_message['id']).exists():
                logger.info(f"SMS ID {old_message['id']} already exists - skipping")
                continue
            
            # Try to find user by old sender name
            sender_name = old_message.get('sender', '')
            user = None
            
            if sender_name:
                users = Users.objects.filter(names__icontains=sender_name)
                if users.exists():
                    user = users.first()
                    
            if not user:
                # Use the first admin user as a fallback
                user = Users.objects.filter(is_staff=True).first()
            
            if not user:
                logger.warning(f"No valid sender found for SMS ID {old_message['id']} - skipping")
                continue
                
            sms = SMS(
                id=old_message['id'],
                target_phone=old_message.get('target', ''),  # Field was renamed
                sent_at=old_message.get('date', timezone.now()),  # Field was renamed
                sender=user,  # Using the found user or admin
                message_body=old_message.get('message', '')  # Field was renamed
            )
            sms.save()
            logger.info(f"Migrated SMS ID {sms.id}")
    
    def preserve_date_fields(self, model_instance, old_data, field_mappings):
        """
        Helper method to preserve original date/time fields from source database
        even for models with auto_now_add=True or auto_now=True
        
        Args:
            model_instance: The Django model instance to update
            old_data: Dictionary of data from the old database
            field_mappings: Dictionary mapping old field names to new field names
                Example: {'date': 'created_at', 'timestamp': 'modified_at'}
        """
        # First save the model to get a database record
        model_instance.save()
        
        # Check if we need to update date fields
        update_needed = False
        updates = {}
        
        for old_field, new_field in field_mappings.items():
            if old_field in old_data and old_data[old_field] is not None:
                updates[new_field] = old_data[old_field]
                update_needed = True
        
        if update_needed:
            # Use the model's manager to directly update the database
            # This bypasses the auto_now_add and auto_now behavior
            model_instance._meta.model.objects.filter(pk=model_instance.pk).update(**updates)
            
            # Log the date preservation
            logger.info(f"Preserved original dates for {model_instance._meta.model.__name__} (ID: {model_instance.pk}): {updates}")
            
            # Refresh the instance from the database to get the updated fields
            model_instance.refresh_from_db()
            
        return model_instance

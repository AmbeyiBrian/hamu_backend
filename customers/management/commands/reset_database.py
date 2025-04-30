from django.core.management.base import BaseCommand
from django.db import transaction
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reset_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('reset')

class Command(BaseCommand):
    help = 'Reset all database tables (delete all records) before running migration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all data',
        )
        parser.add_argument(
            '--modules',
            type=str,
            help='Comma-separated list of modules to reset (e.g., users,shops,packages)',
        )

    def handle(self, *args, **options):
        if not options.get('confirm'):
            self.stdout.write(self.style.ERROR('This command will delete ALL DATA. Add --confirm to proceed.'))
            return

        selected_modules = options.get('modules', '').split(',') if options.get('modules') else None

        # Define the module reset functions
        modules = {
            'sales': self.reset_sales,
            'packages': self.reset_packages,
            'users': self.reset_users,
            'shops': self.reset_shops,
            'customers': self.reset_customers,
            'refills': self.reset_refills,
            'credits': self.reset_credits,
            'expenses': self.reset_expenses,
            'meter_readings': self.reset_meter_readings,
            'stock': self.reset_stock,
            'sms': self.reset_sms,
        }
        
        # Determine which modules to reset
        modules_to_run = {}
        if selected_modules:
            for module in selected_modules:
                module = module.strip()
                if module in modules:
                    modules_to_run[module] = modules[module]
                else:
                    self.stdout.write(self.style.ERROR(f"Unknown module: {module}"))
        else:
            modules_to_run = modules
        
        # Run each reset function
        for name, func in modules_to_run.items():
            self.stdout.write(self.style.NOTICE(f"Resetting {name}..."))
            try:
                with transaction.atomic():
                    before_count = func(count_only=True)
                    func()
                    self.stdout.write(self.style.SUCCESS(f"Successfully reset {name} ({before_count} records deleted)"))
            except Exception as e:
                logger.exception(f"Error resetting {name}")
                self.stdout.write(self.style.ERROR(f"Failed to reset {name}: {str(e)}"))

    def reset_users(self, count_only=False):
        from users.models import Users
        try:
            count = Users.objects.count()
            if count_only:
                return count
            
            # Don't delete superusers to avoid getting locked out
            deleted = Users.objects.exclude(is_superuser=True).delete()
            logger.info(f"Deleted {deleted[0]} user records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting users: {str(e)}")
            raise

    def reset_shops(self, count_only=False):
        from shops.models import Shops
        try:
            count = Shops.objects.count()
            if count_only:
                return count
            
            deleted = Shops.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} shop records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting shops: {str(e)}")
            raise
    
    def reset_customers(self, count_only=False):
        from customers.models import Customers
        try:
            count = Customers.objects.count()
            if count_only:
                return count
            
            deleted = Customers.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} customer records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting customers: {str(e)}")
            raise
            
    def reset_packages(self, count_only=False):
        from packages.models import Packages
        try:
            count = Packages.objects.count()
            if count_only:
                return count
            
            deleted = Packages.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} package records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting packages: {str(e)}")
            raise
            
    def reset_sales(self, count_only=False):
        from sales.models import Sales
        try:
            count = Sales.objects.count()
            if count_only:
                return count
            
            deleted = Sales.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} sales records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting sales: {str(e)}")
            raise
            
    def reset_refills(self, count_only=False):
        from refills.models import Refills
        try:
            count = Refills.objects.count()
            if count_only:
                return count
            
            deleted = Refills.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} refill records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting refills: {str(e)}")
            raise
            
    def reset_credits(self, count_only=False):
        from credits.models import Credits
        try:
            count = Credits.objects.count()
            if count_only:
                return count
            
            deleted = Credits.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} credits records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting credits: {str(e)}")
            raise
            
    def reset_expenses(self, count_only=False):
        from expenses.models import Expenses
        try:
            count = Expenses.objects.count()
            if count_only:
                return count
            
            deleted = Expenses.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} expenses records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting expenses: {str(e)}")
            raise
            
    def reset_meter_readings(self, count_only=False):
        from meter_readings.models import MeterReading
        try:
            count = MeterReading.objects.count()
            if count_only:
                return count
            
            deleted = MeterReading.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} meter reading records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting meter readings: {str(e)}")
            raise
            
    def reset_stock(self, count_only=False):
        from stock.models import StockItem, StockLog
        try:
            log_count = StockLog.objects.count()
            item_count = StockItem.objects.count()
            if count_only:
                return log_count + item_count
            
            # Delete logs first to avoid foreign key constraint errors
            deleted_logs = StockLog.objects.all().delete()
            deleted_items = StockItem.objects.all().delete()
            
            logger.info(f"Deleted {deleted_logs[0]} stock log records and {deleted_items[0]} stock item records")
            return deleted_logs[0] + deleted_items[0]
        except Exception as e:
            logger.error(f"Error while resetting stock: {str(e)}")
            raise
            
    def reset_sms(self, count_only=False):
        from sms.models import SMS
        try:
            count = SMS.objects.count()
            if count_only:
                return count
            
            deleted = SMS.objects.all().delete()
            logger.info(f"Deleted {deleted[0]} SMS records")
            return deleted[0]
        except Exception as e:
            logger.error(f"Error while resetting SMS: {str(e)}")
            raise

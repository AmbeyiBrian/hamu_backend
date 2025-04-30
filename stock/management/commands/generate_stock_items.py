from django.core.management.base import BaseCommand
from django.db import transaction
from shops.models import Shops
from stock.models import StockItem


class Command(BaseCommand):
    help = 'Generate stock items for all shops using predefined choices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if items already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        shops = Shops.objects.all()
        
        if not shops.exists():
            self.stdout.write(self.style.ERROR('No shops found. Please create shops first.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {shops.count()} shops. Starting stock item generation...'))
        
        # Get all item types from the model
        bottle_types = list(StockItem.BottleType.values)
        cap_types = list(StockItem.CapType.values)
        label_types = list(StockItem.LabelType.values)
        shrink_wrap_types = list(StockItem.ShrinkWrapType.values)
        water_bundle_types = list(StockItem.WaterBundleType.values)
        
        total_created = 0
        total_existing = 0
        
        with transaction.atomic():
            # Process each shop
            for shop in shops:
                self.stdout.write(f'Processing shop: {shop.shopName}')
                
                # Generate Bottle items
                for bottle_type in bottle_types:
                    existing = StockItem.objects.filter(
                        shop=shop,
                        item_name=StockItem.ItemName.BOTTLE,
                        item_type=bottle_type
                    ).exists()
                    
                    if not existing or force:
                        if existing and force:
                            # Skip if already exists and not forcing
                            self.stdout.write(f'  - Bottle {bottle_type} already exists, skipping')
                            total_existing += 1
                            continue
                            
                        # Create the stock item
                        StockItem.objects.create(
                            shop=shop,
                            item_name=StockItem.ItemName.BOTTLE,
                            item_type=bottle_type,
                            unit='piece'
                        )
                        self.stdout.write(f'  + Created Bottle {bottle_type}')
                        total_created += 1
                    else:
                        total_existing += 1
                
                # Generate Cap items
                for cap_type in cap_types:
                    existing = StockItem.objects.filter(
                        shop=shop,
                        item_name=StockItem.ItemName.CAP,
                        item_type=cap_type
                    ).exists()
                    
                    if not existing or force:
                        if existing and force:
                            # Skip if already exists and not forcing
                            self.stdout.write(f'  - Cap {cap_type} already exists, skipping')
                            total_existing += 1
                            continue
                            
                        # Create the stock item
                        StockItem.objects.create(
                            shop=shop,
                            item_name=StockItem.ItemName.CAP,
                            item_type=cap_type,
                            unit='piece'
                        )
                        self.stdout.write(f'  + Created Cap {cap_type}')
                        total_created += 1
                    else:
                        total_existing += 1
                
                # Generate Label items
                for label_type in label_types:
                    existing = StockItem.objects.filter(
                        shop=shop,
                        item_name=StockItem.ItemName.LABEL,
                        item_type=label_type
                    ).exists()
                    
                    if not existing or force:
                        if existing and force:
                            # Skip if already exists and not forcing
                            self.stdout.write(f'  - Label {label_type} already exists, skipping')
                            total_existing += 1
                            continue
                            
                        # Create the stock item
                        StockItem.objects.create(
                            shop=shop,
                            item_name=StockItem.ItemName.LABEL,
                            item_type=label_type,
                            unit='piece'
                        )
                        self.stdout.write(f'  + Created Label {label_type}')
                        total_created += 1
                    else:
                        total_existing += 1
                
                # Generate Shrink Wrap items
                for shrink_wrap_type in shrink_wrap_types:
                    existing = StockItem.objects.filter(
                        shop=shop,
                        item_name=StockItem.ItemName.SHRINK_WRAP,
                        item_type=shrink_wrap_type
                    ).exists()
                    
                    if not existing or force:
                        if existing and force:
                            # Skip if already exists and not forcing
                            self.stdout.write(f'  - Shrink Wrap {shrink_wrap_type} already exists, skipping')
                            total_existing += 1
                            continue
                            
                        # Create the stock item
                        StockItem.objects.create(
                            shop=shop,
                            item_name=StockItem.ItemName.SHRINK_WRAP,
                            item_type=shrink_wrap_type,
                            unit='piece'
                        )
                        self.stdout.write(f'  + Created Shrink Wrap {shrink_wrap_type}')
                        total_created += 1
                    else:
                        total_existing += 1
                
                # Generate Water Bundle items
                for water_bundle_type in water_bundle_types:
                    existing = StockItem.objects.filter(
                        shop=shop,
                        item_name=StockItem.ItemName.WATER_BUNDLE,
                        item_type=water_bundle_type
                    ).exists()
                    
                    if not existing or force:
                        if existing and force:
                            # Skip if already exists and not forcing
                            self.stdout.write(f'  - Water Bundle {water_bundle_type} already exists, skipping')
                            total_existing += 1
                            continue
                            
                        # Create the stock item
                        StockItem.objects.create(
                            shop=shop,
                            item_name=StockItem.ItemName.WATER_BUNDLE,
                            item_type=water_bundle_type,
                            unit='bundle'
                        )
                        self.stdout.write(f'  + Created Water Bundle {water_bundle_type}')
                        total_created += 1
                    else:
                        total_existing += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Stock item generation complete! Created {total_created} items, skipped {total_existing} existing items.'
        ))
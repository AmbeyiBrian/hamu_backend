from django.db.models import Sum, F, Q, Case, When, Value, IntegerField
from django.db import connection, transaction
from .models import StockItem, StockLog
from sales.models import Sales
from refills.models import Refills


class StockCalculationService:
    """
    Service class for calculating stock levels based on various events (sales, refills)
    without directly coupling these events to stock management.
    """
    
    @staticmethod
    def get_current_stock_level(stock_item):
        """Calculate current stock level for a specific StockItem"""
        quantity = StockLog.objects.filter(stock_item=stock_item).aggregate(
            total=Sum('quantity_change')
        )['total'] or 0
        return quantity
    
    @staticmethod
    def get_current_stock_by_shop(shop_id):
        """Get all stock items and their current levels for a specific shop"""
        items = StockItem.objects.filter(shop_id=shop_id)
        result = []
        
        for item in items:
            quantity = StockCalculationService.get_current_stock_level(item)
            result.append({
                'id': item.id,
                'item_name': item.item_name,
                'item_type': item.item_type,
                'unit': item.unit,
                'current_quantity': quantity
            })
        
        return result
    
    @staticmethod
    def calculate_stock_impact_from_sales(start_date=None, end_date=None, shop_id=None):
        """
        Calculate how sales have impacted stock levels.
        Returns a dictionary of stock items and quantities used.
        """
        # Start with an empty query
        sales_query = Sales.objects.all()
        
        # Apply filters if provided
        if start_date:
            sales_query = sales_query.filter(sold_at__gte=start_date)
        if end_date:
            sales_query = sales_query.filter(sold_at__lte=end_date)
        if shop_id:
            sales_query = sales_query.filter(shop_id=shop_id)
            
        # Group results by package and get total quantities
        # This will need a raw query since the logic to map from package to stock item is complex
        impact = {}
        
        # Process each sale and determine stock impact
        for sale in sales_query:
            package_name = sale.package.package_name
            quantity = sale.quantity
            
            # Get bottle info from package name (e.g., "20L Bottle", "12x1L Pack")
            # For bottle sales (e.g., "20L Bottle")
            if "x" not in package_name.lower() and "bottle" in package_name.lower():
                bottle_type = package_name.replace("Bottle", "").strip()
                
                # Add to impact dictionary
                key = f"Bottle: {bottle_type}"
                impact[key] = impact.get(key, 0) - quantity  # Negative for reduction
                
            # For shrink-wrapped bundles (e.g., "12x1L Pack", "24x500ml Pack")
            elif "x" in package_name.lower() and ("pack" in package_name.lower() or "bundle" in package_name.lower()):
                # Extract the format like "12x1L"
                format_part = package_name.split()[0]  # e.g., "12x1L"
                # Add to impact dictionary
                key = f"Shrink Wrap: {format_part}"
                impact[key] = impact.get(key, 0) - quantity  # Negative for reduction
                
        return impact
    
    @staticmethod
    def calculate_stock_impact_from_refills(start_date=None, end_date=None, shop_id=None):
        """
        Calculate how refills have impacted stock levels.
        Returns a dictionary of stock items and quantities used.
        """
        # Similar to sales, but for refills
        refills_query = Refills.objects.all()
        
        # Apply filters if provided
        if start_date:
            refills_query = refills_query.filter(created_at__gte=start_date)
        if end_date:
            refills_query = refills_query.filter(created_at__lte=end_date)
        if shop_id:
            refills_query = refills_query.filter(shop_id=shop_id)
        
        # Process refills to determine stock impact
        impact = {}
        
        for refill in refills_query:
            # Since refills use water, they don't directly reduce physical inventory
            # But they can be tracked for reporting purposes
            package_name = refill.package.package_name
            water_amount = refill.package.water_amount
            quantity = refill.quantity
            
            # Track water usage
            key = f"Water: {water_amount}L"
            impact[key] = impact.get(key, 0) - (water_amount * quantity)  # Negative for usage
            
        return impact
    
    @staticmethod
    def reconcile_stocklogs_with_events():
        """
        Compare explicit StockLog entries with calculated impacts from sales and refills.
        Useful for auditing and finding discrepancies.
        """
        # This would compare the sum of StockLog entries with the calculated 
        # impact from sales and refills to identify any discrepancies
        # Implementation depends on specific business requirements
        pass
    
    @staticmethod
    @transaction.atomic
    def process_water_bundle_creation(stock_log):
        """
        Process water bundle creation by deducting corresponding bottles and shrink wraps.
        This method is called when a positive stock log entry is created for a water bundle.
        
        Returns a list of created stock log entries for the deducted items.
        """
        # Only process if this is a water bundle addition
        if stock_log.stock_item.item_name != 'Water Bundle' or stock_log.quantity_change <= 0:
            return []
            
        created_logs = []
        shop = stock_log.shop
        bundle_type = stock_log.stock_item.item_type
        bundle_quantity = stock_log.quantity_change
        director_name = stock_log.director_name
        notes = f"Auto-deducted for Water Bundle creation: {bundle_type} x{bundle_quantity}"
        
        # Parse the water bundle format to determine number of bottles and size
        if bundle_type == '12x1L':
            bottle_quantity = 12 * bundle_quantity
            bottle_type = '1L'
            shrink_wrap_type = '12x1L'
        elif bundle_type == '24x0.5L':
            bottle_quantity = 24 * bundle_quantity
            bottle_type = '0.5L'
            shrink_wrap_type = '24x0.5L'
        elif bundle_type == '8x1.5L':
            bottle_quantity = 8 * bundle_quantity
            bottle_type = '1.5L'
            shrink_wrap_type = '8x1.5L'
        else:
            # Unknown bundle type
            return []
            
        try:
            # Find the corresponding bottle stock item
            bottle_stock_item = StockItem.objects.get(
                shop=shop,
                item_name='Bottle',
                item_type=bottle_type
            )
            
            # Find the corresponding shrink wrap stock item
            shrink_wrap_stock_item = StockItem.objects.get(
                shop=shop,
                item_name='Shrink Wrap',
                item_type=shrink_wrap_type
            )
            
            # Check if there's enough stock to deduct
            bottle_stock = StockCalculationService.get_current_stock_level(bottle_stock_item)
            shrink_wrap_stock = StockCalculationService.get_current_stock_level(shrink_wrap_stock_item)
            
            if bottle_stock < bottle_quantity:
                raise ValueError(f"Not enough {bottle_type} bottles in stock. Required: {bottle_quantity}, Available: {bottle_stock}")
                
            if shrink_wrap_stock < bundle_quantity:
                raise ValueError(f"Not enough {shrink_wrap_type} shrink wraps in stock. Required: {bundle_quantity}, Available: {shrink_wrap_stock}")
            
            # Create deduction for bottles
            bottle_log = StockLog.objects.create(
                stock_item=bottle_stock_item,
                quantity_change=-bottle_quantity,  # Negative for deduction
                notes=notes,
                shop=shop,
                director_name=director_name
            )
            created_logs.append(bottle_log)
            
            # Create deduction for shrink wrap
            shrink_wrap_log = StockLog.objects.create(
                stock_item=shrink_wrap_stock_item,
                quantity_change=-bundle_quantity,  # Negative for deduction
                notes=notes,
                shop=shop,
                director_name=director_name
            )
            created_logs.append(shrink_wrap_log)
            
            return created_logs
            
        except StockItem.DoesNotExist as e:
            # Required stock items don't exist
            raise ValueError(f"Cannot process water bundle: {str(e)}")
        except Exception as e:
            # Other errors
            raise ValueError(f"Error processing water bundle: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def deduct_caps_and_labels_for_refill(refill, agent_name):
        """
        Deduct caps and labels from inventory when a refill is recorded.
        - Deducts caps of type '10/20L' for 10L and 20L refills
        - Deducts labels matching the refill's water amount (5L, 10L, or 20L)
        - Allows negative stock values if physical stock is present but not recorded
        
        Returns a list of created stock log entries for the deducted items.
        """
        created_logs = []
        shop = refill.shop
        package = refill.package
        quantity = refill.quantity
        notes = f"Auto-deducted for Refill: {package.water_amount_label}L x{quantity}"
        
        # Only process refills with water amount labels that match our caps/labels
        water_amount = package.water_amount_label
        
        try:
            # Deduct caps for 10L and 20L refills
            if water_amount in [10, 20]:
                try:
                    # Find the corresponding cap stock item
                    cap_stock_item = StockItem.objects.get(
                        shop=shop,
                        item_name='Cap',
                        item_type='10/20L'
                    )
                    
                    # Create deduction for caps - no validation check for available stock
                    cap_log = StockLog.objects.create(
                        stock_item=cap_stock_item,
                        quantity_change=-quantity,  # Negative for deduction
                        notes=notes,
                        shop=shop,
                        director_name=agent_name
                    )
                    created_logs.append(cap_log)
                    
                except StockItem.DoesNotExist:
                    # Log or handle if caps aren't tracked for this shop
                    pass
            
            # Deduct labels matching the water amount (5L, 10L, 20L)
            # Convert integer water_amount to string format for matching with label types
            label_type = f"{water_amount}L"
            
            # Only deduct labels if water amount is a standard size (5L, 10L, 20L)
            if water_amount in [5, 10, 20]:
                try:
                    # Find the corresponding label stock item
                    label_stock_item = StockItem.objects.get(
                        shop=shop,
                        item_name='Label',
                        item_type=label_type
                    )
                    
                    # Create deduction for labels - no validation check for available stock
                    label_log = StockLog.objects.create(
                        stock_item=label_stock_item,
                        quantity_change=-quantity,  # Negative for deduction
                        notes=notes,
                        shop=shop,
                        director_name=agent_name
                    )
                    created_logs.append(label_log)
                    
                except StockItem.DoesNotExist:
                    # Log or handle if labels aren't tracked for this shop
                    pass
            
            return created_logs
            
        except Exception as e:
            # Handle any other errors
            raise ValueError(f"Error processing refill inventory deduction: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def deduct_stock_for_sale(sale, agent_name):
        """
        Deduct appropriate stock items when a sale is recorded.
        - For bottle sales: deducts the corresponding bottle type and label
        - For water bundles: deducts the corresponding bundle
        
        Affected items:
        - Labels (5L, 10L, 20L)
        - Bottles (0.5L, 1L, 1.5L, 2L, 5L, 10L, 20L, 20L Hard)
        - Water bundles (12x1L, 24x0.5L, 8x1.5L)
        
        Returns a list of created stock log entries for the deducted items.
        """
        created_logs = []
        shop = sale.shop
        package = sale.package
        quantity = sale.quantity
        notes = f"Auto-deducted for Sale: {package.water_amount_label}L x{quantity}"
        
        try:
            # Check if it's a bottle sale
            if package.sale_type == 'SALE' and package.bottle_type not in ['BUNDLE']:
                # Get water amount and determine bottle type
                water_amount = package.water_amount_label
                
                # Determine the bottle type string based on water amount and bottle_type
                bottle_item_type = f"{water_amount}L"
                if package.bottle_type == 'HARD' and water_amount == 20:
                    bottle_item_type = '20L Hard'
                
                try:
                    # Find the corresponding bottle stock item
                    bottle_stock_item = StockItem.objects.get(
                        shop=shop,
                        item_name='Bottle',
                        item_type=bottle_item_type
                    )
                    
                    # Create deduction for bottles
                    bottle_log = StockLog.objects.create(
                        stock_item=bottle_stock_item,
                        quantity_change=-quantity,  # Negative for deduction
                        notes=notes,
                        shop=shop,
                        director_name=agent_name
                    )
                    created_logs.append(bottle_log)
                    
                except StockItem.DoesNotExist:
                    pass
                
                # For standard bottle sizes, also deduct labels
                if water_amount in [5, 10, 20]:
                    try:
                        # Find the corresponding label stock item
                        label_type = f"{water_amount}L"
                        label_stock_item = StockItem.objects.get(
                            shop=shop,
                            item_name='Label',
                            item_type=label_type
                        )
                        
                        # Create deduction for labels
                        label_log = StockLog.objects.create(
                            stock_item=label_stock_item,
                            quantity_change=-quantity,  # Negative for deduction
                            notes=notes,
                            shop=shop,
                            director_name=agent_name
                        )
                        created_logs.append(label_log)
                        
                    except StockItem.DoesNotExist:
                        pass
                
            # Handle water bundle sales
            elif package.sale_type == 'SALE' and package.bottle_type == 'BUNDLE':
                # Get description to identify bundle type
                description = package.description.lower()
                
                # Determine the bundle type
                bundle_type = None
                if '12x1' in description:
                    bundle_type = '12x1L'
                elif '24x0.5' in description or '24x500' in description:
                    bundle_type = '24x0.5L'
                elif '8x1.5' in description:
                    bundle_type = '8x1.5L'
                
                if bundle_type:
                    try:
                        # Find the corresponding water bundle stock item
                        bundle_stock_item = StockItem.objects.get(
                            shop=shop,
                            item_name='Water Bundle',
                            item_type=bundle_type
                        )
                        
                        # Create deduction for water bundle
                        bundle_log = StockLog.objects.create(
                            stock_item=bundle_stock_item,
                            quantity_change=-quantity,  # Negative for deduction
                            notes=notes,
                            shop=shop,
                            director_name=agent_name
                        )
                        created_logs.append(bundle_log)
                        
                    except StockItem.DoesNotExist:
                        pass
            
            return created_logs
            
        except Exception as e:
            # Handle any other errors
            raise ValueError(f"Error processing sale inventory deduction: {str(e)}")
import requests
from django.conf import settings


def send_sms(api_key, email, messages):
    """
    Send SMS messages using the ujumbesms.co.ke API.
    
    Args:
        api_key (str): The API key for the SMS service
        email (str): The email registered with the SMS service
        messages (list): List of message bags containing recipient and message details
            Each message should have the format:
            {
                "message": "Your message here",
                "numbers": "2547XXXXXXXX",  # Phone number
                "sender": "HamuWater"  # Always use HamuWater
            }
    
    Returns:
        dict: The JSON response from the SMS API
    """
    url = "https://ujumbesms.co.ke/api/messaging"
    headers = {
        "x-authorization": 'OTJhNWVhNGQxY2UyMGZiMjY5ODU1ZjYzYzNiMGJj',
        "email": 'eliasrmwangi@gmail.com',
        "Content-Type": "application/json"
    }

    # Transform messages to match expected API format
    message_bags = []
    for msg in messages:
        message_bag = {
            "message_bag": {
                "numbers": msg.get("numbers", ""),
                "message": msg.get("message", ""),
                "sender": "HamuWater"
            }
        }
        message_bags.append(message_bag)

    payload = {
        "data": message_bags
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def send_batch_sms(recipients, message, api_key=None, email=None):
    """
    Send SMS to a batch of recipients, handling the 80-recipient limit
    by splitting into smaller batches if necessary.
    
    Args:
        recipients (list): List of phone numbers
        message (str): The message to send
        api_key (str): Optional API key, defaults to settings if not provided
        email (str): Optional email, defaults to settings if not provided
        
    Returns:
        list: List of API responses for each batch
    """
    # Use settings if not provided
    if not api_key:
        api_key = getattr(settings, 'SMS_API_KEY', '')
    if not email:
        email = getattr(settings, 'SMS_EMAIL', '')
    
    # Split recipients into batches of 80 as per API limit
    batch_size = 80
    recipient_batches = [recipients[i:i+batch_size] for i in range(0, len(recipients), batch_size)]
    
    responses = []
    for batch in recipient_batches:
        message_bags = []
        for phone in batch:
            # Format each message individually as per frontend implementation
            message_bag = {
                "numbers": phone,
                "message": message
            }
            message_bags.append(message_bag)
            
        response = send_sms(api_key, email, message_bags)
        responses.append(response)
    
    return responses


def send_free_refill_notification(customer, is_thankyou=False):
    """
    Send an SMS notification to a customer about their free refill.
    
    Args:
        customer: Customer model instance
        is_thankyou (bool): If True, send a thank you message for using a free refill
                           If False, notify about eligibility for next free refill
    
    Returns:
        dict: The response from the SMS API
    """
    phone_number = customer.phone_number
    shop_name = customer.shop.shopName
    
    if is_thankyou:
        message = (f"Dear {customer.names}, thank you for your loyalty to Hamu Water - {shop_name} shop. "
                   f"We hope you enjoyed your free refill! We appreciate your business.")
    else:
        message = (f"Dear {customer.names}, congratulations! Your next refill at "
                   f"{shop_name} is FREE! Visit us soon to claim your reward. Thank you for your loyalty.")
    
    return send_batch_sms([phone_number], message)


def send_free_refill_thank_you_sms(customer, free_quantity, package_type):
    """
    Send an SMS notification to a customer thanking them for their loyalty
    and informing them about the number of free refills they received.
    
    Args:
        customer: Customer model instance
        free_quantity: Number of free refills received
        package_type: Type of water package (e.g., "20L")
        
    Returns:
        dict: The response from the SMS API
    """
    phone_number = customer.phone_number
    shop_name = customer.shop.shopName
    
    # Construct message with quantity information
    quantity_text = f"{free_quantity} free {package_type} litres" if free_quantity > 1 else f"a free {package_type} litre"
    
    message = (f"Dear {customer.names}, thank you for your loyalty to Hamu Water - {shop_name}. "
               f"You have received {quantity_text} water refill! We appreciate your continued business.")
    
    return send_batch_sms([phone_number], message)


def send_shop_customers_sms(shop, message):
    """
    Send an SMS to all customers of a specific shop.
    
    Args:
        shop: Shop model instance
        message (str): The message to send
        
    Returns:
        list: List of API responses
    """
    recipients = [customer.phone_number for customer in shop.customers.all()]
    return send_batch_sms(recipients, message)


def send_credit_customers_sms(message):
    """
    Send an SMS to all customers with credits.
    
    Args:
        message (str): The message to send
        
    Returns:
        list: List of API responses
    """
    from credits.models import Credits
    from django.db.models import Count
    
    # Get customers with at least one credit payment
    customers_with_credits = Credits.objects.values('customer__phone_number').annotate(
        credit_count=Count('id')
    ).filter(credit_count__gt=0)
    
    recipients = [item['customer__phone_number'] for item in customers_with_credits]
    return send_batch_sms(recipients, message)
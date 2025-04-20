def create_notification(user, title, message, notification_type='info', link=None):
    """
    Utility function to create a new notification for a user.
    
    Args:
        user: The Users instance to create the notification for
        title: Title of the notification
        message: Content of the notification
        notification_type: Type of notification (info, success, warning, error)
        link: Optional URL to include with the notification
    
    Returns:
        The created Notification instance
    """
    from notifications.models import Notification
    
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type,
        link=link
    )
    
    return notification

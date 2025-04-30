# Hamu Backend

A Django-based REST API backend for the Hamu water management system. This system provides a comprehensive solution for managing water delivery, sales, inventory, and customer management.

## Overview

Hamu Backend is a full-featured API that powers both the Hamu Web and Mobile applications. It manages all core business logic including customer management, water refills, sales tracking, stock management, analytics, and notifications.

## Features

- **User Authentication & Management**: Secure user management system
- **Customer Management**: Track and manage customer information and history
- **Credit System**: Manage customer credits and payment tracking
- **Meter Reading Management**: Record and track water meter readings
- **Stock Management**: Inventory tracking for water bottles and related items
- **Sales Tracking**: Comprehensive sales and transaction management
- **Expense Tracking**: Record and categorize business expenses
- **Refill Management**: Track water refill operations
- **Shop Management**: Manage multiple shop locations
- **Package Management**: Configure different water package options
- **SMS Notifications**: Send automated notifications to customers
- **Analytics**: Data analysis and reporting capabilities

## Tech Stack

- **Framework**: Django
- **API**: Django REST Framework
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Authentication**: JWT (JSON Web Tokens)

## Project Structure

The project follows a Django app-based structure with modularized components:

- `analytics/`: Data analysis and reporting
- `credits/`: Customer credit management
- `customers/`: Customer information management
- `expenses/`: Business expense tracking
- `meter_readings/`: Water meter tracking
- `notifications/`: User notification system
- `packages/`: Water package configurations
- `refills/`: Water refill management
- `sales/`: Sales transaction processing
- `shops/`: Shop location management
- `sms/`: SMS messaging functionality
- `stock/`: Inventory management
- `users/`: User authentication and profiles

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AmbeyiBrian/hamu_backend.git
   cd hamu_backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

7. Access the API at http://localhost:8000/ and the admin interface at http://localhost:8000/admin/

## API Documentation

The API endpoints are organized by app functionality. Main endpoint groups include:

- `/api/users/` - User authentication and management
- `/api/customers/` - Customer management
- `/api/sales/` - Sales operations
- `/api/stock/` - Inventory management
- `/api/refills/` - Water refill operations
- `/api/credits/` - Credit management

For detailed API documentation, run the server and visit http://localhost:8000/api/docs/ (if using Django REST Swagger or drf-yasg).

## Environment Variables

The following environment variables should be configured for production:

- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (False in production)
- `ALLOWED_HOSTS` - Allowed host names
- `DATABASE_URL` - Database connection string
- `SMS_API_KEY` - API key for SMS service

## Deployment

For production deployment:

1. Set environment variables appropriately
2. Configure a production-ready database (PostgreSQL recommended)
3. Set up static files serving
4. Use a WSGI server like Gunicorn
5. Configure Nginx or similar as a reverse proxy

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is proprietary and is not licensed for public use or distribution without explicit permission.

MyShop

MyShop is a Windows desktop shop management application designed to simplify day-to-day product, inventory, category, pricing, and database management.

The application provides a practical interface for managing products and stock while keeping track of price changes and inventory movements.

Features
📦 Product Management
Add new products
Edit existing products
Delete products
View product details
Search products quickly
Search by product name, Barcode, SKU, or brand
Filter products by category
Filter low-stock products
Sort product tables

The product management interface includes fields such as product name, Barcode, SKU, category, quantity, unit, sale price, and minimum stock level.

🗂️ Category Management
Add categories
Rename categories
Delete categories
Display the number of products in each category
Assign products to categories

Categories are also available as filters throughout the product management interface.

📊 Inventory Management
View current stock levels
Identify low-stock products
Adjust stock quantities
Record the reason for manual stock adjustments
Track stock changes

The application maintains stock movement records including the previous quantity, new quantity, change amount, reason, and user responsible for the change.

💰 Price Management
View current product prices
Apply percentage-based price increases or decreases to selected products
Preview price changes before applying them
Maintain a price history
View previous and new prices
Track the percentage of each price change

The bulk pricing interface allows selected products to be updated using a percentage and provides a preview of the resulting prices.

🔎 Fast Search

The main search field supports quick product lookup and is designed to work with barcode scanners operating as keyboard/HID devices.

Supported search fields include:

Product name
Barcode
SKU
Brand
📋 Price & Stock History

MyShop keeps historical records for important changes, including:

Product price changes
Previous price
New price
Percentage change
Stock movements
Quantity before and after the movement
Change reason
Date/time of the operation

The price history interface displays the product, old price, new price, percentage change, and date.

📈 Dashboard

The main dashboard provides an overview of the shop, including:

Total number of products
Total number of categories
Low-stock count
Recently updated products
Recent price changes
Selected product information
📊 Excel Integration

The application includes Excel import/export functionality for working with product data.

This makes it possible to use existing Excel product lists and transfer product information between Excel and MyShop.

💾 Database & Backup

MyShop uses a local database for storing application data and includes database management and backup functionality.

The project is designed as a Windows desktop application, making it suitable for environments where a local database is preferred.

🔐 Authentication & Permissions

The application includes user authentication and role-based access.

Administrative operations are protected based on the logged-in user's role.

Technology Stack

MyShop is built using:

Python
PySide6 — Desktop GUI
SQLAlchemy — Database ORM
SQLite — Local database
OpenPyXL — Excel integration
PyInstaller — Windows executable packaging
Inno Setup — Windows installer
Pytest — Automated testing
Project Structure
MyShop/
│
├── app/
│   ├── database/
│   │   ├── connection.py
│   │   ├── migrations.py
│   │   └── models.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── backup_service.py
│   │   ├── database_service.py
│   │   ├── excel_service.py
│   │   ├── product_service.py
│   │   ├── stock_service.py
│   │   └── ...
│   │
│   ├── ui/
│   │   ├── dialogs.py
│   │   └── main_window.py
│   │
│   └── main.py
│
├── tests/
├── installer/
├── scripts/
│
├── requirements.txt
├── MyShop.spec
├── run.py
└── README.md

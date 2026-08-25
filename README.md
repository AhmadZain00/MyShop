# MyShop

MyShop is a Windows desktop shop management application designed to simplify day-to-day product, inventory, category, pricing, and database management.

The application provides a practical desktop interface for managing products and stock while maintaining records of price changes and inventory movements.

## Features

### Product Management

- Add new products
- Edit existing products
- Delete products
- View product details
- Search products quickly
- Search by product name, Barcode, SKU, or brand
- Filter products by category
- Filter low-stock products
- Sort product tables

Product records include information such as:

- Product name
- Barcode
- SKU
- Brand
- Category
- Quantity
- Unit
- Sale price
- Minimum stock level
- Notes

### Category Management

- Add categories
- Rename categories
- Delete categories
- Assign products to categories
- Display the number of products in each category
- Filter products by category

Categories are managed directly from the application and are integrated with product management.

### Inventory Management

MyShop provides tools for monitoring and managing inventory.

Features include:

- View current stock levels
- Identify low-stock products
- Adjust stock quantities
- Record the reason for manual stock adjustments
- Track stock movements

Stock movement records include:

- Previous quantity
- New quantity
- Quantity change
- Reason for the change
- User responsible for the operation
- Date and time

### Price Management

MyShop provides tools for managing product prices and maintaining a history of price changes.

Features include:

- View current product prices
- Apply percentage-based price increases or decreases
- Apply price changes to selected products
- Preview price changes before applying them
- Maintain price history
- View previous and new prices
- Track the percentage of each price change

### Fast Search

The main search field provides quick product lookup.

Supported search fields include:

- Product name
- Barcode
- SKU
- Brand

The search interface is designed to work with barcode scanners operating as keyboard/HID devices.

### Price and Stock History

MyShop maintains historical records for important product and inventory changes.

Price history includes:

- Product
- Previous price
- New price
- Percentage change
- Date and time

Stock history includes:

- Product
- Quantity before the movement
- Quantity after the movement
- Quantity change
- Reason
- User responsible for the operation
- Date and time

### Dashboard

The dashboard provides an overview of the shop, including:

- Total number of products
- Total number of categories
- Low-stock count
- Recently updated products
- Recent price changes
- Selected product information

### Excel Integration

MyShop includes Excel import and export functionality for working with product data.

This allows existing product lists to be transferred between Excel and MyShop.

### Database and Backup

MyShop uses a local SQLite database for application data.

The application also includes database management and backup functionality.

The local database approach makes MyShop suitable for environments where a local database is preferred and an external database server is not required.

### Authentication and Permissions

MyShop includes user authentication and role-based access.

Administrative operations are protected based on the logged-in user's role.

## Windows Application

MyShop is distributed as a Windows desktop application.

The packaged version is built as a standalone Windows executable, so end users do not need to install Python or the project's development dependencies when using the packaged application.

A Windows installer can be generated for distributing the application to end users.

## Installation

### Using the Windows Installer

For end users, the recommended installation method is the Windows installer.

1. Download the latest `MyShopSetup.exe` from the project's GitHub Releases.
2. Run the installer.
3. Follow the installation instructions.
4. Launch MyShop from the Desktop shortcut or Start Menu.

The installer creates the required application files and shortcuts.

### Running from Source

Developers can also run MyShop directly from the source code.

Requirements:

- Windows
- Python 3
- Git

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import unicodedata

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment

from sqlalchemy import select
from app.database.connection import SessionLocal
from app.database.models import Product, Category, PriceHistory, StockMovement


# ============================================================
# Official MyShop Excel columns
# ============================================================

HEADERS = [
    "اسم المنتج",
    "Barcode",
    "SKU",
    "التصنيف",
    "الماركة",
    "سعر الشراء",
    "سعر البيع",
    "الكمية",
    "الوحدة",
    "الحد الأدنى",
    "ملاحظات",
]


# ============================================================
# Text / number helpers
# ============================================================

def _text(value, default=None):
    if value is None:
        return default

    text = str(value).strip()

    return text if text else default


def _safe_decimal(value, default=Decimal("0")):
    """
    Convert Excel values to Decimal safely.

    Supports:
    - integers
    - floats
    - Decimal
    - strings
    - comma thousands separators
    - decimal comma
    - common currency symbols
    """

    if value is None:
        return default

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except Exception:
            return default

    text = str(value).strip()

    if not text:
        return default

    # Common currency/text characters
    replacements = [
        "جنيه",
        "ج.م",
        "EGP",
        "USD",
        "EUR",
        "$",
        "€",
        "£",
        "ريال",
        "ر.س",
        "درهم",
        "د.إ",
    ]

    for item in replacements:
        text = text.replace(item, "")

    text = text.strip()

    # Keep only digits, comma, dot and minus
    text = re.sub(r"[^0-9,\.\-]", "", text)

    if not text:
        return default

    # 1,250.50
    # 1.250,50
    if "," in text and "." in text:
        if text.rfind(".") > text.rfind(","):
            text = text.replace(",", "")
        else:
            text = text.replace(".", "")
            text = text.replace(",", ".")

    elif "," in text:
        parts = text.split(",")

        if len(parts) == 2 and len(parts[1]) <= 3:
            text = parts[0] + "." + parts[1]
        else:
            text = text.replace(",", "")

    try:
        return Decimal(text)

    except (InvalidOperation, ValueError):
        return default


def _safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


# ============================================================
# Header normalization
# ============================================================

def _normalize_header(value):
    if value is None:
        return ""

    text = str(value).strip().lower()

    # Remove Unicode marks
    text = unicodedata.normalize("NFKC", text)

    # Arabic normalization
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.replace("ة", "ه")

    # Remove spaces / punctuation
    text = re.sub(r"[\s_\-./\\:()]+", "", text)

    return text


# ============================================================
# Column aliases
# ============================================================

COLUMN_ALIASES = {

    "name": [
        "اسم المنتج",
        "اسم الصنف",
        "اسم السلعة",
        "المنتج",
        "الصنف",
        "السلعة",
        "اسم",
        "product name",
        "product",
        "item name",
        "item",
        "name",
        "productname",
        "itemname",
    ],

    "barcode": [
        "barcode",
        "bar code",
        "باركود",
        "بار كود",
        "كود",
        "رقم الباركود",
        "barcode number",
        "ean",
        "upc",
    ],

    "sku": [
        "sku",
        "sku code",
        "كود sku",
        "كود المنتج",
        "رمز المنتج",
        "product code",
        "item code",
    ],

    "category": [
        "التصنيف",
        "التصنيف الرئيسي",
        "القسم",
        "الفئة",
        "الفئه",
        "تصنيف",
        "category",
        "category name",
        "group",
        "department",
    ],

    "brand": [
        "الماركة",
        "العلامة التجارية",
        "العلامه التجاريه",
        "البراند",
        "ماركة",
        "brand",
        "brand name",
        "manufacturer",
    ],

    "purchase_price": [
        "سعر الشراء",
        "سعر التكلفة",
        "سعر التكلفه",
        "تكلفة الشراء",
        "تكلفه الشراء",
        "سعر التكلفه",
        "purchase price",
        "purchase",
        "cost price",
        "cost",
        "buy price",
        "buying price",
    ],

    "sale_price": [
        "سعر البيع",
        "سعر التجزئة",
        "سعر التجزئه",
        "السعر",
        "سعر",
        "price",
        "sale price",
        "selling price",
        "sellingprice",
        "retail price",
        "sales price",
    ],

    "quantity": [
        "الكمية",
        "الكميه",
        "المخزون",
        "الكمية المتاحة",
        "الكميه المتاحه",
        "qty",
        "quantity",
        "stock",
        "inventory",
        "available quantity",
    ],

    "unit": [
        "الوحدة",
        "الوحده",
        "وحدة",
        "unit",
        "unit name",
        "uom",
    ],

    "min_stock": [
        "الحد الأدنى",
        "الحد الادنى",
        "حد الطلب",
        "حد المخزون",
        "الحد",
        "minimum stock",
        "min stock",
        "minimum",
        "reorder level",
        "reorder point",
    ],

    "notes": [
        "ملاحظات",
        "ملاحظة",
        "ملاحظات المنتج",
        "notes",
        "note",
        "description",
        "details",
        "comment",
        "comments",
    ],
}


def _build_alias_map():
    result = {}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            normalized = _normalize_header(alias)

            if normalized:
                result[normalized] = field

    return result


_ALIAS_MAP = _build_alias_map()


def _detect_columns(headers):
    """
    Detect known columns regardless of:
    - language
    - order
    - missing columns
    - extra columns
    """

    mapping = {}

    for index, header in enumerate(headers):

        normalized = _normalize_header(header)

        if not normalized:
            continue

        field = _ALIAS_MAP.get(normalized)

        if field and field not in mapping:
            mapping[field] = index

    return mapping


def _has_useful_columns(mapping):
    return bool(
        mapping.get("name") is not None
        or mapping.get("sale_price") is not None
        or mapping.get("purchase_price") is not None
        or mapping.get("barcode") is not None
        or mapping.get("sku") is not None
    )


# ============================================================
# Header detection
# ============================================================

def _looks_like_header(row):

    values = []

    for value in row:
        if value is not None:
            text = str(value).strip()

            if text:
                values.append(text)

    if not values:
        return False

    mapping = _detect_columns(values)

    return _has_useful_columns(mapping)


def _find_header_row(ws, max_scan_rows=20):

    max_row = min(ws.max_row, max_scan_rows)

    for row_number in range(1, max_row + 1):

        values = list(
            ws.iter_rows(
                min_row=row_number,
                max_row=row_number,
                values_only=True,
            )
        )

        if not values:
            continue

        row = list(values[0])

        if _looks_like_header(row):

            headers = [
                str(value).strip() if value is not None else ""
                for value in row
            ]

            mapping = _detect_columns(headers)

            return row_number, headers, mapping

    return None, None, {}


# ============================================================
# Row helper
# ============================================================

def _get_value(row, mapping, field, default=None):

    index = mapping.get(field)

    if index is None:
        return default

    if index >= len(row):
        return default

    return row[index]


# ============================================================
# Template
# ============================================================

def make_template(path):

    path = Path(path)

    wb = Workbook()

    ws = wb.active
    ws.title = "products"

    ws.append(HEADERS)

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # Barcode / SKU as text
    for row in ws.iter_rows(
        min_row=2,
        max_row=5000,
        min_col=2,
        max_col=3,
    ):
        row[0].number_format = "@"
        row[1].number_format = "@"

    widths = [
        28,
        18,
        18,
        20,
        18,
        16,
        16,
        14,
        12,
        14,
        35,
    ]

    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[
            chr(64 + index)
        ].width = width

    ws.freeze_panes = "A2"

    # Instructions
    instructions = wb.create_sheet("instructions")

    instruction_rows = [
        ["تعليمات MyShop"],
        [
            "يمكن استيراد أي ملف Excel تقريبًا، حتى لو كان اسم الورقة مختلفًا."
        ],
        [
            "ترتيب الأعمدة غير مهم، ويمكن أن تكون بعض الأعمدة غير موجودة."
        ],
        [
            "يمكن استخدام أسماء أعمدة عربية أو إنجليزية."
        ],
        [
            "الأعمدة غير المعروفة سيتم تجاهلها تلقائيًا."
        ],
        [
            "اسم المنتج والسعر والكمية يمكن أن تكون غير موجودة، وسيتم استخدام قيم افتراضية."
        ],
        [
            "Barcode و SKU اختياريان."
        ],
        [
            "إذا لم توجد فئة، سيتم إنشاء المنتج بدون فئة."
        ],
    ]

    for row in instruction_rows:
        instructions.append(row)

    instructions.column_dimensions["A"].width = 100

    wb.save(path)


# ============================================================
# Export products
# ============================================================

def export_products(path):

    path = Path(path)

    wb = Workbook()

    ws = wb.active
    ws.title = "products"

    ws.append(HEADERS)

    with SessionLocal() as session:

        products = session.scalars(
            select(Product).order_by(Product.name)
        ).all()

        for product in products:

            ws.append([
                product.name,
                product.barcode,
                product.sku,
                product.category.name if product.category else "",
                product.brand,
                _safe_float(product.purchase_price),
                _safe_float(product.sale_price),
                _safe_float(product.quantity),
                product.unit,
                _safe_float(product.min_stock),
                product.notes,
            ])

    # Barcode / SKU as text
    for row in ws.iter_rows(
        min_row=2,
        min_col=2,
        max_col=3,
    ):
        row[0].number_format = "@"
        row[1].number_format = "@"

    ws.freeze_panes = "A2"

    wb.save(path)


# ============================================================
# Import products - Smart Excel importer
# ============================================================

# ============================================================
# Import products - Smart Excel importer
# ============================================================

def import_products(
    path,
    mode="update",
    progress=None,
    cancel_check=None,
):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Excel file not found: {path}"
        )

    wb = load_workbook(
        path,
        read_only=True,
        data_only=True,
    )

    try:
        # ----------------------------------------------------
        # Find the best worksheet
        #
        # Prefer "products".
        # Otherwise search for the first worksheet that
        # contains a recognizable header.
        # If no recognizable header exists, use the first
        # non-empty worksheet.
        # ----------------------------------------------------

        ws = None

        if "products" in wb.sheetnames:
            ws = wb["products"]

        else:
            # First try to find a worksheet with a recognizable header.
            for sheet_name in wb.sheetnames:
                candidate = wb[sheet_name]

                if candidate.max_row <= 0:
                    continue

                if candidate.max_column <= 0:
                    continue

                header_row_number, headers, mapping = _find_header_row(
                    candidate
                )

                if header_row_number is not None:
                    ws = candidate
                    break

            # If no recognizable header was found,
            # use the first non-empty worksheet.
            if ws is None:
                for sheet_name in wb.sheetnames:
                    candidate = wb[sheet_name]

                    if (
                        candidate.max_row > 0
                        and candidate.max_column > 0
                    ):
                        ws = candidate
                        break

        if ws is None:
            raise ValueError(
                "ملف Excel فارغ ولا يحتوي على أي ورقة بيانات."
            )

        # ----------------------------------------------------
        # Detect header
        # ----------------------------------------------------

        header_row_number, headers, mapping = _find_header_row(ws)

        # ----------------------------------------------------
        # Headerless Excel
        # ----------------------------------------------------

        if header_row_number is None:
            mapping = {
                "name": 0,
                "sale_price": 1,
                "barcode": 2,
                "sku": 3,
                "category": 4,
                "brand": 5,
                "purchase_price": 6,
                "quantity": 7,
                "unit": 8,
                "min_stock": 9,
                "notes": 10,
            }

            data_start_row = 1

        else:
            data_start_row = header_row_number + 1

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        result = {
            "added": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
            "cancelled": False,
            "errors": [],
            "warnings": [],
        }

        # ----------------------------------------------------
        # Warnings - never block import
        # ----------------------------------------------------

        if mapping.get("name") is None:
            result["warnings"].append(
                "لم يتم العثور على عمود اسم المنتج. "
                "سيتم إنشاء أسماء تلقائية عند الحاجة."
            )

        if mapping.get("sale_price") is None:
            result["warnings"].append(
                "لم يتم العثور على عمود سعر البيع. "
                "سيتم استخدام 0."
            )

        if mapping.get("quantity") is None:
            result["warnings"].append(
                "لم يتم العثور على عمود الكمية. "
                "سيتم استخدام 0."
            )

        # ----------------------------------------------------
        # Total rows
        # ----------------------------------------------------

        total = max(
            0,
            ws.max_row - data_start_row + 1,
        )

        # ----------------------------------------------------
        # Database
        # ----------------------------------------------------

        with SessionLocal() as session:
            with session.begin():

                categories = {
                    category.name: category
                    for category in session.scalars(
                        select(Category)
                    ).all()
                }

                for row_number, row in enumerate(
                    ws.iter_rows(
                        min_row=data_start_row,
                        values_only=True,
                    ),
                    start=data_start_row,
                ):

                    # ------------------------------------------------
                    # Cancellation
                    # ------------------------------------------------

                    if cancel_check and cancel_check():
                        result["cancelled"] = True
                        break

                    # ------------------------------------------------
                    # Empty row
                    # ------------------------------------------------

                    if not any(
                        value is not None
                        and str(value).strip()
                        for value in row
                    ):
                        continue

                    # ------------------------------------------------
                    # Process row independently
                    # ------------------------------------------------

                    try:
                        with session.begin_nested():

                            # ----------------------------------------
                            # Product name
                            # ----------------------------------------

                            name = _text(
                                _get_value(
                                    row,
                                    mapping,
                                    "name",
                                )
                            )

                            if not name:
                                name = f"Imported Product {row_number}"

                            # ----------------------------------------
                            # Identifiers
                            # ----------------------------------------

                            barcode = _text(
                                _get_value(
                                    row,
                                    mapping,
                                    "barcode",
                                )
                            )

                            sku = _text(
                                _get_value(
                                    row,
                                    mapping,
                                    "sku",
                                )
                            )

                            # ----------------------------------------
                            # Category
                            # ----------------------------------------

                            category_name = _text(
                                _get_value(
                                    row,
                                    mapping,
                                    "category",
                                )
                            )

                            category = None

                            if category_name:
                                category = categories.get(
                                    category_name
                                )

                                if category is None:
                                    category = Category(
                                        name=category_name
                                    )

                                    session.add(category)
                                    session.flush()

                                    categories[category_name] = category

                            # ----------------------------------------
                            # Other fields
                            # ----------------------------------------

                            brand = _text(
                                _get_value(
                                    row,
                                    mapping,
                                    "brand",
                                )
                            )

                            unit = _text(
                                _get_value(
                                    row,
                                    mapping,
                                    "unit",
                                )
                            ) or "قطعة"

                            notes = _text(
                                _get_value(
                                    row,
                                    mapping,
                                    "notes",
                                )
                            )

                            # ----------------------------------------
                            # Numbers
                            # ----------------------------------------

                            purchase_price = _safe_decimal(
                                _get_value(
                                    row,
                                    mapping,
                                    "purchase_price",
                                )
                            )

                            sale_price = _safe_decimal(
                                _get_value(
                                    row,
                                    mapping,
                                    "sale_price",
                                )
                            )

                            quantity = _safe_decimal(
                                _get_value(
                                    row,
                                    mapping,
                                    "quantity",
                                )
                            )

                            min_stock = _safe_decimal(
                                _get_value(
                                    row,
                                    mapping,
                                    "min_stock",
                                )
                            )

                            # ----------------------------------------
                            # Find existing product
                            #
                            # Barcode first, SKU second
                            # ----------------------------------------

                            product = None

                            if barcode:
                                product = session.scalar(
                                    select(Product).where(
                                        Product.barcode == barcode
                                    )
                                )

                            if product is None and sku:
                                product = session.scalar(
                                    select(Product).where(
                                        Product.sku == sku
                                    )
                                )

                            # ----------------------------------------
                            # Existing product
                            # ----------------------------------------

                            if product is not None:

                                if mode == "ignore":
                                    result["skipped"] += 1
                                    continue

                                old_price = _safe_decimal(
                                    product.sale_price
                                )

                                old_quantity = _safe_decimal(
                                    product.quantity
                                )

                                # ------------------------------------
                                # Price-only mode
                                # ------------------------------------

                                if mode == "prices":
                                    product.purchase_price = (
                                        purchase_price
                                    )

                                    product.sale_price = (
                                        sale_price
                                    )

                                # ------------------------------------
                                # Full update
                                # ------------------------------------

                                else:
                                    product.name = name

                                    # Do not erase an existing
                                    # identifier when the Excel
                                    # column is empty.
                                    if barcode:
                                        product.barcode = barcode

                                    if sku:
                                        product.sku = sku

                                    product.category = category
                                    product.brand = brand

                                    product.purchase_price = (
                                        purchase_price
                                    )

                                    product.sale_price = (
                                        sale_price
                                    )

                                    product.quantity = quantity
                                    product.unit = unit
                                    product.min_stock = min_stock
                                    product.notes = notes

                                # ------------------------------------
                                # Price history
                                # ------------------------------------

                                if sale_price != old_price:
                                    percentage = None

                                    if old_price != 0:
                                        percentage = (
                                            (
                                                sale_price
                                                - old_price
                                            )
                                            / old_price
                                        ) * 100

                                    session.add(
                                        PriceHistory(
                                            product_id=product.id,
                                            old_price=old_price,
                                            new_price=sale_price,
                                            change_percent=percentage,
                                        )
                                    )

                                # ------------------------------------
                                # Stock movement
                                # ------------------------------------

                                if (
                                    mode != "prices"
                                    and quantity != old_quantity
                                ):
                                    session.add(
                                        StockMovement(
                                            product_id=product.id,
                                            quantity_before=old_quantity,
                                            quantity_after=quantity,
                                            delta=(
                                                quantity
                                                - old_quantity
                                            ),
                                            reason="استيراد Excel",
                                        )
                                    )

                                session.flush()

                                result["updated"] += 1

                            # ----------------------------------------
                            # New product
                            # ----------------------------------------

                            else:
                                product = Product(
                                    name=name,
                                    barcode=barcode,
                                    sku=sku,
                                    category=category,
                                    brand=brand,
                                    purchase_price=purchase_price,
                                    sale_price=sale_price,
                                    quantity=quantity,
                                    unit=unit,
                                    min_stock=min_stock,
                                    notes=notes,
                                )

                                session.add(product)
                                session.flush()

                                # ------------------------------------
                                # Initial stock movement
                                # ------------------------------------

                                if quantity != 0:
                                    session.add(
                                        StockMovement(
                                            product_id=product.id,
                                            quantity_before=Decimal("0"),
                                            quantity_after=quantity,
                                            delta=quantity,
                                            reason="استيراد Excel",
                                        )
                                    )

                                result["added"] += 1

                    except Exception as exc:
                        result["failed"] += 1

                        result["errors"].append(
                            {
                                "row": row_number,
                                "error": str(exc),
                                "data": list(row),
                            }
                        )

                    # ------------------------------------------------
                    # Progress
                    # ------------------------------------------------

                    if progress:
                        percentage = int(
                            (
                                row_number
                                - data_start_row
                                + 1
                            )
                            / max(1, total)
                            * 100
                        )

                        progress(
                            min(100, max(0, percentage))
                        )

        return result

    finally:
        wb.close()

# ============================================================
# Export import errors
# ============================================================

def export_errors(path, errors):

    path = Path(path)

    wb = Workbook()

    ws = wb.active
    ws.title = "errors"

    ws.append(
        [
            "رقم الصف",
            "الخطأ",
        ]
        + HEADERS
    )

    for error in errors:

        data = error.get("data", [])

        values = list(data)

        # Ensure enough cells for HEADERS
        if len(values) < len(HEADERS):

            values.extend(
                [""] * (
                    len(HEADERS)
                    - len(values)
                )
            )

        ws.append(
            [
                error.get("row"),
                error.get("error"),
            ]
            + values[:len(HEADERS)]
        )

    wb.save(path)
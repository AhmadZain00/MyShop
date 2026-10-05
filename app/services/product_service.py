from decimal import Decimal
from sqlalchemy import select, or_, func, desc, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app.database import connection as dbconn
from app.database.models import Product, Category, PriceHistory, StockMovement

class ProductService:
    def search(self, term="", category_id=None, low_stock=False, limit=500):
        with dbconn.SessionLocal() as s:
            stmt = select(Product).options(joinedload(Product.category)).order_by(Product.name).limit(limit)
            conditions = []
            term = (term or "").strip()
            if term:
                q = f"%{term}%"
                conditions.append(or_(Product.name.like(q), Product.barcode.like(q),
                                      Product.sku.like(q), Product.brand.like(q)))
            if category_id:
                conditions.append(Product.category_id == category_id)
            if low_stock:
                conditions.append(Product.quantity <= Product.min_stock)
            if conditions:
                stmt = select(Product).options(joinedload(Product.category)).where(*conditions).order_by(Product.name).limit(limit)
            return list(s.scalars(stmt))

    def get(self, product_id):
        with dbconn.SessionLocal() as s:
            return s.get(Product, product_id)

    def add(self, data, user_id=None):
        with dbconn.SessionLocal.begin() as s:
            p = Product(**data)
            s.add(p)
            try:
                s.flush()
            except IntegrityError as exc:
                raise ValueError("Barcode أو SKU موجود بالفعل.") from exc
            if p.quantity:
                s.add(StockMovement(product_id=p.id, quantity_before=0,
                                    quantity_after=p.quantity, delta=p.quantity,
                                    reason="إضافة منتج", changed_by=user_id))
            return p.id

    def update(self, product_id, data, user_id=None):
        with dbconn.SessionLocal.begin() as s:
            p = s.get(Product, product_id)
            if not p:
                raise ValueError("المنتج غير موجود.")
            old_price = Decimal(p.sale_price)
            old_qty = Decimal(p.quantity)
            for k, v in data.items():
                setattr(p, k, v)
            new_price = Decimal(p.sale_price)
            new_qty = Decimal(p.quantity)
            if new_price != old_price:
                pct = ((new_price - old_price) / old_price * 100) if old_price else None
                s.add(PriceHistory(product_id=p.id, old_price=old_price, new_price=new_price,
                                   change_percent=pct, changed_by=user_id))
            if new_qty != old_qty:
                s.add(StockMovement(product_id=p.id, quantity_before=old_qty,
                                    quantity_after=new_qty, delta=new_qty-old_qty,
                                    reason="تعديل المخزون", changed_by=user_id))
            try:
                s.flush()
            except IntegrityError as exc:
                raise ValueError("Barcode أو SKU موجود بالفعل.") from exc

    def delete(self, product_id):
        with dbconn.SessionLocal.begin() as s:
            p = s.get(Product, product_id)
            if p:
                s.delete(p)

    def delete_all(self):
        """Delete every product in one transaction (DB cascades clear history)."""
        with dbconn.SessionLocal.begin() as s:
            result = s.execute(delete(Product))
            return result.rowcount

    def bulk_price(self, product_ids, percent, user_id):
        with dbconn.SessionLocal.begin() as s:
            for pid in product_ids:
                p = s.get(Product, pid)
                if not p:
                    continue
                old = Decimal(p.sale_price)
                new = (old * (Decimal("1") + Decimal(str(percent))/Decimal("100"))).quantize(Decimal("0.01"))
                p.sale_price = new
                s.add(PriceHistory(product_id=p.id, old_price=old, new_price=new,
                                   change_percent=Decimal(str(percent)), changed_by=user_id))

    def low_stock_count(self):
        with dbconn.SessionLocal() as s:
            return s.scalar(select(func.count(Product.id)).where(Product.quantity <= Product.min_stock)) or 0

    def stats(self):
        with dbconn.SessionLocal() as s:
            return {
                "products": s.scalar(select(func.count(Product.id))) or 0,
                "categories": s.scalar(select(func.count(Category.id))) or 0,
                "low_stock": self.low_stock_count(),
            }

    def recent_products(self, limit=8):
        with dbconn.SessionLocal() as s:
            return list(s.scalars(select(Product).options(joinedload(Product.category)).order_by(desc(Product.updated_at)).limit(limit)))

    def recent_price_changes(self, limit=8):
        with dbconn.SessionLocal() as s:
            return list(s.scalars(select(PriceHistory).options(joinedload(PriceHistory.product)).order_by(desc(PriceHistory.changed_at)).limit(limit)))

class CategoryService:
    def all(self):
        with dbconn.SessionLocal() as s:
            return list(s.scalars(select(Category).order_by(Category.name)))

    def add(self, name):
        name = name.strip()
        if not name:
            raise ValueError("اسم التصنيف مطلوب.")
        with dbconn.SessionLocal.begin() as s:
            if s.scalar(select(Category).where(Category.name == name)):
                raise ValueError("التصنيف موجود بالفعل.")
            s.add(Category(name=name))

    def rename(self, category_id, name):
        name = name.strip()
        if not name:
            raise ValueError("اسم التصنيف مطلوب.")
        with dbconn.SessionLocal.begin() as s:
            c = s.get(Category, category_id)
            if not c:
                raise ValueError("التصنيف غير موجود.")
            duplicate = s.scalar(select(Category).where(Category.name == name, Category.id != category_id))
            if duplicate:
                raise ValueError("التصنيف موجود بالفعل.")
            c.name = name

    def delete(self, category_id):
        with dbconn.SessionLocal.begin() as s:
            c = s.get(Category, category_id)
            if not c:
                return
            if s.scalar(select(Product.id).where(Product.category_id == category_id).limit(1)):
                raise ValueError("لا يمكن حذف تصنيف يحتوي على منتجات. انقل المنتجات أولًا.")
            s.delete(c)

class HistoryService:
    def for_product(self, product_id, limit=100):
        with dbconn.SessionLocal() as s:
            return list(s.scalars(select(PriceHistory).options(joinedload(PriceHistory.product))
                                  .where(PriceHistory.product_id == product_id)
                                  .order_by(desc(PriceHistory.changed_at)).limit(limit)))

    def stock_for_product(self, product_id, limit=100):
        with dbconn.SessionLocal() as s:
            return list(s.scalars(select(StockMovement)
                                  .where(StockMovement.product_id == product_id)
                                  .order_by(desc(StockMovement.changed_at)).limit(limit)))

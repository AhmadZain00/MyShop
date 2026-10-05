from decimal import Decimal
from sqlalchemy import select
from app.database import connection as dbconn
from app.database.models import Product, StockMovement

class StockService:
    def adjust(self, product_id, delta, reason, user_id):
        delta = Decimal(str(delta))
        with dbconn.SessionLocal.begin() as s:
            p = s.get(Product, product_id)
            if not p:
                raise ValueError("المنتج غير موجود.")
            before = Decimal(p.quantity)
            after = before + delta
            if after < 0:
                raise ValueError("لا يمكن أن تصبح الكمية أقل من صفر.")
            p.quantity = after
            s.add(StockMovement(product_id=product_id, quantity_before=before,
                                quantity_after=after, delta=delta,
                                reason=reason, changed_by=user_id))
            return after

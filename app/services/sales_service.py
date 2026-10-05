from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload

from app.database import connection as dbconn
from app.database.models import Product, Sale, StockMovement

UTC_OFFSET_HOURS = 3  # Cairo: no DST since 2023 — local day = UTC+3 year-round.

def _local_day_bounds(now=None):
    """Start/end (naive UTC timestamps) of the shop's local calendar day."""
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
    local_now = now + timedelta(hours=UTC_OFFSET_HOURS)
    day_start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start = day_start_local - timedelta(hours=UTC_OFFSET_HOURS)
    return day_start, day_start + timedelta(days=1)

def to_local(naive_utc):
    """Convert a naive UTC timestamp from the DB to timezone-aware local time."""
    if naive_utc is None:
        return None
    return naive_utc.replace(tzinfo=timezone.utc).astimezone()

class SalesService:
    def record_sale(self, product_id, quantity, unit_price, user_id=None):
        """Record one sale and deduct stock in a single transaction.

        Raises ValueError when the product is missing, the quantity/price is
        invalid, or the stock is insufficient — nothing is written then.
        """
        quantity = Decimal(str(quantity))
        unit_price = Decimal(str(unit_price))
        if quantity <= 0:
            raise ValueError("الكمية يجب أن تكون أكبر من صفر.")
        if unit_price < 0:
            raise ValueError("السعر لا يمكن أن يكون سالبًا.")
        total = (quantity * unit_price).quantize(Decimal("0.01"))
        with dbconn.SessionLocal.begin() as s:
            p = s.get(Product, product_id)
            if not p:
                raise ValueError("المنتج غير موجود.")
            before = Decimal(p.quantity)
            after = before - quantity
            if after < 0:
                raise ValueError(f"الكمية غير كافية في المخزون (المتاح: {before:g} {p.unit}).")
            p.quantity = after
            s.add(StockMovement(product_id=product_id, quantity_before=before,
                                quantity_after=after, delta=-quantity,
                                reason="بيع", changed_by=user_id))
            sale = Sale(product_id=product_id, quantity=quantity,
                        unit_price=unit_price, total=total, sold_by=user_id)
            s.add(sale)
            s.flush()
            return sale.id, after

    def today_totals(self):
        """Total money and operations count for the current local day."""
        start, end = _local_day_bounds()
        with dbconn.SessionLocal() as s:
            total, count = s.execute(
                select(func.coalesce(func.sum(Sale.total), 0), func.count(Sale.id))
                .where(Sale.sold_at >= start, Sale.sold_at < end)
            ).one()
            return {"total": Decimal(total), "count": count}

    def sales_for_day(self, year, month, day):
        """Detailed sale rows for any calendar day (newest first)."""
        start_local = datetime(year, month, day)
        start = start_local - timedelta(hours=UTC_OFFSET_HOURS)
        end = start + timedelta(days=1)
        with dbconn.SessionLocal() as s:
            return list(s.scalars(
                select(Sale).options(joinedload(Sale.product))
                .where(Sale.sold_at >= start, Sale.sold_at < end)
                .order_by(desc(Sale.sold_at))
            ))

    def day_totals(self, year, month, day):
        """Totals for a specific calendar day (for reports)."""
        start_local = datetime(year, month, day)
        start = start_local - timedelta(hours=UTC_OFFSET_HOURS)
        end = start + timedelta(days=1)
        with dbconn.SessionLocal() as s:
            total, count = s.execute(
                select(func.coalesce(func.sum(Sale.total), 0), func.count(Sale.id))
                .where(Sale.sold_at >= start, Sale.sold_at < end)
            ).one()
            return {"total": Decimal(total), "count": count}

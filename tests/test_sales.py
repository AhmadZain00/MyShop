from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from app.database import connection as dbconn
from app.database.models import Product, Sale, StockMovement
from app.services.product_service import ProductService
from app.services.sales_service import SalesService, _local_day_bounds, to_local


def _make_product(name, quantity=Decimal("10"), price=Decimal("50")):
    stamp = datetime.now(timezone.utc).timestamp()
    pid = ProductService().add({
        "name": name, "barcode": f"SALE{stamp}", "sku": None, "brand": None,
        "purchase_price": Decimal("5"), "sale_price": price, "quantity": quantity,
        "unit": "قطعة", "min_stock": Decimal("0"), "notes": None, "category_id": None,
    })
    return pid


def test_record_sale_deducts_stock_and_records_movement():
    pid = _make_product("منتج بيع ١")
    sale_id, remaining = SalesService().record_sale(pid, 3, Decimal("50"))
    assert remaining == Decimal("7")
    with dbconn.SessionLocal() as s:
        assert Decimal(s.get(Product, pid).quantity) == Decimal("7")
        sale = s.get(Sale, sale_id)
        assert Decimal(sale.total) == Decimal("150.00")
        assert sale.sold_by is None
        moves = s.scalars(select(StockMovement).where(StockMovement.product_id == pid)).all()
        assert any(m.reason == "بيع" and Decimal(m.delta) == Decimal("-3") for m in moves)


def test_record_sale_rejects_insufficient_stock():
    pid = _make_product("منتج بيع ٢", quantity=Decimal("5"))
    with pytest.raises(ValueError):
        SalesService().record_sale(pid, 6, Decimal("50"))
    with dbconn.SessionLocal() as s:
        assert Decimal(s.get(Product, pid).quantity) == Decimal("5")
        assert s.scalar(select(func.count(Sale.id)).where(Sale.product_id == pid)) == 0


def test_record_sale_validates_inputs():
    pid = _make_product("منتج بيع ٣")
    svc = SalesService()
    with pytest.raises(ValueError):
        svc.record_sale(pid, 0, Decimal("50"))
    with pytest.raises(ValueError):
        svc.record_sale(pid, 1, Decimal("-1"))


def test_today_totals_increments_after_sales():
    svc = SalesService()
    before = svc.today_totals()
    pid = _make_product("منتج بيع ٤")
    svc.record_sale(pid, 2, Decimal("30"))
    svc.record_sale(pid, 1, Decimal("30"))
    after = svc.today_totals()
    assert after["count"] == before["count"] + 2
    assert Decimal(after["total"]) - Decimal(before["total"]) == Decimal("90.00")


def test_sales_for_day_window_boundaries():
    svc = SalesService()
    pid = _make_product("منتج بيع ٥")
    start, end = _local_day_bounds()
    # A sale one microsecond before the day window must not appear.
    with dbconn.SessionLocal.begin() as s:
        s.add(Sale(product_id=pid, quantity=Decimal("1"), unit_price=Decimal("10"),
                   total=Decimal("10"), sold_at=start - timedelta(microseconds=1)))
    assert [r for r in svc.sales_for_day(datetime.now(timezone.utc).year,
                                         datetime.now(timezone.utc).month,
                                         datetime.now(timezone.utc).day)
            if r.product_id == pid] == []
    # A sale inside the window must appear exactly once.
    with dbconn.SessionLocal.begin() as s:
        s.add(Sale(product_id=pid, quantity=Decimal("1"), unit_price=Decimal("10"),
                   total=Decimal("10"), sold_at=end - timedelta(microseconds=1)))
    rows = [r for r in svc.sales_for_day(datetime.now(timezone.utc).year,
                                         datetime.now(timezone.utc).month,
                                         datetime.now(timezone.utc).day)
            if r.product_id == pid]
    assert len(rows) == 1


def test_sale_keeps_price_snapshot():
    pid = _make_product("منتج بيع ٦", price=Decimal("50"))
    sale_id, _ = SalesService().record_sale(pid, 1, Decimal("40"))
    with dbconn.SessionLocal() as s:
        sale = s.get(Sale, sale_id)
        assert Decimal(sale.unit_price) == Decimal("40.00")
        assert Decimal(sale.total) == Decimal("40.00")


def test_to_local_roundtrip():
    naive_utc = datetime(2026, 7, 15, 12, 0)
    local = to_local(naive_utc)
    assert local.utcoffset() is not None
    assert local.astimezone(timezone.utc).replace(tzinfo=None) == naive_utc


def test_sale_dialog_builds_and_computes_total():
    """Regression: self.price (spinbox) once shadowed price(), so the dialog
    crashed on construction with a swallowed TypeError and the sell button
    appeared dead. The widget must live under a non-conflicting name."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    pid = _make_product("منتج ديالوج", price=Decimal("50"))
    p = ProductService().get(pid)
    from app.ui.main_window import SaleDialog
    dlg = SaleDialog(p)
    assert callable(dlg.price) and callable(dlg.quantity) and callable(dlg.total)
    assert dlg.total() == Decimal("50.00")
    dlg.price_spin.setValue(40)
    assert dlg.total() == Decimal("40.00")


def test_migrate_bumps_schema_to_2():
    from app.database.migrations import migrate
    from sqlalchemy import text
    with dbconn.engine.begin() as conn:
        conn.execute(text(
            "INSERT OR REPLACE INTO app_meta(key, value) VALUES ('schema_version', '1')"
        ))
    migrate()
    with dbconn.engine.begin() as conn:
        version = int(conn.execute(text(
            "SELECT value FROM app_meta WHERE key='schema_version'"
        )).scalar_one())
    assert version == 2

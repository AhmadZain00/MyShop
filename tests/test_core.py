from decimal import Decimal
from pathlib import Path
import tempfile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.database.models import Base, Product, User, Category, PriceHistory, StockMovement
from app.services.security import hash_password, verify_password
from app.services.product_service import ProductService, CategoryService
from app.services.stock_service import StockService

def test_password():
    h=hash_password("StrongPassword123!")
    assert verify_password("StrongPassword123!",h)
    assert not verify_password("wrong",h)

def test_database_and_product():
    with tempfile.TemporaryDirectory() as td:
        engine=create_engine(f"sqlite:///{Path(td)/'test.db'}", future=True)
        Base.metadata.create_all(engine)
        S=sessionmaker(bind=engine, future=True)
        with S.begin() as s:
            c=Category(name="خلاطات"); s.add(c); s.flush()
            p=Product(name="خلاط اختبار",barcode="123456",sale_price=Decimal("100"),quantity=5,category_id=c.id)
            s.add(p)
        with S() as s:
            p=s.scalar(select(Product).where(Product.barcode=="123456"))
            assert p.name=="خلاط اختبار"
            assert p.sale_price==Decimal("100.00")
        # Windows keeps SQLite file handles locked until the engine is disposed.
        engine.dispose()

def test_model_constraints():
    with tempfile.TemporaryDirectory() as td:
        engine=create_engine(f"sqlite:///{Path(td)/'test.db'}", future=True)
        Base.metadata.create_all(engine)
        S=sessionmaker(bind=engine, future=True)
        with S.begin() as s:
            s.add(Category(name="أحواض"))
        with S() as s:
            assert s.scalar(select(Category).where(Category.name=="أحواض")) is not None
        # Release SQLite file handles before TemporaryDirectory cleanup on Windows.
        engine.dispose()

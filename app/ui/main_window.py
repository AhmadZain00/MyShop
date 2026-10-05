from decimal import Decimal, InvalidOperation
from PySide6 import QtWidgets, QtCore, QtGui
from sqlalchemy import select, func
from app.database import connection as dbconn
from app.database.models import Product, Category
from app.services.product_service import ProductService, CategoryService, HistoryService
from app.services.stock_service import StockService
from app.services.auth_service import AuthService
from app.services.excel_service import make_template, export_products, export_errors, export_sales
from app.services.sales_service import SalesService, to_local
from app.services.excel_worker import ExcelImportWorker, ExcelExportWorker
from app.services.backup_service import backup_to, restore_from
from app.services.database_service import inspect_database, import_database
from app.ui.dialogs import UserDialog, ResetPasswordDialog

class StatCard(QtWidgets.QFrame):
    def __init__(self, title, value="0", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        lay = QtWidgets.QVBoxLayout(self)
        t = QtWidgets.QLabel(title); t.setObjectName("statTitle")
        self.value = QtWidgets.QLabel(value); self.value.setObjectName("statValue")
        lay.addWidget(t); lay.addWidget(self.value)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.products = ProductService()
        self.categories = CategoryService()
        self.history = HistoryService()
        self.stock = StockService()
        self.sales = SalesService()
        self.auth = AuthService()
        self.current_product_id = None
        self.excel_thread = None
        self.excel_worker = None
        self.excel_progress = None
        self.setWindowTitle("MyShop — إدارة الأدوات الصحية")
        self.resize(1380, 850)
        self.setLayoutDirection(QtCore.Qt.RightToLeft)
        self._style()
        self._build()
        self.refresh_all()
        # Keep the "today's sales" card and the sales tab live without manual refresh.
        self.sales_timer = QtCore.QTimer(self)
        self.sales_timer.setInterval(30_000)
        self.sales_timer.timeout.connect(self.refresh_sales_today)
        self.sales_timer.start()

    def _style(self):
        self.setStyleSheet("""
        QWidget { font-family: "Segoe UI"; font-size: 10.5pt; }
        QMainWindow, QWidget { background: #f5f7fa; color: #1f2937; }
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTableWidget { color: #1f2937;
            background: white; border: 1px solid #d7dce2; border-radius: 7px;
            padding: 7px;
        }
        QPushButton {
            background: #1f6feb; color: white; border: 0; border-radius: 7px;
            padding: 9px 15px; font-weight: 600;
        }
        QPushButton:hover { background: #1559bd; }
        QPushButton:disabled { background: #aab2bd; }
        QTabWidget::pane { border: 0; }
        QTabBar::tab { background: #e9edf2; color: #344054; padding: 11px 18px; margin: 2px; border-radius: 7px; }
        QTabBar::tab:selected { background: #1f6feb; color: white; }
        QHeaderView::section { background: #eef1f5; color: #344054; padding: 8px; border: 0; font-weight: 700; }
        QTableWidget { gridline-color: #edf0f3; color: #1f2937; }
        QFrame#statCard { background: white; border: 1px solid #e2e6eb; border-radius: 12px; }
        QLabel#statTitle { color: #667085; }
        QLabel#statValue { font-size: 25pt; font-weight: 800; }
        QLabel#priceBig { font-size: 30pt; font-weight: 900; }
        QGroupBox { background: white; color: #1f2937; border: 1px solid #e2e6eb; border-radius: 10px; margin-top: 12px; padding: 12px; }
        QGroupBox::title { subcontrol-origin: margin; right: 12px; padding: 0 6px; font-weight: 700; }
        """)

    def _build(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("MyShop")
        title.setStyleSheet("font-size: 22pt; font-weight: 900;")
        subtitle = QtWidgets.QLabel(f"مرحبًا {self.user['username']} — {self.user['role']}")
        subtitle.setStyleSheet("color:#667085;")
        header.addWidget(title); header.addSpacing(12); header.addWidget(subtitle); header.addStretch()
        root.addLayout(header)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("🔎  بحث سريع: اسم المنتج / Barcode / SKU / الماركة")
        self.search.setMinimumHeight(48)
        self.search.returnPressed.connect(self.focus_first_result)
        self.search.setToolTip("يمكن استخدام Barcode Scanner كلوحة مفاتيح HID ثم Enter")
        self.search.textChanged.connect(self.search_products)
        root.addWidget(self.search)
        self.search.setFocus()

        self.tabs = QtWidgets.QTabWidget()
        root.addWidget(self.tabs, 1)
        self.dashboard = QtWidgets.QWidget()
        self.products_page = QtWidgets.QWidget()
        self.add_page = QtWidgets.QWidget()
        self.categories_page = QtWidgets.QWidget()
        self.price_page = QtWidgets.QWidget()
        self.stock_page = QtWidgets.QWidget()
        self.history_page = QtWidgets.QWidget()
        self.sales_page = QtWidgets.QWidget()
        self.tools_page = QtWidgets.QWidget()
        for page, label in [
            (self.dashboard,"الرئيسية"),(self.products_page,"المنتجات"),
            (self.add_page,"إضافة منتج"),(self.categories_page,"التصنيفات"),
            (self.price_page,"تعديل الأسعار"),(self.stock_page,"المخزون"),
            (self.history_page,"سجل الأسعار"),(self.sales_page,"المبيعات"),
            (self.tools_page,"Excel / Backup / Database")
        ]:
            self.tabs.addTab(page, label)
        if self.user["role"]=="admin":
            self.users_page = QtWidgets.QWidget()
            self.tabs.addTab(self.users_page, "المستخدمين")
        self._dashboard_ui(); self._products_ui(); self._add_ui()
        self._categories_ui(); self._price_ui(); self._stock_ui()
        self._history_ui(); self._sales_ui(); self._tools_ui()
        if self.user["role"]=="admin":
            self._users_ui()
        self.tabs.currentChanged.connect(self._tab_changed)

    def _dashboard_ui(self):
        l=QtWidgets.QVBoxLayout(self.dashboard)
        cards=QtWidgets.QHBoxLayout()
        self.card_products=StatCard("عدد المنتجات")
        self.card_categories=StatCard("عدد التصنيفات")
        self.card_sales=StatCard("مبيعات اليوم (جنيه)")
        self.card_low=StatCard("مخزون منخفض")
        for c in [self.card_products,self.card_categories,self.card_sales,self.card_low]:
            cards.addWidget(c)
        l.addLayout(cards)
        box=QtWidgets.QGroupBox("بحث سريع / المنتج المحدد")
        bl=QtWidgets.QVBoxLayout(box)
        self.product_name=QtWidgets.QLabel("لم يتم اختيار منتج")
        self.product_name.setStyleSheet("font-size:18pt;font-weight:800;")
        self.product_details=QtWidgets.QLabel("")
        self.price_big=QtWidgets.QLabel("—"); self.price_big.setObjectName("priceBig")
        self.price_big.setAlignment(QtCore.Qt.AlignCenter)
        bl.addWidget(self.product_name); bl.addWidget(self.product_details); bl.addWidget(self.price_big)
        self.sell_btn=QtWidgets.QPushButton("💰 بيع هذا المنتج")
        self.sell_btn.setEnabled(False)
        self.sell_btn.clicked.connect(self.sell_selected)
        bl.addWidget(self.sell_btn)
        l.addWidget(box)
        split=QtWidgets.QHBoxLayout()
        self.recent_products_table=self._compact_table(["المنتج","السعر","آخر تعديل"])
        self.recent_prices_table=self._compact_table(["المنتج","السعر القديم","السعر الجديد","التاريخ"])
        a=QtWidgets.QGroupBox("آخر المنتجات تعديلًا"); al=QtWidgets.QVBoxLayout(a); al.addWidget(self.recent_products_table)
        b=QtWidgets.QGroupBox("آخر تغييرات الأسعار"); bl2=QtWidgets.QVBoxLayout(b); bl2.addWidget(self.recent_prices_table)
        split.addWidget(a); split.addWidget(b); l.addLayout(split)

    def _compact_table(self, headers):
        t=QtWidgets.QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    def _products_ui(self):
        l=QtWidgets.QVBoxLayout(self.products_page)
        filters=QtWidgets.QHBoxLayout()
        self.category_filter=QtWidgets.QComboBox(); self.category_filter.currentIndexChanged.connect(self.refresh_table)
        self.low_filter=QtWidgets.QCheckBox("مخزون منخفض فقط"); self.low_filter.stateChanged.connect(self.refresh_table)
        filters.addWidget(QtWidgets.QLabel("التصنيف:")); filters.addWidget(self.category_filter)
        filters.addWidget(self.low_filter); filters.addStretch()
        edit=QtWidgets.QPushButton("تعديل المحدد"); edit.clicked.connect(self.edit_selected)
        delete=QtWidgets.QPushButton("حذف المحدد"); delete.clicked.connect(self.delete_selected)
        details=QtWidgets.QPushButton("عرض التفاصيل"); details.clicked.connect(self.show_selected)
        sellb=QtWidgets.QPushButton("بيع المحدد"); sellb.clicked.connect(self.sell_selected_from_table)
        filters.addWidget(details); filters.addWidget(sellb); filters.addWidget(edit); filters.addWidget(delete)
        l.addLayout(filters)
        if self.user["role"]=="admin":
            danger=QtWidgets.QPushButton("حذف كل المنتجات")
            danger.setToolTip("حذف جميع المنتجات نهائيًا، بما في ذلك سجل الأسعار وحركات المخزون")
            danger.setStyleSheet("QPushButton { background: #c0392b; } QPushButton:hover { background: #a03024; }")
            danger.clicked.connect(self.delete_all_products)
            filters.addWidget(danger)
        if self.user["role"]!="admin":
            edit.setEnabled(False); delete.setEnabled(False)
        self.table=QtWidgets.QTableWidget(0,9)
        self.table.setHorizontalHeaderLabels(["ID","المنتج","Barcode","SKU","التصنيف","الكمية","الوحدة","سعر البيع","الحد الأدنى"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(lambda _: self.edit_selected())
        self.table.setSortingEnabled(True)
        l.addWidget(self.table)
        if self.user["role"]!="admin":
            edit.setEnabled(False); delete.setEnabled(False)

    def _add_ui(self):
        form=QtWidgets.QFormLayout(self.add_page)
        self.fields={}
        specs=[("اسم المنتج",""),("Barcode",""),("SKU",""),("الماركة",""),
               ("سعر الشراء","0"),("سعر البيع","0"),("الكمية","0"),("الوحدة","قطعة"),
               ("الحد الأدنى","0"),("ملاحظات","")]
        for label,default in specs:
            w=QtWidgets.QLineEdit(default); self.fields[label]=w; form.addRow(label+":",w)
        self.add_category_combo=QtWidgets.QComboBox(); form.addRow("التصنيف:",self.add_category_combo)
        b=QtWidgets.QPushButton("إضافة المنتج"); b.clicked.connect(self.add_product); form.addRow(b)

    def _categories_ui(self):
        l=QtWidgets.QVBoxLayout(self.categories_page)
        top=QtWidgets.QHBoxLayout()
        self.category_name=QtWidgets.QLineEdit(); self.category_name.setPlaceholderText("اسم التصنيف الجديد")
        add=QtWidgets.QPushButton("إضافة تصنيف"); add.clicked.connect(self.add_category)
        top.addWidget(self.category_name); top.addWidget(add); top.addStretch(); l.addLayout(top)
        self.category_table=QtWidgets.QTableWidget(0,3)
        self.category_table.setHorizontalHeaderLabels(["ID","التصنيف","عدد المنتجات"])
        self.category_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        l.addWidget(self.category_table)
        btns=QtWidgets.QHBoxLayout()
        ren=QtWidgets.QPushButton("إعادة تسمية"); ren.clicked.connect(self.rename_category)
        dele=QtWidgets.QPushButton("حذف التصنيف"); dele.clicked.connect(self.delete_category)
        btns.addWidget(ren); btns.addWidget(dele); btns.addStretch(); l.addLayout(btns)
        if self.user["role"]!="admin":
            add.setEnabled(False); ren.setEnabled(False); dele.setEnabled(False)

    def _price_ui(self):
        l=QtWidgets.QVBoxLayout(self.price_page)
        info=QtWidgets.QLabel("حدد المنتجات من جدول المنتجات أولًا، ثم عد إلى هذه الصفحة لتطبيق نسبة زيادة أو خفض.")
        info.setStyleSheet("color:#667085;")
        l.addWidget(info)
        row=QtWidgets.QHBoxLayout()
        self.price_percent=QtWidgets.QDoubleSpinBox(); self.price_percent.setRange(-100,10000); self.price_percent.setDecimals(2); self.price_percent.setSuffix(" %")
        self.price_percent.setValue(10)
        self.price_selection_label=QtWidgets.QLabel("0 منتج محدد")
        applyb=QtWidgets.QPushButton("تطبيق على المحدد"); applyb.clicked.connect(self.apply_bulk_price)
        row.addWidget(QtWidgets.QLabel("التغيير:")); row.addWidget(self.price_percent)
        row.addWidget(self.price_selection_label); row.addStretch(); row.addWidget(applyb)
        l.addLayout(row)
        self.bulk_preview=QtWidgets.QTableWidget(0,4)
        self.bulk_preview.setHorizontalHeaderLabels(["المنتج","السعر الحالي","السعر بعد التغيير","النسبة"])
        l.addWidget(self.bulk_preview)
        if self.user["role"]!="admin": applyb.setEnabled(False)

    def _stock_ui(self):
        l=QtWidgets.QVBoxLayout(self.stock_page)
        top=QtWidgets.QHBoxLayout()
        self.stock_search=QtWidgets.QLineEdit(); self.stock_search.setPlaceholderText("ابحث عن منتج للمخزون")
        self.stock_search.textChanged.connect(self.refresh_stock_table)
        top.addWidget(self.stock_search); l.addLayout(top)
        self.stock_table=QtWidgets.QTableWidget(0,6)
        self.stock_table.setHorizontalHeaderLabels(["ID","المنتج","الكمية","الوحدة","الحد الأدنى","الحالة"])
        self.stock_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        l.addWidget(self.stock_table)
        action=QtWidgets.QHBoxLayout()
        self.stock_delta=QtWidgets.QDoubleSpinBox(); self.stock_delta.setRange(-1000000,1000000); self.stock_delta.setDecimals(3)
        self.stock_reason=QtWidgets.QLineEdit("تعديل يدوي")
        adj=QtWidgets.QPushButton("تطبيق حركة مخزون"); adj.clicked.connect(self.adjust_stock)
        action.addWidget(QtWidgets.QLabel("التغيير:")); action.addWidget(self.stock_delta)
        action.addWidget(QtWidgets.QLabel("السبب:")); action.addWidget(self.stock_reason)
        action.addWidget(adj); l.addLayout(action)
        if self.user["role"]!="admin": adj.setEnabled(False)

    def _history_ui(self):
        l=QtWidgets.QVBoxLayout(self.history_page)
        top=QtWidgets.QHBoxLayout()
        self.history_product=QtWidgets.QLineEdit(); self.history_product.setPlaceholderText("اكتب ID المنتج أو اختره من المنتجات")
        b=QtWidgets.QPushButton("عرض السجل"); b.clicked.connect(self.refresh_history)
        top.addWidget(self.history_product); top.addWidget(b); l.addLayout(top)
        self.history_table=QtWidgets.QTableWidget(0,5)
        self.history_table.setHorizontalHeaderLabels(["المنتج","السعر القديم","السعر الجديد","نسبة التغيير","التاريخ"])
        l.addWidget(self.history_table)

    def _sales_ui(self):
        l=QtWidgets.QVBoxLayout(self.sales_page)
        top=QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("التاريخ:"))
        self.sales_date=QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.sales_date.setCalendarPopup(True); self.sales_date.setDisplayFormat("yyyy-MM-dd")
        self.sales_date.dateChanged.connect(self.refresh_sales)
        todayb=QtWidgets.QPushButton("اليوم"); todayb.clicked.connect(self.sales_goto_today)
        self.sales_export=QtWidgets.QPushButton("تصدير اليوم إلى Excel")
        self.sales_export.clicked.connect(self.export_sales_excel)
        top.addWidget(self.sales_date); top.addWidget(todayb); top.addStretch()
        top.addWidget(self.sales_export)
        l.addLayout(top)
        summary=QtWidgets.QHBoxLayout()
        self.card_sales_count=StatCard("عدد العمليات")
        self.card_sales_total=StatCard("إجمالي اليوم","0.00 جنيه")
        summary.addWidget(self.card_sales_count); summary.addWidget(self.card_sales_total); summary.addStretch()
        l.addLayout(summary)
        self.sales_table=self._compact_table(["الوقت","المنتج","الكمية","سعر الوحدة","الإجمالي"])
        l.addWidget(self.sales_table)
        if self.user["role"]!="admin": self.sales_export.setEnabled(False)

    def _tools_ui(self):
        l=QtWidgets.QVBoxLayout(self.tools_page)
        buttons=[
            ("تحميل نموذج Excel",self.template_excel),("استيراد Excel",self.import_excel),
            ("تصدير المنتجات إلى Excel",self.export_excel),("إنشاء Backup",self.backup),
            ("Restore",self.restore),("استيراد Database",self.import_db)]
        for text,slot in buttons:
            b=QtWidgets.QPushButton(text); b.setMinimumHeight(45); b.clicked.connect(slot)
            b.setEnabled(self.user["role"]=="admin"); l.addWidget(b)
        l.addStretch()

    def _users_ui(self):
        l=QtWidgets.QVBoxLayout(self.users_page)
        top=QtWidgets.QHBoxLayout()
        add=QtWidgets.QPushButton("إضافة مستخدم")
        add.clicked.connect(self.add_user)
        top.addWidget(add); top.addStretch()
        l.addLayout(top)
        self.users_table=QtWidgets.QTableWidget(0,4)
        self.users_table.setHorizontalHeaderLabels(["ID","اسم المستخدم","الدور","الحالة"])
        self.users_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.users_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        l.addWidget(self.users_table)
        btns=QtWidgets.QHBoxLayout()
        reset=QtWidgets.QPushButton("إعادة تعيين كلمة المرور")
        reset.clicked.connect(self.reset_user_password)
        delete=QtWidgets.QPushButton("حذف المستخدم")
        delete.setStyleSheet("QPushButton { background: #c0392b; } QPushButton:hover { background: #a03024; }")
        delete.clicked.connect(self.delete_user)
        btns.addWidget(reset); btns.addWidget(delete); btns.addStretch()
        l.addLayout(btns)
        self.refresh_users_table()

    def refresh_users_table(self):
        users=self.auth.list_users()
        self.users_table.setRowCount(len(users))
        for r,u in enumerate(users):
            role_label="مدير" if u["role"]=="admin" else "موظف"
            status="كلمة مرور مؤقتة" if u["must_change_password"] else "نشط"
            vals=[u["id"],u["username"],role_label,status]
            for c,v in enumerate(vals):
                self.users_table.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))
        self.users_table.resizeColumnsToContents()

    def _selected_user(self):
        row=self.users_table.currentRow()
        if row<0: return None
        return {"id":int(self.users_table.item(row,0).text()),
                "username":self.users_table.item(row,1).text()}

    def add_user(self):
        dlg=UserDialog(self.auth,self)
        if dlg.exec()==QtWidgets.QDialog.Accepted:
            self.refresh_users_table()

    def reset_user_password(self):
        u=self._selected_user()
        if not u: return
        dlg=ResetPasswordDialog(u["id"],u["username"],self.auth,self)
        if dlg.exec()==QtWidgets.QDialog.Accepted:
            self.refresh_users_table()

    def delete_user(self):
        u=self._selected_user()
        if not u: return
        if QtWidgets.QMessageBox.question(
                self,"تأكيد",
                f"هل تريد حذف المستخدم '{u['username']}'؟")!=QtWidgets.QMessageBox.Yes:
            return
        try:
            self.auth.delete_user(u["id"],self.user["id"])
            self.refresh_users_table()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"خطأ",str(e))

    def refresh_all(self):
        self.load_categories()
        self.refresh_dashboard()
        self.refresh_table()
        self.refresh_stock_table()
        self.refresh_categories_table()
        self.update_selection_count()
        self.refresh_sales()

    def load_categories(self):
        cats=self.categories.all()
        for combo in [self.category_filter,self.add_category_combo]:
            old=combo.currentData(); combo.blockSignals(True); combo.clear()
            combo.addItem("كل التصنيفات" if combo is self.category_filter else "بدون تصنيف", None)
            for c in cats: combo.addItem(c.name,c.id)
            if old is not None:
                idx=combo.findData(old)
                if idx>=0: combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def refresh_dashboard(self):
        t=self.sales.today_totals()
        self.card_sales.value.setText(f"{t['total']:,.2f}")
        self.card_sales.setToolTip(f"{t['count']} عملية بيع اليوم")
        s=self.products.stats()
        self.card_products.value.setText(str(s["products"]))
        self.card_categories.value.setText(str(s["categories"]))
        self.card_low.value.setText(str(s["low_stock"]))
        recent=self.products.recent_products()
        self.recent_products_table.setRowCount(len(recent))
        for r,p in enumerate(recent):
            vals=[p.name,f"{p.sale_price:,.2f}",p.updated_at.strftime("%Y-%m-%d %H:%M")]
            for c,v in enumerate(vals): self.recent_products_table.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))
        changes=self.products.recent_price_changes()
        self.recent_prices_table.setRowCount(len(changes))
        for r,h in enumerate(changes):
            vals=[h.product.name,f"{h.old_price:,.2f}",f"{h.new_price:,.2f}",h.changed_at.strftime("%Y-%m-%d %H:%M")]
            for c,v in enumerate(vals): self.recent_prices_table.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))

    def refresh_sales_today(self):
        t=self.sales.today_totals()
        self.card_sales.value.setText(f"{t['total']:,.2f}")
        self.card_sales.setToolTip(f"{t['count']} عملية بيع اليوم")
        if self.tabs.currentWidget() is self.sales_page:
            self.refresh_sales()

    def _tab_changed(self,_idx):
        if self.tabs.widget(_idx) is self.sales_page:
            self.refresh_sales()

    def refresh_sales(self):
        if not hasattr(self,"sales_table"): return
        day=self.sales_date.date().toPython()
        rows=self.sales.sales_for_day(day.year,day.month,day.day)
        self.sales_table.setRowCount(len(rows))
        for r,s in enumerate(rows):
            vals=[to_local(s.sold_at).strftime("%Y-%m-%d %H:%M"),s.product.name,
                  f"{s.quantity:g}",f"{s.unit_price:,.2f}",f"{s.total:,.2f}"]
            for c,v in enumerate(vals): self.sales_table.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))
        self.sales_table.resizeColumnsToContents()
        t=self.sales.day_totals(day.year,day.month,day.day)
        self.card_sales_count.value.setText(str(t["count"]))
        self.card_sales_total.value.setText(f"{t['total']:,.2f} جنيه")

    def sales_goto_today(self):
        self.sales_date.setDate(QtCore.QDate.currentDate())

    def sell_selected(self):
        self.sell_product(self.current_product_id)

    def sell_selected_from_table(self):
        rows=self.table.selectionModel().selectedRows()
        self.sell_product(int(self.table.item(rows[0].row(),0).text()) if rows else None)

    def sell_product(self,pid):
        if pid is None:
            QtWidgets.QMessageBox.information(self,"بيع","اختر منتجًا أولًا (امسح الباركود أو حدده من الجدول).")
            return
        p=self.products.get(pid)
        if not p: return
        if Decimal(str(p.quantity))<=0:
            QtWidgets.QMessageBox.warning(self,"بيع",f"لا يوجد مخزون من '{p.name}'.")
            return
        dlg=SaleDialog(p,self)
        if dlg.exec()!=QtWidgets.QDialog.Accepted: return
        try:
            sale_id,remaining=self.sales.record_sale(pid,dlg.quantity(),dlg.price(),self.user["id"])
            QtWidgets.QMessageBox.information(self,"تم البيع",
                f"تم بيع: {p.name}\nالكمية: {dlg.quantity():g}  |  الإجمالي: {dlg.total():,.2f} جنيه\nالمتبقي بالمخزون: {remaining:g}")
            # Snap the sales tab to today so a window left open since yesterday
            # doesn't keep showing an old (empty) day right after a new sale.
            self.sales_date.setDate(QtCore.QDate.currentDate())
            self.refresh_all()
        except Exception as e: QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def export_sales_excel(self):
        day=self.sales_date.date().toPython()
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,"تصدير المبيعات",
            f"sales_{day.isoformat()}.xlsx","Excel (*.xlsx)")
        if path:
            try:
                result=export_sales(path,day)
                QtWidgets.QMessageBox.information(self,"تم",
                    f"تم تصدير {result['count']} عملية بإجمالي {result['total']:,.2f} جنيه.")
            except Exception as e:QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def refresh_table(self):
        cat=self.category_filter.currentData() if hasattr(self,"category_filter") else None
        low=self.low_filter.isChecked() if hasattr(self,"low_filter") else False
        rows=self.products.search(self.search.text(),cat,low,1000)
        self.table.setSortingEnabled(False); self.table.setRowCount(len(rows))
        for r,p in enumerate(rows):
            vals=[p.id,p.name,p.barcode or "",p.sku or "",p.category.name if p.category else "",
                  f"{p.quantity:g}",p.unit,f"{p.sale_price:,.2f}",f"{p.min_stock:g}"]
            for c,v in enumerate(vals): self.table.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))
        self.table.setSortingEnabled(True); self.table.resizeColumnsToContents()
        self.update_selection_count()

    def search_products(self): self.refresh_table()

    def focus_first_result(self):
        if not self.table.rowCount(): return
        self.table.selectRow(0); self.show_selected()
        # Scanned barcode (or exact SKU) jumps straight to the confirm dialog.
        term=self.search.text().strip()
        if term:
            p=self.products.get(int(self.table.item(0,0).text()))
            if p and term in (p.barcode,p.sku): self.sell_product(p.id)

    def selected_ids(self):
        return [int(self.table.item(i.row(),0).text()) for i in self.table.selectionModel().selectedRows()]

    def update_selection_count(self):
        if hasattr(self,"price_selection_label"):
            ids=self.selected_ids() if hasattr(self,"table") else []
            self.price_selection_label.setText(f"{len(ids)} منتج محدد")
            self.update_bulk_preview(ids)

    def show_selected(self):
        rows=self.table.selectionModel().selectedRows()
        if not rows:return
        pid=int(self.table.item(rows[0].row(),0).text()); p=self.products.get(pid)
        if not p:return
        self.current_product_id=pid
        self.product_name.setText(p.name)
        self.product_details.setText(f"Barcode: {p.barcode or '-'}   |   SKU: {p.sku or '-'}   |   المخزون: {p.quantity:g} {p.unit}")
        self.price_big.setText(f"{p.sale_price:,.2f} جنيه")
        self.sell_btn.setEnabled(True)
        self.history_product.setText(str(pid))
        self.refresh_history()
        self.tabs.setCurrentWidget(self.dashboard)

    def edit_selected(self):
        rows=self.table.selectionModel().selectedRows()
        if not rows:return
        pid=int(self.table.item(rows[0].row(),0).text()); p=self.products.get(pid)
        if not p:return
        dlg=ProductEditDialog(p,self.categories.all(),self)
        if dlg.exec()==QtWidgets.QDialog.Accepted:
            try:
                self.products.update(pid,dlg.data(),self.user["id"])
                self.refresh_all()
            except Exception as e: QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def add_product(self):
        try:
            def dec(label): return Decimal(self.fields[label].text() or "0")
            d={"name":self.fields["اسم المنتج"].text().strip(),"barcode":self.fields["Barcode"].text().strip() or None,
               "sku":self.fields["SKU"].text().strip() or None,"brand":self.fields["الماركة"].text().strip() or None,
               "purchase_price":dec("سعر الشراء"),"sale_price":dec("سعر البيع"),"quantity":dec("الكمية"),
               "unit":self.fields["الوحدة"].text() or "قطعة","min_stock":dec("الحد الأدنى"),
               "notes":self.fields["ملاحظات"].text() or None,"category_id":self.add_category_combo.currentData()}
            if not d["name"]: raise ValueError("اسم المنتج مطلوب.")
            self.products.add(d,self.user["id"])
            QtWidgets.QMessageBox.information(self,"تم","تمت إضافة المنتج.")
            for w in self.fields.values(): w.clear()
            self.refresh_all()
        except Exception as e: QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def refresh_categories_table(self):
        cats=self.categories.all(); self.category_table.setRowCount(len(cats))
        with dbconn.SessionLocal() as s:
            counts=dict(s.execute(select(Product.category_id, func.count(Product.id)).group_by(Product.category_id)).all())
        for r,c in enumerate(cats):
            vals=[c.id,c.name,counts.get(c.id,0)]
            for col,v in enumerate(vals): self.category_table.setItem(r,col,QtWidgets.QTableWidgetItem(str(v)))
        self.category_table.resizeColumnsToContents()

    def add_category(self):
        try:self.categories.add(self.category_name.text());self.category_name.clear();self.refresh_all()
        except Exception as e:QtWidgets.QMessageBox.warning(self,"خطأ",str(e))

    def rename_category(self):
        row=self.category_table.currentRow()
        if row<0:return
        cid=int(self.category_table.item(row,0).text())
        old=self.category_table.item(row,1).text()
        name,ok=QtWidgets.QInputDialog.getText(self,"إعادة تسمية","الاسم الجديد:",text=old)
        if ok:
            try:self.categories.rename(cid,name);self.refresh_all()
            except Exception as e:QtWidgets.QMessageBox.warning(self,"خطأ",str(e))

    def delete_category(self):
        row=self.category_table.currentRow()
        if row<0:return
        cid=int(self.category_table.item(row,0).text())
        if QtWidgets.QMessageBox.question(self,"تأكيد","هل تريد حذف التصنيف؟")!=QtWidgets.QMessageBox.Yes:return
        try:self.categories.delete(cid);self.refresh_all()
        except Exception as e:QtWidgets.QMessageBox.warning(self,"خطأ",str(e))

    def update_bulk_preview(self,ids):
        self.bulk_preview.setRowCount(0)
        pct=Decimal(str(self.price_percent.value())) if hasattr(self,"price_percent") else Decimal("0")
        for pid in ids:
            p=self.products.get(pid)
            if not p:continue
            old=Decimal(p.sale_price); new=(old*(1+pct/100)).quantize(Decimal("0.01"))
            r=self.bulk_preview.rowCount(); self.bulk_preview.insertRow(r)
            for c,v in enumerate([p.name,f"{old:,.2f}",f"{new:,.2f}",f"{pct:g}%"]):
                self.bulk_preview.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))

    def apply_bulk_price(self):
        ids=self.selected_ids()
        if not ids:return
        pct=self.price_percent.value()
        if QtWidgets.QMessageBox.question(self,"تأكيد",f"تطبيق {pct:g}% على {len(ids)} منتج؟")!=QtWidgets.QMessageBox.Yes:return
        try:self.products.bulk_price(ids,pct,self.user["id"]);self.refresh_all()
        except Exception as e:QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def refresh_stock_table(self):
        term=self.stock_search.text() if hasattr(self,"stock_search") else ""
        rows=self.products.search(term,limit=1000)
        self.stock_table.setRowCount(len(rows))
        for r,p in enumerate(rows):
            low=Decimal(p.quantity)<=Decimal(p.min_stock)
            vals=[p.id,p.name,f"{p.quantity:g}",p.unit,f"{p.min_stock:g}","⚠ منخفض" if low else "جيد"]
            for c,v in enumerate(vals): self.stock_table.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))
        self.stock_table.resizeColumnsToContents()

    def adjust_stock(self):
        row=self.stock_table.currentRow()
        if row<0:return
        pid=int(self.stock_table.item(row,0).text())
        try:
            after=self.stock.adjust(pid,self.stock_delta.value(),self.stock_reason.text().strip() or "تعديل يدوي",self.user["id"])
            QtWidgets.QMessageBox.information(self,"تم",f"الكمية الجديدة: {after:g}")
            self.refresh_all()
        except Exception as e:QtWidgets.QMessageBox.warning(self,"خطأ",str(e))

    def refresh_history(self):
        try:pid=int(self.history_product.text())
        except:return
        rows=self.history.for_product(pid); self.history_table.setRowCount(len(rows))
        for r,h in enumerate(rows):
            vals=[h.product.name,f"{h.old_price:,.2f}",f"{h.new_price:,.2f}",
                  f"{h.change_percent:.2f}%" if h.change_percent is not None else "-",h.changed_at.strftime("%Y-%m-%d %H:%M")]
            for c,v in enumerate(vals):self.history_table.setItem(r,c,QtWidgets.QTableWidgetItem(str(v)))
        self.history_table.resizeColumnsToContents()

    def delete_selected(self):
        rows=self.table.selectionModel().selectedRows()
        if not rows:return
        if QtWidgets.QMessageBox.question(self,"تأكيد","سيتم حذف المنتج/المنتجات المحددة. متابعة؟")!=QtWidgets.QMessageBox.Yes:return
        try:
            for pid in self.selected_ids():self.products.delete(pid)
            self.refresh_all()
        except Exception as e:QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def delete_all_products(self):
        count=self.products.stats()["products"]
        if count==0:
            QtWidgets.QMessageBox.information(self,"لا يوجد شيء", "لا توجد منتجات للحذف.")
            return
        confirm=QtWidgets.QMessageBox.warning(
            self,"تأكيد الحذف",
            f"سيتم حذف جميع المنتجات ({count} منتج) نهائيًا،\n"
            "بما في ذلك سجل الأسعار وحركات المخزون المرتبطة بها.\n\n"
            "لا يمكن التراجع عن هذه العملية. متابعة؟",
            QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if confirm!=QtWidgets.QMessageBox.Yes:return
        try:
            deleted=self.products.delete_all()
            QtWidgets.QMessageBox.information(self,"تم",f"تم حذف {deleted} منتج.")
            self.refresh_all()
        except Exception as e:QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def template_excel(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,"حفظ نموذج Excel","products_template.xlsx","Excel (*.xlsx)")
        if path:make_template(path);QtWidgets.QMessageBox.information(self,"تم","تم إنشاء النموذج.")

    def import_excel(self):
        if self.excel_thread is not None:
            return
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,"اختيار Excel","","Excel (*.xlsx)")
        if not path:return
        mode,ok=QtWidgets.QInputDialog.getItem(self,"تكرار المنتجات","عند وجود Barcode/SKU:",["تحديث الموجود","تجاهل الموجود","تحديث الأسعار فقط","إلغاء"],0,False)
        if not ok or mode=="إلغاء":return
        self.excel_progress=QtWidgets.QProgressDialog("جاري استيراد Excel...","إلغاء",0,100,self)
        self.excel_progress.setWindowTitle("استيراد المنتجات")
        self.excel_progress.setAutoClose(False); self.excel_progress.setMinimumDuration(0); self.excel_progress.show()
        self.excel_thread=QtCore.QThread(self)
        self.excel_worker=ExcelImportWorker(path,{"تحديث الموجود":"update","تجاهل الموجود":"ignore","تحديث الأسعار فقط":"prices"}[mode])
        self.excel_worker.moveToThread(self.excel_thread)
        self.excel_thread.started.connect(self.excel_worker.run)
        self.excel_worker.progress.connect(self.excel_progress.setValue)
        self.excel_progress.canceled.connect(self.excel_worker.cancel)
        self.excel_worker.finished.connect(self._excel_import_finished)
        self.excel_worker.failed.connect(self._excel_import_failed)
        self.excel_worker.finished.connect(self.excel_thread.quit)
        self.excel_worker.failed.connect(self.excel_thread.quit)
        self.excel_thread.finished.connect(self._clear_excel_worker)
        self.excel_thread.start()

    @QtCore.Slot(object)
    def _excel_import_finished(self,result):
        if self.excel_progress: self.excel_progress.close()
        msg=f"إضافة: {result['added']} | تحديث: {result['updated']} | تخطي: {result.get('skipped',0)} | أخطاء: {result['failed']}"
        if result.get("cancelled"): msg += "\nتم إيقاف العملية بواسطة المستخدم."
        if result["errors"]:
            out,_=QtWidgets.QFileDialog.getSaveFileName(self,"تصدير الأخطاء","import_errors.xlsx","Excel (*.xlsx)")
            if out:
                try: export_errors(out,result["errors"])
                except Exception as e: QtWidgets.QMessageBox.warning(self,"تحذير",str(e))
        QtWidgets.QMessageBox.information(self,"نتيجة الاستيراد",msg)
        self.refresh_all()

    @QtCore.Slot(str)
    def _excel_import_failed(self,error):
        if self.excel_progress: self.excel_progress.close()
        QtWidgets.QMessageBox.critical(self,"فشل الاستيراد",error)

    def _clear_excel_worker(self):
        if self.excel_worker: self.excel_worker.deleteLater()
        if self.excel_thread: self.excel_thread.deleteLater()
        self.excel_worker=None; self.excel_thread=None; self.excel_progress=None

    def export_excel(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,"تصدير المنتجات","products.xlsx","Excel (*.xlsx)")
        if path:
            try:export_products(path);QtWidgets.QMessageBox.information(self,"تم","تم تصدير المنتجات.")
            except Exception as e:QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def backup(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,"حفظ Backup","shop_backup.db","SQLite (*.db)")
        if path:
            try:backup_to(path);QtWidgets.QMessageBox.information(self,"تم","تم إنشاء النسخة الاحتياطية.")
            except Exception as e:QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def restore(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,"اختيار Backup","","SQLite (*.db *.sqlite)")
        if not path:return
        if QtWidgets.QMessageBox.question(self,"تحذير","سيتم أخذ Backup تلقائي ثم استبدال القاعدة الحالية. متابعة؟")!=QtWidgets.QMessageBox.Yes:return
        try:restore_from(path);QtWidgets.QMessageBox.information(self,"تم","تمت الاستعادة. أعد تشغيل البرنامج.");QtWidgets.QApplication.quit()
        except Exception as e:QtWidgets.QMessageBox.critical(self,"خطأ",str(e))

    def import_db(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,"استيراد Database","","SQLite (*.db *.sqlite)")
        if not path:return
        try:
            info=inspect_database(path)
            if QtWidgets.QMessageBox.question(self,"تأكيد",f"القاعدة تحتوي على {info['products']} منتج و{info['categories']} تصنيف.\nاستبدال القاعدة الحالية؟")!=QtWidgets.QMessageBox.Yes:return
            import_database(path);QtWidgets.QMessageBox.information(self,"تم","تم الاستيراد. أعد تشغيل البرنامج.");QtWidgets.QApplication.quit()
        except Exception as e:QtWidgets.QMessageBox.critical(self,"فشل الاستيراد",str(e))

class ProductEditDialog(QtWidgets.QDialog):
    def __init__(self,p,categories,parent=None):
        super().__init__(parent);self.p=p;self.setWindowTitle("تعديل المنتج");self.resize(520,600)
        form=QtWidgets.QFormLayout(self);self.w={}
        vals={"اسم المنتج":p.name,"Barcode":p.barcode or "","SKU":p.sku or "","الماركة":p.brand or "",
              "سعر الشراء":str(p.purchase_price),"سعر البيع":str(p.sale_price),"الكمية":str(p.quantity),
              "الوحدة":p.unit,"الحد الأدنى":str(p.min_stock),"ملاحظات":p.notes or ""}
        for k,v in vals.items():
            self.w[k]=QtWidgets.QLineEdit(v);form.addRow(k+":",self.w[k])
        self.cat=QtWidgets.QComboBox()
        self.cat.addItem("بدون تصنيف",None)
        for c in categories:self.cat.addItem(c.name,c.id)
        idx=self.cat.findData(p.category_id)
        if idx>=0:self.cat.setCurrentIndex(idx)
        form.addRow("التصنيف:",self.cat)
        bb=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save|QtWidgets.QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept);bb.rejected.connect(self.reject);form.addRow(bb)
    def data(self):
        try:
            dec=lambda k:Decimal(self.w[k].text() or "0")
            return {"name":self.w["اسم المنتج"].text().strip(),"barcode":self.w["Barcode"].text().strip() or None,
                    "sku":self.w["SKU"].text().strip() or None,"brand":self.w["الماركة"].text().strip() or None,
                    "purchase_price":dec("سعر الشراء"),"sale_price":dec("سعر البيع"),"quantity":dec("الكمية"),
                    "unit":self.w["الوحدة"].text() or "قطعة","min_stock":dec("الحد الأدنى"),
                    "notes":self.w["ملاحظات"].text() or None,"category_id":self.cat.currentData()}
        except InvalidOperation as e:raise ValueError("أحد الحقول الرقمية غير صالح.") from e

class SaleDialog(QtWidgets.QDialog):
    def __init__(self,product,parent=None):
        super().__init__(parent)
        self.setWindowTitle("تسجيل بيع")
        self.setMinimumWidth(420)
        available=Decimal(str(product.quantity))
        form=QtWidgets.QFormLayout(self)
        name=QtWidgets.QLabel(f"{product.name}  —  المتاح: {available:g} {product.unit}")
        name.setStyleSheet("font-weight:700;")
        self.qty_spin=QtWidgets.QDoubleSpinBox(); self.qty_spin.setDecimals(3)
        self.qty_spin.setRange(0.001,999_999.999); self.qty_spin.setValue(min(1.0,float(available)))
        self.price_spin=QtWidgets.QDoubleSpinBox(); self.price_spin.setDecimals(2)
        self.price_spin.setRange(0,99_999_999.99); self.price_spin.setValue(float(product.sale_price))
        self.total_lbl=QtWidgets.QLabel("—"); self.total_lbl.setObjectName("priceBig")
        form.addRow("المنتج:",name)
        form.addRow("الكمية:",self.qty_spin)
        form.addRow("سعر الوحدة:",self.price_spin)
        form.addRow("الإجمالي:",self.total_lbl)
        bb=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("تأكيد البيع")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("إلغاء")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.qty_spin.valueChanged.connect(self._update_total)
        self.price_spin.valueChanged.connect(self._update_total)
        self._update_total()
        self.qty_spin.selectAll(); self.qty_spin.setFocus()
    def _update_total(self):
        self.total_lbl.setText(f"{self.total():,.2f} جنيه")
    def quantity(self): return Decimal(str(self.qty_spin.value()))
    def price(self): return Decimal(str(self.price_spin.value()))
    def total(self): return (self.quantity()*self.price()).quantize(Decimal("0.01"))


# MyShop — نظام إدارة منتجات وأسعار ومخزون لمحل أدوات صحية

Version 1.1.0

## الفكرة

MyShop تطبيق Windows مكتبي يعمل Offline، ويفصل البرنامج عن البيانات. لا توجد قائمة منتجات داخل كود Python؛ كل المنتجات والأسعار والمخزون والتصنيفات محفوظة في SQLite.

**مهم:** النسخة الافتراضية تستخدم `%LOCALAPPDATA%\MyShop\data\shop.db` لأن الكتابة داخل `Program Files` قد تكون مقيدة. وللنقل السهل يمكن تفعيل Portable Mode بإنشاء ملف فارغ اسمه `portable.flag` بجانب `MyShop.exe`، وعندها سيستخدم البرنامج `data\shop.db` بجانب البرنامج.

## A. تشغيل المشروع أثناء التطوير

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Python 3.10+ وPySide6 موصى بهما رسميًا، والـ wheel يتضمن Qt binaries فلا تحتاج لتثبيت Qt منفصل.

## B. Dependencies

```bat
pip install -r requirements.txt
```

## C. تشغيل البرنامج

```bat
python run.py
```

في أول تشغيل ستظهر شاشة إنشاء حساب المدير. اختر كلمة مرور قوية. لا توجد كلمة مرور Admin ثابتة داخل الكود.

## D. إنشاء Database

إذا لم توجد قاعدة البيانات، ينشئ البرنامج المجلدات والجداول تلقائيًا. يوجد جدول `app_meta` لإصدار الـ schema، والبرنامج ينفذ migrations بسيطة وآمنة قبل التشغيل.

## E. إضافة منتج يدويًا

سجّل دخولك كـ Admin ثم افتح "إضافة منتج". Barcode اختياري، لكن إذا أُدخل فلا يمكن تكراره.

## F. إنشاء Excel Template

من "استيراد/تصدير Excel" اضغط "تحميل نموذج Excel". الملف يحتوي ورقة `products` وورقة `instructions`.

## G. ملء Excel

الأعمدة:
- اسم المنتج
- Barcode
- SKU
- التصنيف
- الماركة
- سعر الشراء
- سعر البيع
- الكمية
- الوحدة
- الحد الأدنى
- ملاحظات

## H. Import Excel

يقرأ البرنامج الصفوف، يتحقق من الأرقام والحقول، ويمنع تكرار Barcode. إذا كان Barcode موجودًا في قاعدة البيانات يمكنك اختيار:
- تحديث الموجود
- تجاهل الموجود
- تحديث الأسعار فقط
- إلغاء

يتم الاستيراد داخل transaction مع savepoint لكل صف، لذلك الصف الخاطئ لا يلغي الصفوف الصحيحة. يظهر Progress Bar ويمكن إلغاء العملية، ويعمل الاستيراد في Worker Thread حتى لا تتجمد الواجهة. يتم تسجيل تغييرات الأسعار والمخزون الناتجة عن الاستيراد في السجلين المخصصين لهما.

## I. تصدير المنتجات إلى Excel

من نفس الصفحة اختر "تصدير المنتجات".

## J. Backup Database

"Backup" يأخذ نسخة متسقة من SQLite إلى المكان الذي تختاره. يفضل الاحتفاظ بنسخ متعددة وعلى وسيط منفصل.

## K. Restore Database

البرنامج يتحقق من أن الملف SQLite صالح وأن الجداول الأساسية موجودة، يأخذ backup تلقائيًا من القاعدة الحالية، ثم يستبدلها ويعيد فتحها.

## L. Import Database

من "استيراد قاعدة بيانات" اختر ملف `.db` أو `.sqlite`. يعرض البرنامج عدد المنتجات والتصنيفات قبل التأكيد. لا يتم الاستيراد إذا كان الـ schema غير متوافق.

## M. نقل Database لجهاز آخر

على الجهاز القديم:
1. Backup.
2. انسخ `shop_backup.db` إلى USB.

على الجهاز الجديد:
1. ثبّت MyShop.
2. سجّل دخولك.
3. Import Database.
4. اختر النسخة الاحتياطية.
5. بعد التأكيد ستظهر المنتجات والأسعار والمخزون والتصنيفات وسجل الأسعار والمستخدمون.

## N. إنشاء EXE

تم تجهيز `MyShop.spec` و`build.bat` لبناء نسخة Windows `onedir`. PyInstaller يدعم `onedir` كحزمة مجلد واحدة، ويمكن للمستخدم تشغيلها بدون Python أو تثبيت المكتبات. بناء Windows يجب تنفيذه على Windows لأن PyInstaller ليس cross-compiler.


استخدم:

```bat
build.bat
```

بعد البناء ستجد:

```text
dist\MyShop\MyShop.exe
```

النسخة الافتراضية هي **onedir** وليس onefile. هذا أفضل لهذا المشروع لأن PySide6 تطبيق كبير نسبيًا، ولأن قاعدة البيانات يجب أن تبقى خارج ملفات البرنامج. PyInstaller يجعل onedir هو الخيار الافتراضي، بينما onefile يفك محتويات التطبيق عند التشغيل.

## O. Installer

تم تجهيز `build_installer.bat` ليبني الـ EXE ثم يمرره إلى Inno Setup. إذا كان Inno Setup مثبتًا:

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\MyShop.iss
```

الـ installer يثبت البرنامج في Program Files ويترك بيانات المستخدم في LocalAppData. تحديث البرنامج لا يحذف قاعدة البيانات.

## P. تثبيت البرنامج على جهاز المحل

ثبّت `MyShopSetup.exe`، ثم شغّل البرنامج. في أول تشغيل أنشئ Admin. بعد ذلك استورد قاعدة المنتجات من Excel أو قاعدة SQLite جاهزة.

## Q. تحديث البرنامج

لا تحذف مجلد `%LOCALAPPDATA%\MyShop`. المثبت يحدّث ملفات البرنامج فقط. قبل أي تحديث مهم خذ Backup.

## R. نقل البرنامج لجهاز جديد

استخدم Backup Database ثم Import Database على الجهاز الجديد. لا تحتاج إلى نسخ ملفات Python أو تثبيت Python عند استخدام EXE.

## S. Barcode Scanner

اختر Barcode Scanner يدعم **USB HID Keyboard / Keyboard Emulation**. غالبًا لا يحتاج Driver خاصًا؛ الكمبيوتر يتعامل معه كلوحة مفاتيح. حقل البحث في MyShop هو نقطة الاستقبال: عند فتح البرنامج يكون عليه Focus، اعمل Scan، ثم Enter إذا كان الجهاز مضبوطًا على إرسال Enter بعد القراءة. إذا كان Barcode موجودًا سيظهر أول منتج مطابق وتُفتح تفاصيله. **مهم:** إذا كانت الباركودات تحتوي أصفارًا في البداية، يجب أن تكون خلايا Barcode في Excel نصية؛ نموذج MyShop يضبط العمود على Text.

## صلاحيات المستخدمين

- Admin: كل الصلاحيات.
- Employee: البحث وعرض المنتجات والأسعار فقط.

كلمات المرور لا تُخزن كنص؛ يستخدم البرنامج `hashlib.scrypt` مع Salt عشوائي.

## Database Schema

الجداول الأساسية:
- users
- categories
- products
- price_history
- stock_movements
- app_meta

Indexes موجودة على Barcode وSKU واسم المنتج والتصنيف.

## لماذا SQLAlchemy؟

تم اختيار SQLAlchemy لعزل طبقة البيانات عن الواجهة وإتاحة التطوير مستقبلًا. SQLite تظل ملفًا محليًا واحدًا، ويمكن نقله ونسخه بسهولة.

## ملاحظات هندسية

- لا تعتمد على الإنترنت.
- لا توجد بيانات منتجات hard-coded.
- يوجد فصل بين UI / Services / Database.
- العمليات الثقيلة مثل Excel تستخدم `QThread` حتى لا تتجمد الواجهة.
- Backup قبل Restore وImport Database.
- يوجد schema versioning بسيط ويمكن توسيعه إلى Alembic لاحقًا إذا أصبحت migrations أكثر تعقيدًا.

## الاختبار

يوجد `tests/test_core.py` لاختبار:
- إنشاء قاعدة البيانات
- المستخدم وكلمة المرور
- إضافة المنتج
- منع Barcode المكرر
- تغيير السعر وتسجيل Price History
- Low Stock
- ترقية schema الأساسية

تشغيل الاختبارات:

```bat
pip install pytest
pytest -q
```

## المصادر الرسمية

- Qt for Python / PySide6: https://doc.qt.io/qtforpython-6/
- SQLAlchemy SQLite: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- PyInstaller: https://pyinstaller.org/en/latest/usage.html
- openpyxl: https://openpyxl.readthedocs.io/
- SQLite: https://sqlite.org/docs.html


## Production Release

Run the validation before building:

```bat
python scripts\validate_production.py
pytest -q
```

Then build the Windows distribution:

```bat
build.bat
```

For the installer:

```bat
build_installer.bat
```

Production data is intentionally separated from the application installation directory.
Use `portable.flag` only when you explicitly want portable mode.

See `PRODUCTION_CHECKLIST.md` for the final release and smoke-test procedure.

# MyShop — Production Checklist

## Before release
- [ ] Run `python scripts/validate_production.py`
- [ ] Run `pytest -q`
- [ ] Test a clean database on a fresh Windows user profile.
- [ ] Test Excel import with a large file.
- [ ] Test duplicate Barcode/SKU behavior.
- [ ] Test Barcode scanner with Enter suffix.
- [ ] Test Admin and Employee permissions.
- [ ] Test Backup and Restore.
- [ ] Test Database Import on a copy of production data.
- [ ] Test portable mode with `portable.flag`.
- [ ] Build with PyInstaller on Windows.
- [ ] Test the generated EXE on a machine without Python.
- [ ] Build and test the Inno Setup installer.
- [ ] Verify application data is stored outside Program Files.
- [ ] Verify logs are written to the application data directory.

## Release artifact
Recommended release folder:

```text
MyShop/
  MyShop.exe
  data/
  portable.flag        # only for portable distribution
```

For an installed copy, do not ship the production database inside Program Files.
The database should live in the per-user application data directory.

## Smoke test
1. Start the application.
2. Login as Admin.
3. Create a category.
4. Add a product with Barcode `001234`.
5. Search/scan `001234`.
6. Edit sale price and confirm price history.
7. Adjust stock and confirm stock movement.
8. Select multiple products and apply a bulk price change.
9. Export to Excel.
10. Import the exported file into a test database.
11. Create a backup.
12. Restore the backup.
13. Login as Employee and verify restricted actions.

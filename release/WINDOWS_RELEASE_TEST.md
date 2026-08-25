# MyShop Windows Release Test

Run on a clean Windows 10/11 machine.

- [ ] Install `MyShopSetup.exe`.
- [ ] Launch MyShop and verify first-run database/log setup.
- [ ] Login as Admin.
- [ ] Create a category and a product with Barcode `001234`.
- [ ] Search/scan `001234` and verify the product opens.
- [ ] Change the sale price and verify Price History.
- [ ] Adjust stock and verify Stock Movement.
- [ ] Run a bulk price update and verify history.
- [ ] Export products to Excel.
- [ ] Import an Excel file with valid and invalid rows and verify the error report.
- [ ] Create a backup, change data, then restore and verify the old data returns.
- [ ] Login as Employee and verify restricted admin actions.
- [ ] Test upgrade over the previous version without losing user data.
- [ ] Uninstall and verify installed binaries are removed according to policy.
- [ ] Test portable mode with `portable.flag`.

Release only after all checks pass on real Windows hardware.

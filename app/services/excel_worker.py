from PySide6 import QtCore
from app.services.excel_service import import_products, export_products, make_template, export_errors

class ExcelImportWorker(QtCore.QObject):
    progress = QtCore.Signal(int)
    finished = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, path, mode):
        super().__init__(); self.path = path; self.mode = mode; self._cancelled = False

    @QtCore.Slot()
    def run(self):
        try:
            result = import_products(self.path, self.mode, self.progress.emit, lambda: self._cancelled)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self): self._cancelled = True

class ExcelExportWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    def __init__(self, path): super().__init__(); self.path=path
    @QtCore.Slot()
    def run(self):
        try: export_products(self.path); self.finished.emit(self.path)
        except Exception as exc: self.failed.emit(str(exc))

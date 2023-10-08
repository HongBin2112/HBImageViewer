from os.path import splitext

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QFileDialog,
)

from .ui_hb_dialog_load import Ui_HBDialogLoad

class HBDialogLoad(QDialog):

    loaded = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = Ui_HBDialogLoad()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._old_pos: QPointF = QPointF()

        self._connect_events()

    def load(self):
        text_files_path = self.ui.textFilePath.toPlainText()
        if not text_files_path:
            return

        filepaths = text_files_path.split("\n")
        self.loaded.emit(filepaths)
        self.close()

    def select_files(self):
        select_files_paths = self._select_files()
        if select_files_paths:
            images_path = "\n".join(select_files_paths)
            self.ui.textFilePath.setPlainText(images_path)   

    def _connect_events(self):
        self.ui.lineTop.mousePressEvent = self._begin_drag_window
        self.ui.lineTop.mouseMoveEvent = self._process_drag_window

        self.ui.btnLoad.clicked.connect(self.load)
        self.ui.btnSelect.clicked.connect(self.select_files)
        self.ui.btnCancel.clicked.connect(self.close)

    def _begin_drag_window(self: QWidget, event: QMouseEvent):
        self._old_pos: QPointF = event.globalPosition()

    def _process_drag_window(self: QWidget, event: QMouseEvent):
        delta: QPointF = event.globalPosition() - self._old_pos
        self.move(self.pos() + delta.toPoint())
        self._old_pos = event.globalPosition()

    def _select_files(self) -> tuple[str]:
        """ (select mutiple files) This funciton will open a QFileDialog,
        and return the selected files' path.
        """
        files_dialog = QFileDialog(self)
        files_path, _ = files_dialog.getOpenFileNames(
            self,
            "Select Image",
            "./",
            "All Files(*);;Images (*.png *.bmp *.jpg *.jpeg);;Text File (*.txt)"
            )
        if not files_path:
            return []

        result = []
        for fp in files_path:
            if splitext(fp)[1] == ".txt":
                with open(fp) as f:
                    result.extend(f.read().splitlines())
            else:
                result.append(fp)

        return result

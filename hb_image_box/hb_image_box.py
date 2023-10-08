from os.path import isfile
from typing import Union, Sequence, Callable

from PIL import ImageQt, Image
from PySide6.QtCore import (
    Signal,
    Qt,
    QPoint,
    QRect,
    QMimeData,
    QUrl
)
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QWheelEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QAction,
    QUndoStack,
    QKeySequence,
    QShortcut,
    QUndoCommand
)
from PySide6.QtWidgets import (
    QLabel,
    QFileDialog,
    QMessageBox,
    QApplication,
    QMenu,
    QSizePolicy
)

from hbimage import HBImage
from hbimage.hbimage import is_url
from .command import (
    CommandCropImage,
    CommandRotateImage,
)

class HBImageBox(QLabel):

    image_loaded: Signal = Signal(HBImage)
    image_deleted: Signal = Signal()
    image_processed: Signal = Signal()


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        self._hbimage: "HBImage" = None
        self._scale_factor: float = 1.0
        self._displayed_image: QImage = None
        self._displayed_rect: QRect = QRect()

        self._poi_start: QPoint = QPoint()
        self._poi_end: QPoint = QPoint()
        self._roi_selecting: bool = False

        self.menu_process = QMenu(self)
        self._actions: Sequence[QAction] = []
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(6)

        self._add_actions()
        self._set_actions()
        self._set_shortcuts()

        self.set_init_image("./assets/dragImage128.png")
        self.menu_process.setStyleSheet("""
            background-color: #028C6A; /* 設定綠色背景 */
            color: white; /* 設定文字顏色為白色 */
            selection-background-color: #555; /* 設定選擇項目的背景顏色 */
        """)

    @property
    def scale_factor(self) -> float:
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, factor: float):
        self._scale_factor = factor

    @property
    def is_empty(self) -> bool:
        return not self._hbimage

    @property
    def image(self) -> HBImage:
        return self._hbimage

    # ==================================================================

    def select_image(self):
        """This funciton will open a QFileDialog and show image."""
        image_filter = "Image Files (*.png *.bmp *.jpg *.jpeg);;All Files (*)"
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Image", "./", image_filter)

        if filepath:
            return self.load_image(filepath)

    def load_image(self, source: Union[str, Image.Image], info: Union[dict, None] = None):
        try:
            self.set_image(HBImage(source, info))
            self.show_image()
            self.image_loaded.emit(self._hbimage)
        except Exception as e:
            QMessageBox.warning(self, "Load Image Error", str(e))

    def set_image(self, hbimage, reset: bool = True):
        if not isinstance(hbimage, HBImage):
            raise TypeError("Only can set HBImage type image.")

        self._hbimage = hbimage
        self._displayed_image: QImage = hbimage.qt_image
        self._displayed_rect = self._displayed_image.rect()
        if reset:
            self._scale_factor: float = 1.0
        self._poi_start: QPoint = QPoint()
        self._poi_end: QPoint = QPoint()
        self._undo_stack.setClean()

    def copy_image_to_clipboard(self):
        if self.is_empty:
            return None
        clipboard = QApplication.clipboard()
        data = QMimeData()
        data.setImageData(QImage(self._hbimage.crop().qt_image))
        clipboard.setMimeData(data)

    def load_image_from_clipboard(self):
        # https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            pil_image = ImageQt.fromqimage(QImage(mime_data.imageData()))
            self.load_image(pil_image, {"filepath": "Clipboard"})
        elif mime_data.hasText():
            text = mime_data.text()
            if is_url(text):
                self.load_image(text)

    def show_image(self):
        """Displays the loaded image with scaling.

        This method scales the image according to the `_scale_factor` and displays it in the widget.
        """
        if self.is_empty:
            self.setText(" ")
            return
        try:
            scaled_w = self._scale_factor * self._hbimage.size[0]
            scaled_h = self._scale_factor * self._hbimage.size[1]
            scale_mode = Qt.AspectRatioMode.KeepAspectRatio
            scale_filter = Qt.TransformationMode.SmoothTransformation

            img = self._displayed_image.scaled(scaled_w, scaled_h, scale_mode, scale_filter)
            img = QPixmap.fromImage(img)
            self._displayed_rect = img.rect()
            self.setPixmap(img)
            self.adjustSize()
            self.update()
        except Exception as e:
            QMessageBox.warning(self, "Show Image Error", str(e))

    def save_image(self):
        if self.is_empty:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            f"./{self._hbimage.filename}",
            "All Files (*);;Images (*.png *.bmp *.jpg *.jpeg)"
        )
        if not filepath:
            return

        try:
            self._hbimage.save(filepath)
        except Exception as e:
            QMessageBox.warning(self, "Save Image Error", str(e))

    def delete_image(self):
        if self.is_empty:
            QMessageBox.warning(self, "Delete Image Error", "There is no image!")
            return

        sure_delete = QMessageBox.question(
            self, 
            'Message', 
            'Are you sure you delete this image?',
            QMessageBox.StandardButton.Yes, 
            QMessageBox.StandardButton.No)

        if sure_delete == QMessageBox.StandardButton.No:
            return

        self._hbimage: "HBImage" = None
        self._scale_factor: float = 1.0
        self._displayed_image: QImage = None
        self._displayed_rect: QRect = QRect()
        self._poi_start: QPoint = QPoint()
        self._poi_end: QPoint = QPoint()
        self._undo_stack.setClean()
        self.update()
        self.show_image()
        self.image_deleted.emit()
        #self.set_init_image("./assets/dragImage128.png")

    def draw_rect(self, rect: tuple[int, int, int, int], pen: QPen = None):
        x0, y0, x1, y1 = rect
        self._poi_start = QPoint(x0, y0)
        self._poi_end = QPoint(x1, y1)
        self.update()

    def set_init_image(self, fp):
        try:
            _init_img = QImage(fp)
            self.setPixmap(QPixmap.fromImage(_init_img))
            self.resize(500, 500)
        except Exception:
            self.resize(500, 500)

    # ==================================================================

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handles wheel scrolling events for image scaling."""
        super().wheelEvent(event)
        ZOOM_INCREMENT = 0.1

        ctrl_pressed = event.modifiers() == Qt.KeyboardModifier.ControlModifier
        if not ctrl_pressed: 
            return

        wheel_angle = event.angleDelta().y()
        pre_factor = self._scale_factor
        if wheel_angle > 0:
            self._scale_factor += ZOOM_INCREMENT
        elif wheel_angle < 0:
            self._scale_factor -= ZOOM_INCREMENT

        self._scale_factor = max(0.1, self._scale_factor)
        _poi_factor = self._scale_factor / pre_factor
        self._poi_start *= _poi_factor
        self._poi_end *= _poi_factor
        self.show_image()
        self.update()

    # Drag and Drop: https://doc.qt.io/qtforpython-6/overviews/dnd.html#drag-and-drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    # Loading images into the HBImageBox widget from drag-and-drop.
    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            return False
        filepath = event.mimeData().urls()[0] 
        if filepath.isLocalFile():
            filepath = filepath.toLocalFile()
        else:
            filepath = filepath.toString()
        self.load_image(filepath)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        ctrl_pressed = event.modifiers() == Qt.KeyboardModifier.ControlModifier

        if event.button() == Qt.MouseButton.LeftButton and self._hbimage:
            self._roi_selecting = True
            self._poi_start = event.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self.menu_process.exec(self.mapToGlobal(event.pos()))
        elif event.button() == Qt.MouseButton.MiddleButton and ctrl_pressed:
            self._scale_factor = 1.0
            self.show_image()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._roi_selecting:
            self._poi_end = event.pos()
            self.repaint()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._roi_selecting:
            self._poi_end = event.pos()
            #self.update()
            _rect = QRect(self._poi_start, self._poi_end).normalized()
            self._hbimage.set_roi(_rect.getCoords() , (1 / self._scale_factor))
            self._roi_selecting = False

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._roi_selecting:
            self._paint_roi()

    # ==================================================================

    def _paint_roi(self):
        _rect = QRect(self._poi_start, self._poi_end).normalized()
        if _rect.isNull() or (self._poi_start == self._poi_end):
            return

        # Adjust display rect because the line will be drawn outside the box by 1 pixel.
        _dis_rect = self._displayed_rect.adjusted(0,0,-1,-1)
        with QPainter(self) as painter:
            _pen = QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DashLine)
            painter.setPen(_pen)
            painter.drawRect(_rect.intersected(_dis_rect))

    def _add_actions(self):
        self.action_load = QAction("Load", self)
        self.action_crop = QAction("Crop", self)
        self.action_rotate = QAction("Rotate", self)
        self.action_copy = QAction("Copy", self)
        self.action_paste = QAction("Paste", self)
        self.action_save = QAction("Save", self)
        self.action_delete = QAction("Delete", self)
        self.action_undo = QAction("Undo", self)
        self.action_redo = QAction("Redo", self)

        self.action_undo.setEnabled(False)
        self.action_redo.setEnabled(False)

        self._actions = (
            self.action_load,
            self.menu_process.addSeparator(),
            self.action_crop,
            self.action_rotate,
            self.menu_process.addSeparator(),
            self.action_copy,
            self.action_paste,
            self.menu_process.addSeparator(),
            self.action_save,
            self.action_delete,
            self.menu_process.addSeparator(),
            self.action_undo,
            self.action_redo,
        )
        self.menu_process.addActions(self._actions)

    def _make_image_action_fn(self, command: QUndoCommand):
        def image_action_fn():
            self._undo_stack.push(command(self, self._hbimage))
        return image_action_fn

    def _set_actions(self):
        self._undo_stack.canRedoChanged.connect(self.action_redo.setEnabled)
        self._undo_stack.canUndoChanged.connect(self.action_undo.setEnabled)

        self.action_load.triggered.connect(self.select_image)
        self.action_crop.triggered.connect(self._make_image_action_fn(CommandCropImage))
        self.action_rotate.triggered.connect(self._make_image_action_fn(CommandRotateImage))
        self.action_copy.triggered.connect(self.copy_image_to_clipboard)
        self.action_paste.triggered.connect(self.load_image_from_clipboard)
        self.action_save.triggered.connect(self.save_image)
        self.action_delete.triggered.connect(self.delete_image)
        self.action_undo.triggered.connect(self._undo_stack.undo)
        self.action_redo.triggered.connect(self._undo_stack.redo)

    def _add_shortcut(self, action: QAction, shortcut):
        action.setShortcut(shortcut)
        shortcut = QShortcut(shortcut, self)
        shortcut.activated.connect(action.trigger)

    def _set_shortcuts(self):
        std_key = QKeySequence.StandardKey
        shortcuts = (
            std_key.Open,
            QKeySequence(Qt.Key.Key_C),
            QKeySequence(Qt.Key.Key_O),
            std_key.Copy,
            std_key.Paste,
            std_key.Save,
            std_key.Delete,
            std_key.Undo,
            std_key.Redo,
        )

        # get actions exclude separators.
        actions = (act for act in self._actions if not act.isSeparator()) 
        for act, sc in zip(actions, shortcuts):
            self._add_shortcut(act, sc)



from os.path import splitext
from typing import Union

from PySide6.QtCore import Qt, QSize, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QMessageBox,
    QMainWindow,
    QFileDialog,
)


from hb_dialog_load import HBDialogLoad
from hbimage import HBAlbum, HBImage
from .ui_hb_main_window import Ui_HBMainWindow
from . import widget_effect


class HBMainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_HBMainWindow()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.hbalbum: HBAlbum = HBAlbum()
        self.image_box = self.ui.WidgetHBImageBox
        self._menu_btns = (
            self.ui.btnImageInfos,
            self.ui.btnLoad,
            self.ui.btnSave,
            self.ui.btnSaveAll,
            self.ui.btnExit,
            self.ui.btnNext,
            self.ui.btnPrevious,
        )

        self.ui.widgetMenu.hide()
        self._set_shadow()
        self._set_animation()
        self._connect_events()

    # ==================================================================

    def load_images(self):
        self.dialog_load = HBDialogLoad()
        self.dialog_load.loaded.connect(self._load_images)
        self.dialog_load.exec()

    def save_images(self):
        if self.hbalbum.is_empty:
            return None

        folder_path = QFileDialog.getExistingDirectory(self, "Choose Save Folder", "./")
        if not folder_path:
            return

        self.hbalbum.save(folder_path)
        message = f"Images saved successfully to:\n{folder_path}\n\nSaved Files:\n"
        message += "\n".join(self.hbalbum.filenames)
        QMessageBox.information(self, "Save Images", message)

    def add_image(self, hbimage: HBImage):
        self.hbalbum.append(hbimage)
        self.hbalbum.bookmark = len(self.hbalbum)
        self.set_image(self.hbalbum.bookmark_image)

    def set_image(self, hbimage: HBImage):
        self.image_box.set_image(hbimage)
        self.image_box.show_image()
        self.update_image_info()
        self._update_menu_btns_enable()

    def delete_image(self, index: int = None):
        if self.hbalbum.is_empty:
            raise FileNotFoundError("Try to delete nothing.")

        self.hbalbum.delete(self.hbalbum.bookmark)
        if self.hbalbum.is_empty:
            self.update_image_info()
            self._update_menu_btns_enable()
            self.image_box.set_init_image("./assets/dragImage128.png")
            return
        self.set_image(self.hbalbum.bookmark_image)

    def update_image_info(self):
        if self.image_box.is_empty:
            self.ui.lineEditName.setText("")
            self.ui.lineEditWidth.setText("")
            self.ui.lineEditHeight.setText("")
            self.ui.lineEditPage.setText("-")
            return None

        img = self.image_box.image
        filename = img.filename
        width, height = img.size
        
        self.ui.lineEditName.setText(f"{filename}")
        self.ui.lineEditWidth.setText(f"{width}")
        self.ui.lineEditHeight.setText(f"{height}")
        self.ui.lineEditPage.setText(f"{self.hbalbum.bookmark + 1}")

    def set_album_page(self, page: Union[str, int, None] = None):
        if self.image_box.is_empty:
            self.update_image_info()
            return

        page = page or self.ui.lineEditPage.text().strip()
        try:
            page = int(page)
            self.hbalbum.bookmark = page - 1
        except Exception:
            self.hbalbum.bookmark = len(self.hbalbum) - 1
        self.set_image(self.hbalbum.bookmark_image)

    def modify_image_name(self):
        new_value = self.ui.lineEditName.text().strip()
        if new_value == "" or self.image_box.is_empty:
            self.update_image_info()
            return

        name, extension = splitext(new_value)
        if not extension:
            new_value = name + splitext(self.image_box.image.filename)[1]
        self.image_box.image.filename = new_value
        self.update_image_info()

    def toggle_menu_display(self):
        menu = self.ui.widgetMenu
        btn_menu = self.ui.btnMenu

        if menu.isHidden():
            self.ui.widgetMenu.animations["show_menu"].start()
            btn_menu.animations["show_menu"].start()
            menu.show()
        else:
            self.ui.widgetMenu.animations["hide_menu"].start()
            btn_menu.animations["hide_menu"].start()
            self.ui.widgetMenu.animations["hide_menu"].finished.connect(menu.hide)

    def toggle_window_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ==================================================================

    def _load_images(self, filepaths: list[str]) -> None:
        if not filepaths:
            return None
        try:
            if self.hbalbum.is_empty:
                self.hbalbum.load(filepaths)
                self.hbalbum.bookmark = 0
            else:
                self.hbalbum.extend(HBAlbum(filepaths))
                self.hbalbum.bookmark = len(self.hbalbum) - 1
        except Exception as e:
            QMessageBox.warning(self, "Set Image Error", str(e))
            return None

        self.set_image(self.hbalbum.bookmark_image)

    def _update_after_processed_image(self):
        self.hbalbum[self.hbalbum.bookmark] = self.image_box.image
        self.update_image_info()

    def _begin_drag_window(self, event: QMouseEvent):
        self._old_pos: QPointF = event.globalPosition()

    def _process_drag_window(self, event: QMouseEvent):
        delta: QPointF = event.globalPosition() - self._old_pos
        self.move(self.pos() + delta.toPoint())
        self._old_pos = event.globalPosition()

    def _connect_events(self):
        self.image_box.image_loaded.connect(self.add_image)
        self.image_box.image_processed.connect(self._update_after_processed_image)
        self.image_box.image_deleted.connect(self.delete_image)

        self.ui.btnClose.clicked.connect(self.close)
        self.ui.btnMaxWindow.clicked.connect(self.toggle_window_maximize)
        self.ui.btnMinWindow.clicked.connect(self.showMinimized)

        self.ui.widgetWindowMove.mousePressEvent = self._begin_drag_window
        self.ui.widgetWindowMove.mouseMoveEvent = self._process_drag_window

        self.ui.btnMenu.clicked.connect(self.toggle_menu_display)
        #self.ui.btnImageInfos.clicked.connect(self.ui.hb_image_box.actionInformation.trigger)
        self.ui.btnLoad.clicked.connect(self.load_images)
        self.ui.btnSave.clicked.connect(self.image_box.action_save.trigger)
        self.ui.btnSaveAll.clicked.connect(self.save_images)
        self.ui.btnExit.clicked.connect(self.close)

        self.ui.btnNext.clicked.connect(lambda : self.set_album_page(self.hbalbum.bookmark + 2))
        self.ui.btnPrevious.clicked.connect(lambda : self.set_album_page(self.hbalbum.bookmark))
        self.ui.lineEditPage.returnPressed.connect(self.set_album_page)
        self.ui.lineEditName.returnPressed.connect(self.modify_image_name)

    def _update_menu_btns_enable(self):
        need_update_btns = (
            self.ui.btnImageInfos,
            self.ui.btnSave,
            self.ui.btnSaveAll,
            self.ui.btnExit,
        )
        
        for btn in need_update_btns:
            btn.setEnabled(not self.image_box.is_empty)

        is_no_next_image = self.hbalbum.bookmark == len(self.hbalbum) - 1 or self.hbalbum.is_empty
        is_no_previous_image = self.hbalbum.bookmark == 0
        self.ui.btnNext.setEnabled(not is_no_next_image)
        self.ui.btnPrevious.setEnabled(not is_no_previous_image)

    def _set_shadow(self):
        btns_shadow_args = (2, 3, 10, (50,50,50,64))
        for btn in self._menu_btns:
            widget_effect.add_shadow(btn, self, *btns_shadow_args)

    def _set_animation(self):
        BUTTON_MENU_MIN_SIZE = QSize(70, 40)
        BUTTON_MENU_MAX_SIZE = QSize(110, 40)
        MENU_MAX_WIDTH = 200
        MENU_MIN_WIDTH = 0

        widget_effect.add_animation(
            self.ui.btnMenu,
            name = "show_menu",
            prop = "minimumSize",
            duration = 150,
            startValue = BUTTON_MENU_MIN_SIZE,
            endValue = BUTTON_MENU_MAX_SIZE
        )

        widget_effect.add_animation(
            self.ui.btnMenu,
            name = "hide_menu",
            prop = "minimumSize",
            duration = 200,
            startValue = BUTTON_MENU_MAX_SIZE,
            endValue = BUTTON_MENU_MIN_SIZE
        )

        widget_effect.add_animation(
            self.ui.widgetMenu,
            name = "show_menu",
            prop = "maximumWidth",
            duration = 150,
            startValue = MENU_MIN_WIDTH,
            endValue = MENU_MAX_WIDTH
        )

        widget_effect.add_animation(
            self.ui.widgetMenu,
            name = "hide_menu",
            prop = "maximumWidth",
            duration = 200,
            startValue = MENU_MAX_WIDTH,
            endValue = MENU_MIN_WIDTH
        )

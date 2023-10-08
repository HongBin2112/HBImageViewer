import sys
import os

from PySide6.QtWidgets import QApplication

if __name__ == "__main__":

    os.system(f"pyside6-uic ui/HBMainWindow.ui > hb_main_window/ui_hb_main_window.py")
    os.system(f"pyside6-uic ui/HBDialogLoad.ui > hb_dialog_load/ui_hb_dialog_load.py")
    from hb_main_window import HBMainWindow
    from hb_image_box import HBImageBox

    app = QApplication(sys.argv)
    #box = HBImageBox()
    #box.show()
    #box.load_image("/home/hongbin/Desktop/images/comic_HR.bmp")

    w = HBMainWindow()
    w.show()
    sys.exit(app.exec())

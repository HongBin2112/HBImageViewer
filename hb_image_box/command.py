from PySide6.QtGui import QUndoCommand

#from hb_image_box import HBImageBox
#from memory_profiler import profile

class CommandImageProcess(QUndoCommand):

    def __init__(self, parent, hbimage):
        super().__init__()
        self._hb_image_box: "HBImageBox" = parent
        self.pre_hbimage = hbimage
        self.pre_roi = hbimage.roi

    def _do(self, set_image: "HBImage" = None):
        if not set_image:
            set_image = self.pre_hbimage
        self._hb_image_box.set_image(set_image, False)
        self._hb_image_box.show_image()
        self._hb_image_box.image_processed.emit()

    def redo(self):
        ...

    def undo(self):
        self._do()
        self._hb_image_box.draw_rect(self.pre_roi * self._hb_image_box.scale_factor)



class CommandCropImage(CommandImageProcess):

    def redo(self):
        self._do(self.pre_hbimage.crop())


class CommandRotateImage(CommandImageProcess):

    def redo(self):
        self.pre_hbimage.rotate(90)
        self._do()

    def undo(self):
        self.pre_hbimage.rotate(270)
        self._do()


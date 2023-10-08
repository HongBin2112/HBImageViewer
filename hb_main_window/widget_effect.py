from PySide6.QtGui import QColor
from PySide6.QtCore import (
    QPropertyAnimation,
)
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QWidget,
)

# [PySide6練習筆記] 添加陰影及動畫效果 | https://medium.com/p/83f1d2f888d


def add_animation(widget: QWidget, name: str, prop: str, duration: int, startValue, endValue):
    anim = QPropertyAnimation(widget, prop.encode())
    anim.setDuration(duration)
    anim.setStartValue(startValue)
    anim.setEndValue(endValue)

    if hasattr(widget, 'animations'):
        widget.animations.update({name: anim})
    else:
        widget.animations = {name: anim}


def add_shadow(
    widget: QWidget,
    parent,
    Xoffset: int,
    Yoffset: int,
    BlurRadius: int,
    Color: tuple
    ) -> None:

    widget.shadow = QGraphicsDropShadowEffect(parent)
    widget.shadow.setXOffset(Xoffset)
    widget.shadow.setYOffset(Yoffset)
    widget.shadow.setBlurRadius(BlurRadius)
    widget.shadow.setColor(QColor(*Color))

    widget.setGraphicsEffect(widget.shadow)
from __future__ import annotations
from typing import Union


class Rect:
    """ Represents a rectangular region with coordinates (x0, y0, x1, y1). """

    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(self, *position) -> None:
        if len(position) == 4:
            _pos = position
        elif isinstance(position[0], (tuple, Rect)) and len(position[0]) == 4:
            _pos = position[0]
        else:
            raise ValueError("Rect must be either 4 integers or a tuple of 4 values.")

        _pos = self._check_pos_tuple(_pos)
        self.x0, self.y0, self.x1, self.y1 = _pos
        self.validate()

    def __add__(self, margin: tuple[int, int, int, int]) -> "Rect":
        margin = self._check_pos_tuple(margin)
        return Rect(
            self.x0 + margin[0],
            self.y0 + margin[1],
            self.x1 + margin[2],
            self.y1 + margin[3]
            )

    def __iadd__(self, margin: tuple[int, int, int, int]) -> "Rect":
        margin = self._check_pos_tuple(margin)
        self.x0 += margin[0]
        self.y0 += margin[1]
        self.x1 += margin[2]
        self.y1 += margin[3]
        self.validate()
        return self

    def __mul__(
        self,
        scale: Union[int, float, tuple[float, float, float, float]]
        ) -> "Rect":
        return Rect(self._scale_pos(scale))

    def __imul__(
        self,
        scale: Union[int, float, tuple[float, float, float, float]]
        ) -> "Rect":
        self.x0, self.y0, self.x1, self.y1 = self._scale_pos(scale)
        self.validate()
        return self

    def __repr__(self) -> str:
        """
        Returns:
            str: Rect(x0, y0, x1, y1)
        """
        return f"Rect({self.x0}, {self.y0}, {self.x1}, {self.y1})"

    def __len__(self):
        return 4

    def __getitem__(self, index: int) -> int:
        return (self.x0, self.y0, self.x1, self.y1)[index]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rect):
            return False
        return (self.x0, self.y0, self.x1, self.y1) == (other.x0, other.y0, other.x1, other.y1)

    @property
    def width(self) -> int:
        return abs(self.x1 - self.x0)

    @property
    def height(self) -> int:
        return abs(self.y1 - self.y0)

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def is_valid(self) -> bool:
        """
        Checks if the Rect is not a line or a point (width or height is zero),
        and check if the top-left (x0, y0) are less than the bottom-right (x1, y1).
        """
        return self.x0 < self.x1 and self.y0 < self.y1

    def center(self) -> tuple[int, int]:
        x_center = (self.x0 + self.x1) // 2
        y_center = (self.y0 + self.y1) // 2
        return (x_center, y_center)

    def copy(self) -> "Rect":
        return Rect(self)

    def constrain(self, box: Union[tuple[int, int, int, int], "Rect"]) -> "Rect":
        """ Constrains the Rect within a specified bounding box.

        Args:
            box (Union[tuple[int, int, int, int], "Rect"]): 
            A tuple (x0, y0, x1, y1) or another Rect instance.

        Returns:
            Rect: A new Rect instance that represents the constrained region.
        """
        box = Rect(box)
        if not box.is_valid:
            raise ValueError("Invalid constraint range.")

        x0, y0, x1, y1 = (self.x0, self.y0, self.x1, self.y1)
        x0 = max(x0, box.x0)
        y0 = max(y0, box.y0)
        x1 = min(x1, box.x1)
        y1 = min(y1, box.y1)
        return Rect(x0, y0, x1, y1)

    def validate(self):
        """ Validates and normalizes coordinates (x0, y0, x1, y1):
        - Sets negative values to 0.
        - Swaps x0 and x1 if x0 > x1.
        - Swaps y0 and y1 if y0 > y1.
        """
        x0, y0, x1, y1 = (self.x0, self.y0, self.x1, self.y1)

        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0

        self.x0, self.y0, self.x1, self.y1 = (max(0, x0), max(0, y0), max(0, x1), max(0, y1))

    def _check_pos_tuple(self, pos: tuple) -> tuple[int, int, int, int]:
        """ If input tuple is not valid, then raise Error.

        Args:
            pos (tuple)

        Returns:
            tuple[int, int, int, int]: The validated position tuple.

        Raises:
            ValueError: If the tuple does not contain exactly 4 integers.
            TypeError: If any element in the tuple is not an integer.
        """
        if len(pos) != 4:
            raise ValueError("Tuple must contain exactly 4 integers.")
        if not all(isinstance(p, int) for p in pos):
            raise TypeError("All elements in the tuple must be integers.")
        return pos

    def _scale_pos(
        self,
        scale: Union[int, float, tuple[float, float, float, float]]
        ) -> tuple[int, int, int, int]:
        """ Scales coordinates based on the provided scale factor.

        Args:
            scale (Union[int, float, tuple[float, float, float, float]])
        Returns:
            tuple: A tuple of scaled coordinates (x0, y0, x1, y1).
        """
        if isinstance(scale, (int, float)):
            scale = (scale, scale, scale, scale)
        elif not isinstance(scale, (list, tuple)):
            raise TypeError("Invalid scale type.")
        if len(scale) != 4:
            raise ValueError("Scale must have exactly four elements.")

        return tuple(int(p * factor) for p, factor in zip(self, scale))

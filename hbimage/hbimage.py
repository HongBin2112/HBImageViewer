from __future__ import annotations
import re
from os.path import splitext, basename, exists
from typing import Callable, Union
from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qs

from PIL import (
    Image,
    ImageChops,
    ImageQt
)

from .rect import Rect


class HBImage:

    def __init__(
        self,
        source: Union[str, Image.Image, "HBImage"],
        info: Union[dict, None] = None,
        roi: Union[tuple[int, int, int, int], "Rect", None] = None,
        *,
        headers: Union[dict[str, str], None] = None
        ) -> None:

        self._image: Image.Image = None
        self._roi: "Rect" = Rect(roi) if roi else Rect(0, 0, 0, 0)
        self._info: dict = dict.fromkeys([
            "filename", "filepath"
        ])

        self.load(source, info, headers=headers)

    def _repr_png_(self):
        """ Enables directly display image in a Jupyter Notebook.\n
        Requires the IPython library.
        """
        return self._image._repr_png_()

    def _repr_jpeg_(self):
        return self._image._repr_jpeg_()

    def _process_with_roi(image_process_function: Callable[[HBImage], "HBImage"]):
        """Decorator.\n
        If self.roi is set, the function only modifies this region.
        """
        def do_process(self: "HBImage") -> "HBImage":
            if self.roi.is_valid:
                process_image = image_process_function(self.crop())
                return self.paste(process_image)
            return image_process_function(self)
        return do_process

    # ============================ property ====================================

    @property
    def filename(self) -> str:
        return self._info["filename"]

    @filename.setter
    def filename(self, name):
        self._info.update({"filename": name})

    @property
    def filepath(self) -> str:
        return self._info["filepath"]

    @property
    def format(self) -> str:
        return self._image.format.lower() if self._image else ""

    @property
    def image(self) -> Image.Image:
        return self._image

    @property
    def qt_image(self):
        return ImageQt.ImageQt(self._image)

    @property
    def size(self) -> tuple[int, int]:
        return self._image.size if self._image else (0, 0)

    @property
    def roi(self) -> Rect:
        return self._roi

    @roi.setter
    def roi(self, _roi: tuple[int, int, int, int]):
        self._roi = Rect(_roi).constrain((0, 0, *self.size))

    # ============================ methods ====================================

    def crop(self, box: Union[tuple[int, int, int, int], None] = None) -> "HBImage":
        """Crop the image to the specified region defined by a tuple (x0, y0, x1, y1).\n
        If 'box' is not provided, it crops the Region of Interest (ROI).
        """
        _rect = Rect(box) if box else self.roi

        if not _rect.is_valid:
            return self

        return HBImage(self._image.crop(_rect), self._info.copy())

    def copy(self) -> "HBImage":
        """ This method creates a new HBImage object that is an exact copy of the original,
        including image data, filepath, ROI (Region of Interest), and other attributes.

        Returns:
            HBImage: A new HBImage object that is an exact copy of the original.
        """
        new_image = HBImage(self._image.copy(), self._info.copy(), self.roi.copy())
        return new_image

    def load(
        self,
        source: Union[str, Image.Image, "HBImage"],
        info: Union[dict, None] = None,
        *,
        headers: Union[dict[str, str], None] = None
        ) -> None:
        """
        Args:
            source (Union[str, Image.Image, "HBImage"]): The source of image data.
            info (Union[dict, None]): Additional information about the image (optional).
            headers: if you want to get image from a website.

        Raises:
            TypeError: If the source type is unsupported.
        """
        if isinstance(source, str):
            if is_url(source):
                self._load_from_url(source, headers)
            else:
                self._load_from_path(source)

        elif isinstance(source, Image.Image):
            self._load_from_pil_image(source, info)
        elif isinstance(source, HBImage):
            self = source.copy()
        else:
            raise TypeError(f"Unsupported source type: {type(source)}")

    def save(self, filepath: str = "", format: str = "", **kwargs):
        """ Save the image to a file.

        Args:
            filepath (str, optional): The path to save the image.
            format (str, optional): The file format to use (e.g., "jpg", "png").

        Raises:
            FileExistsError: Raised if a usable filename cannot be found after multiple attempts.
        """
        if not filepath:
            filepath = f"./{self.filename}"
        if format:
            filepath = f"{splitext(filepath)[0]}.{format}"

        # If the specified filename already exists, append _1 until a usable filename is found.
        base_path, extension = splitext(filepath)
        counter = 1
        max_attempts = 100

        while exists(filepath) and counter <= max_attempts:
            filepath = f"{base_path}_{counter}{extension}"
            counter += 1

        if counter > max_attempts:
            raise FileExistsError("File already exists. Unable to find a usable filename.")

        self._image.save(filepath, format, **kwargs)

    def paste(self, other: "HBImage") -> "HBImage":
        """ Pastes another image into this image.\n
        The paste position is determined based on the self.roi (Region of Interest).
        """
        pasted_image = self._image.copy()
        pasted_image.paste(other.image, self.roi)
        return HBImage(pasted_image, self._info.copy(), self.roi)

    def resize(self, size: tuple[int, int], *, resample: Union[int, None] = None) -> "HBImage":
        """ This method primarily utilizes the PIL.Image.Image resize method.\n
        Args:
            size (tuple[int, int]): The new dimensions of the image (width, height)
            resample (int, optional): Integer value representing the resampling method.

            Possible values are from PIL.Image.Resampling:\n
            - 0: Nearest-neighbor sampling.
            - 1: Lanczos windowed sinc interpolation.
            - 2: Bilinear interpolation.
            - 3: Bicubic interpolation.
            - 4: Box sampling.
            - 5: Hamming windowed sinc interpolation.

        Returns:
            HBImage: A new HBImage object with the resized image.
        """
        resized_image = self._image.resize(size, resample)
        return HBImage(resized_image, self._info.copy())

    def scale(
        self,
        factor: Union[int, float, tuple[float, float]],
        *,
        resample: Union[int, None] = None
        ) -> "HBImage":

        if isinstance(factor, (int, float)):
            factor = (factor, factor)
        elif not isinstance(factor, (list, tuple)):
            raise TypeError("Invalid scale type.")
        if len(factor) != 2:
            raise ValueError("Scale must have exactly 2 elements.")

        w = int(self.size[0] * factor[0])
        h = int(self.size[1] * factor[1])
        resized_image = self._image.resize((w, h), resample)
        return HBImage(resized_image, self._info.copy())

    def fit(self, container: tuple[int, int], *, resample: Union[int, None] = None):
        """ Resize the image to fit within the specified container 
        while maintaining its original aspect ratio.

        Args:
            container (tuple[int, int]):
            The dimensions of the container (width, height) to fit the image into.
            resample (int, optional): Integer value representing the resampling method.

        Returns:
            HBImage: A new HBImage object with the resized image.
        """
        container_width, container_height = container
        image_width, image_height = self.size

        width_scale = container_width / image_width
        height_scale = container_height / image_height
        scale_factor = min(width_scale, height_scale)
        new_w = int(image_width * scale_factor)
        new_h = int(image_height * scale_factor)

        resized_image = self._image.resize((new_w, new_h), resample)
        return HBImage(resized_image, self._info.copy())

    def set_roi(self, roi: tuple[int, int, int, int], scale: float = 1.0):
        self.roi = Rect(roi) * scale

    def rotate(self, angle) -> None:
        rotate_img = self._image.rotate(angle, expand=True)
        self._image = rotate_img
        #return HBImage(rotate_img, self._info.copy())

    @_process_with_roi
    def gray(self) -> "HBImage":
        """ Convert the image to grayscale. If the self.roi is set,\n
        only the region of interest (ROI) in the image is turned to grayscale.

        Returns:
            HBImage: A new grayscale HBImage.
        """
        return HBImage(self._image.convert("L"), self._info.copy(), self.roi)

    @_process_with_roi
    def invert_color(self) -> "HBImage":
        inverted_img = ImageChops.invert(self._image)
        return HBImage(inverted_img, self._info.copy(), self.roi)

    # ====================== private methods ================================

    def _fetch_infos(self):
        self._image.format_description

    def _load_from_path(self, filepath: str):
        self._image = Image.open(filepath)
        self._info.update({
            "filename": basename(filepath),
            "filepath": filepath
        })

    def _load_from_url(self, url: str, headers: Union[dict[str, str], None] = None):
        if headers is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"
            }
        req = Request(url, headers=headers)

        parsed_url = urlparse(url)
        url_args = parse_qs(parsed_url.query)
        filename = basename(parsed_url.path)
        file_format = url_args.get("format", "")
        if file_format:
            filename += f".{file_format[0]}"

        self._image = Image.open(urlopen(req))
        self._info.update({
            "filename": filename,
            "filepath": url
        })

    def _load_from_pil_image(self, source: "Image.Image", info: Union[dict, None] = None):
        if info is None:
            info = {}
        self._image = source
        filename_default = "Untitled"
        if source.format:
            filename_default += f".{source.format}"

        self._info.update({
            "filename": info.get("filename", filename_default),
            "filepath": info.get("filepath", "Unknown")
        })


def is_url(string) -> bool:
    url_regex = re.compile(
        r'^(?:http|ftp)s?://'                                                                   # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'    # domain...
        r'localhost|'                                                                           # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'                                                  # ...or ip
        r'(?::\d+)?'                                                                            # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return re.match(url_regex, string) is not None

from __future__ import annotations
import os
from typing import Union, Sequence
from concurrent.futures import ThreadPoolExecutor

from .hbimage import HBImage


class HBAlbum:
    """ HBAlbum is used to manage a collection of HBImage objects.\n
    You can utilize this class to load, save,
    and manipulate multiple images simultaneously.
    """

    def __init__(
        self,
        source: Union[str, HBImage, Sequence[Union[str, HBImage]]] = ""
        ):

        self._album: list[HBImage] = []
        self._bookmark: int = 0
        if source:
            self.load(source)

    def __len__(self):
        return len(self._album)

    def __getitem__(self, key):
        return self._album[key]

    def __setitem__(self, key: int, value: "HBImage"):
        if not isinstance(value, HBImage):
            raise TypeError("Elements in the sequence must be HBImage type.")
        self._album[key] = value

    def __iter__(self):
        return self._album.__iter__()

    @property
    def filenames(self) -> tuple[str, ...]:
        return tuple(img.filename for img in self._album)

    @property
    def is_empty(self) -> bool:
        return len(self._album) == 0

    @property
    def bookmark_image(self) -> "HBImage":
        return self._album[self._bookmark]

    @property
    def bookmark(self) -> int:
        return self._bookmark

    @bookmark.setter
    def bookmark(self, index: int):
        """ Set the bookmark to a specified index.

        Args:
            index (int): The index position to set as the bookmark.
        Raises:
            TypeError: If the provided index is not an integer.
        """
        if not isinstance(index, int):
            raise TypeError("Bookmark index must be an integer.")
        self._bookmark = max(0, min(index, len(self) - 1))

    def append(self, hb_image: "HBImage"):
        self._album.append(hb_image)

    def extend(self, hb_album: "HBAlbum"):
        self._album.extend(hb_album)

    def delete(self, index: int):
        """ Delete an HBImage from the album by index.\n
        This method also closes the file pointer associated with the deleted HBImage.\n
        If the deleted image is bookmarked, the bookmark is set to the first image.

        Args:
            index (int): The index of the HBImage to delete.
        """
        _ = self._album[index]
        self._album[index]._image.close()
        del self._album[index]
        if index < self._bookmark:
            self._bookmark -= 1
        elif self._bookmark == index:
            self._bookmark = 0

    def insert(self, index: int, hbimage: "HBImage"):
        """ Insert an HBImage into the album at a specified index.\n

        Args:
            index (int): The index position at which to insert the HBImage.\n
            hbimage (HBImage): The HBImage object to insert.

        Raises:
            TypeError: If the provided argument is not an HBImage.
        """
        if not isinstance(hbimage, HBImage):
            raise TypeError("Arg must be HBImage type.")
        self._album.insert(index, hbimage)
        if index >= self._bookmark:
            self._bookmark += 1

    def load(self, source: Union[str, HBImage, Sequence[Union[str, HBImage]]]):
        if isinstance(source, (str, HBImage)):
            self._album = [HBImage(source)]
            return None

        if not isinstance(source, (list, tuple)):
            raise TypeError("Unsupported source type.")
        if not isinstance(source[0], (str, HBImage)):
            raise TypeError("Elements in the sequence must be str or HBImage type.")

        self._load_from_sequence(source)
            

    def save(self, folder_path: str, format: str = "", filename_prefix: str = ""):
        """ Save images in the album to a specified folder.

        Args:
            folder_path (str): The folder path where the images will be saved.\n
            format (str, optional): The image format to save as (e.g., "jpg", "png").\n
            filename_prefix (str, optional): A prefix to prepend to the saved image filenames.

        Raises:
            AttributeError: If the album is empty and there are no images to save.
        """
        if self.is_empty:
            raise AttributeError("There is no Image.")
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

        if filename_prefix:
            filename_prefix += '_'
        filename_prefix = os.path.join(folder_path, filename_prefix)
        fn_save_image = lambda hbimg: hbimg.save(f"{filename_prefix}{hbimg.filename}")

        with ThreadPoolExecutor() as executor:
            _ = tuple(executor.map(fn_save_image, self._album))

    def save_to_pdf(self, filepath: str):
        if self.is_empty:
            raise IndexError("There is no image.")

        pil_images = tuple(hbimg._image for hbimg in self._album)
        append_images = pil_images[1:] if len(self._album) > 1 else None

        pil_images[0].save(filepath, format="pdf", save_all=True, append_images=append_images)

    def _load_from_sequence(self, source: Sequence[Union[str, HBImage]]):
        with ThreadPoolExecutor() as executor:
            self._album = list(executor.map(HBImage, source))

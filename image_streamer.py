import random
import yaml
from typing import Union
from pathlib import Path
from typing import Protocol, Iterator
from PIL import Image
import io
import cv2


class StreamerProtocol(Protocol):

    def __iter__(self):
        """ returns the next image to show on the wallpaper"""

    def __len__(self):
        """ shows how many images to iterate over """


class StreamerBase(StreamerProtocol):

    def __init__(self):
        self._current = 0

    def __iter__(self) -> Iterator[Image.Image]:
        return self

    def __next__(self) -> Image.Image:
        if self._current == len(self.paths):
            raise StopIteration
        else:
            image = self.get(self._current)
            self._current += 1
            return image

    def get(self, index: int) -> Image.Image:
        raise NotImplementedError("__call__ not implemented")


class FTPStreamer(StreamerBase):

    def __init__(self, server_host: str, directory: str = "", user: str = "", passwd: str = "", randomize: bool = False):
        from ftplib import FTP
        # connect to host, default port
        ftp = FTP(server_host)
        # user anonymous, passwd anonymous@
        ftp.login(user, passwd)

        if directory != "":
            ftp.cwd(directory)

        # self.images = ftp.retrlines('LIST')
        self.paths = ftp.nlst()
        if randomize:
            random.shuffle(self.paths)

        self.ftp = ftp
        super().__init__()

    def __len__(self):
        return len(self.paths)

    def get(self, index: int):
        return self._read_image(self.paths[index])

    def _read_image(self, path: str):
        stream = io.BytesIO()
        self.ftp.retrbinary(f'RETR {path}', stream.write)
        stream.seek(0)
        return Image.open(stream)

    def _read_bytes(self, path: str):
        stream = io.BytesIO()
        self.ftp.retrbinary(f'RETR {path}', stream.write)
        stream.seek(0)
        return stream.getvalue()


def resize_with_pad(image, target_width, target_height, interpolation=None):
    image_width = image.shape[1]
    image_height = image.shape[0]
    ratio = image_width / image_height
    resized_height = round(image_height * target_width / image_width)

    if ratio > 1.0 and resized_height <= target_height:
        # pad top / bottom
        new_width = target_width
        scale = new_width / image_width
        new_height = round(scale * image_height)
        # print(
        #     f"resizing from {image_width}x{image_height} to {new_width}x{new_height}")

        if interpolation is None:
            interpolation = cv2.INTER_AREA if new_width < image_width else cv2.INTER_CUBIC

        image = cv2.resize(image, (new_width, new_height),
                           interpolation=interpolation)
        total_padding = target_height - new_height
        top = round(total_padding / 2)
        bottom = total_padding - top
        left = 0
        right = 0

    else:
        # pad left / right
        new_height = target_height
        scale = new_height / image_height

        new_width = round(scale * image_width)
        # print(
        #     f"resizing from {image_width}x{image_height} to {new_width}x{new_height}")
        image = cv2.resize(image, (new_width, new_height),
                           interpolation=cv2.INTER_AREA if new_width < image_width else cv2.INTER_CUBIC)

        total_padding = target_width - new_width
        left = round(total_padding / 2)
        right = total_padding - left
        top = 0
        bottom = 0

    assert top >= 0, f"invalid top padding {top}"
    assert bottom >= 0, f"invalid bottom padding {bottom}"
    assert left >= 0, f"invalid left padding {left}"
    assert right >= 0, f"invalid right padding {right}"

    image = cv2.copyMakeBorder(
        image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=0)

    return image, (top, bottom, left, right), 1. / scale


def image_resize(image, width=None, height=None, inter=cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation=inter)

    # return the resized image
    return resized


class DirectoryStreamer(StreamerBase):

    def __init__(self, d: Union[str, Path], extensions=["jpg", "png"], pattern="*", randomize: bool = False):
        def match(x: Path):
            lower = x.name.lower()
            return any(lower.endswith(f".{ext}") for ext in extensions)

        self.paths = sorted(list(filter(match, Path(d).rglob(pattern))))
        if randomize:
            random.shuffle(self.paths)

        print(f"=> found {len(self.paths)} paths inside of {d}")
        super().__init__()

    def __len__(self):
        return len(self.paths)

    def get(self, index: int):
        return Image.open(self.paths[index])


def load_config(config_path: str):
    with Path(config_path).open("r") as reader:
        data = yaml.load(reader, yaml.SafeLoader)
    return data


def load_streamer(config: dict) -> StreamerProtocol:
    data = config['streamer']

    if data['type'] == 'DirectoryStreamer':
        return DirectoryStreamer(
            d=data['path'],
            extensions=data.get('extensions', ['jpg', 'png']),
            pattern=data.get("pattern", "*"),
            randomize=data.get('randomize', True)
        )
    elif data['type'] == 'FTPStreamer':
        return FTPStreamer(
            server_host=data['host'],
            directory=data.get('path', ""),
            user=data.get("user", ""),
            passwd=data.get("passwd", ""),
            randomize=data.get('randomize', True)
        )
    else:
        raise Exception(
            "`type` has to be set to one of [DirectoryStreamer, FTPStreamer]")


if __name__ == "__main__":
    streamer = DirectoryStreamer("/home/baudcode/elias")
    for image in streamer:
        print(image.size)

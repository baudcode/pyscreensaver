import random
import yaml
from typing import Union
from pathlib import Path
from typing import Protocol, Iterator
from PIL import Image
import io


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
            extensions=data.get('extensions', ['jpg', 'png', 'jpeg']),
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

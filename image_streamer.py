import dataclasses
import io
import random
from pathlib import Path
from typing import Iterator, List, Optional, Protocol, Tuple, Union

import yaml
from PIL import Image


@dataclasses.dataclass
class _StreamerConfig:
    type: str
    path: str
    randomize: bool = False
    extensions: List[str] = dataclasses.field(default_factory=lambda: ['jpg', 'png', 'jpeg'])
    pattern: str = "*"

    # optional attributes for ftp streamer
    host: str = None
    passwd: str = ""
    user: str = ""


@dataclasses.dataclass
class _TextConfig:
    x: int = 10
    y: int = 10
    font_size: int = 24
    color: str = "white"
    font: str = "Arial"
    format: str = "%0"
    type: str = "bold"
    anchor: str = "nw"
    contrast_color: Optional[str] = None
    black_border_color: Optional[str] = None
    white_threshold: int = 235 # 0 to 255 (255 = white)

@dataclasses.dataclass
class Config:
    streamer: _StreamerConfig

    fullscreen: bool = True
    timeout: int = 5
    mode: str = "endless"
    text: Optional[_TextConfig] = None
    initial_sleep: int = 5
    
    @classmethod
    def from_dict(self, data: dict):
        _text = data.pop("text", None)
        text = _TextConfig(**_text) if _text is not None else None
        _streamer = data.pop("streamer")
        streamer = _StreamerConfig(**_streamer)

        return Config(
            streamer=streamer,
            text=text,
            **data,
        )


class StreamerProtocol(Protocol):

    def __iter__(self) -> Iterator[Tuple[Image.Image, Path]]:
        """ returns the next image to show on the wallpaper"""

    def __len__(self) -> int:
        """ shows how many images to iterate over """


class StreamerBase(StreamerProtocol):

    def __init__(self):
        self._current = 0

    def __iter__(self) -> Iterator[Tuple[Image.Image, Path]]:
        return self

    def __next__(self) -> Tuple[Image.Image, Path]:
        if self._current == len(self.paths):
            raise StopIteration
        else:
            image, path = self.get(self._current)
            self._current += 1
            return image, path

    def get(self, index: int) -> Tuple[Image.Image, Path]:
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
        path = self.paths[index]
        return self._read_image(path), path

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
        path = self.paths[index]
        return Image.open(path), path


def load_config(config_path: str) -> Config:
    with Path(config_path).open("r") as reader:
        data = yaml.load(reader, yaml.SafeLoader)
    return Config.from_dict(data)


def load_streamer(config: Config) -> StreamerProtocol:
    data = config.streamer

    if data.type == 'DirectoryStreamer':
        return DirectoryStreamer(
            d=data.path,
            extensions=data.extensions,
            pattern=data.pattern,
            randomize=data.randomize
        )
    elif data['type'] == 'FTPStreamer':
        assert data.host is not None, "`host` needs to be set"
        return FTPStreamer(
            server_host=data.host,
            directory=data.path,
            user=data.user,
            passwd=data.passwd,
            randomize=data.randomize
        )
    else:
        raise Exception(
            "`type` has to be set to one of [DirectoryStreamer, FTPStreamer]")


if __name__ == "__main__":
    streamer = DirectoryStreamer("/home/baudcode/elias")
    for image in streamer:
        print(image.size)

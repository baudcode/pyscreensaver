import asyncio
import copy
import sys
import time
from pathlib import Path

import numpy as np
from PIL import ExifTags, Image, ImageTk

from image_streamer import Config, load_config, load_streamer

print("Waiting for 5 seconds")  # noqa
time.sleep(5)
print("Starting App")

# the tkinter library changed it's name from Python 2 to 3.
if sys.version_info[0] == 2:
    import Tkinter
    # I decided to use a library reference to avoid potential naming conflicts with people's programs.
    tkinter = Tkinter
else:
    import tkinter


cur_dir = Path(__file__).parent

config = load_config(cur_dir / "config.yaml")
root = tkinter.Tk()

w, h = root.winfo_screenwidth(), root.winfo_screenheight()
is_fullscreen = False


def key(event):
    print(event)
    print("pressed", repr(event.char))
    if event.char == 'q':
        root.destroy()


def quit_application(event=None):
    root.destroy()
    return "break"


def toggle_fullscreen(event=None):
    global is_fullscreen
    is_fullscreen = not is_fullscreen
    root.attributes("-fullscreen", is_fullscreen)
    if is_fullscreen:
        root.config(cursor="none")
    else:
        root.config(cursor="watch")

    return "break"


def end_fullscreen(event=None):
    global is_fullscreen
    if is_fullscreen:
        toggle_fullscreen(event=event)


root.geometry("%dx%d+0+0" % (w, h))
root.focus_set()
root.bind("<Key>", key)

root.bind("<f>", toggle_fullscreen)
root.bind("<Escape>", end_fullscreen)
root.bind("<q>", quit_application)


canvas = tkinter.Canvas(root, width=w, height=h,
                        background='black', highlightthickness=0)
canvas.pack()
image = Image.fromarray(np.zeros((h, w, 3), 'uint8'))
current_path = None

if config.fullscreen:
    toggle_fullscreen()


def update_global_state(update_image: Image.Image, update_path: Path, event: asyncio.Event):
    global image, current_path
    print('update image var...')
    image = update_image
    current_path = update_path
    event.set()

    # wait until the event is deactivated
    while event.set():
        print("waiting until event is cleared")
        asyncio.sleep(.5)


async def update_image(event: asyncio.Event):
    endless = config.mode == 'endless'
    once = True

    while endless or once:

        streamer = load_streamer(config)
        for image, path in streamer:
            update_global_state(image, path, event)
            await asyncio.sleep(config.timeout)

        once = False


def resize_fit(image, target_width: int, target_height: int):
    """ resizes image with keeping aspect ratio """
    image_width, image_height = image.size[0], image.size[1]

    scale_factor = max(image_width / target_width,
                       image_height / target_height)

    new_size = int(image.size[0] /
                   scale_factor), int(image.size[1] / scale_factor)
    resized = image.resize(new_size)

    return resized

def get_orientation_exif_tag():
    for k, v in ExifTags.TAGS.items():
        if v == 'Orientation':
            return k
    raise ValueError("cannot find Orientation exif tag in global tags")

def rotate_for_orientation(image: Image.Image):

    try:
        orientation = get_orientation_exif_tag()
        exif = dict(image._getexif().items())

        if exif[orientation] == 3:
            image = image.transpose(Image.ROTATE_180)
        elif exif[orientation] == 6:
            image = image.transpose(Image.ROTATE_270)
        elif exif[orientation] == 8:
            image = image.transpose(Image.ROTATE_90)

    except (AttributeError, KeyError, IndexError):
        # cases: image don't have getexif
        pass

    return image

def text_measure(config: Config, text: str):
    # Define the font
    custom_font = tkinter.font.Font(family=config.text.font, size=config.text.font, weight=config.text.type)

    # Measure the dimensions
    text_width = custom_font.measure(text)
    text_height = custom_font.metrics("linespace")  # Total height of a line of text
    return text_width, text_height

async def main_thread(event: asyncio.Event):
    global image, current_path, config
    # run screen updates once to get the screen size
    root.update_idletasks()
    root.update()

    while 1:
        # update canvas
        w, h = root.winfo_width(), root.winfo_height()
        if w == 1 or h == 1:
            continue

        if event.is_set():
            
            print("event is set...")
            event.clear()
            print("updating image from image var...")
            canvas.delete("all")
            assert isinstance(
                image, Image.Image), f"image is {type(image)} type, instead of Image.Image"
            # TODO: check which orientation the image has.
            image = rotate_for_orientation(image)
            resized = resize_fit(image, w, h)

            tk_image = ImageTk.PhotoImage(resized)
            canvas.create_image(w // 2, h // 2, image=tk_image)
            
            if config.text:
                
                # format text by format given
                current = current_path
                text = copy.deepcopy(config.text.format)
                i = 0

                while current.parent != Path("/") and i != 50:
                    if f"%{i}" in text:
                        text = text.replace(f"%{i}", current.name)
                    i += 1
                    current = current.parent

                def draw_text():
                    return canvas.create_text(
                        config.text.x, config.text.y,
                        text=text,
                        font=(config.text.font, config.text.font_size, config.text.type),
                        fill=config.text.color,
                        anchor=config.text.anchor # ["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]
                    )

                if config.text.background:
                    # Draw text on canvas
                    text_id = draw_text()

                    # Get bounding box of the text
                    bbox = list(canvas.bbox(text_id))
                    _width, _height = bbox[2] - bbox[0], bbox[3] - bbox[1]

                    bbox[0] -= config.text.background.padding[2]
                    bbox[2] += config.text.background.padding[0]
                    bbox[1] -= config.text.background.padding[3]
                    bbox[3] += config.text.background.padding[1]

                    canvas.create_rectangle(*bbox, fill=config.text.background.color, outline=config.text.background.outline)
                
                draw_text()


        # run screen updates
        root.update_idletasks()
        root.update()
        await asyncio.sleep(.3)


async def main():
    event = asyncio.Event()
    await asyncio.gather(
        main_thread(event=event),
        update_image(event=event)
    )

if __name__ == "__main__":
    asyncio.run(main())

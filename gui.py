import sys

# the tkinter library changed it's name from Python 2 to 3.
if sys.version_info[0] == 2:
    import Tkinter
    # I decided to use a library reference to avoid potential naming conflicts with people's programs.
    tkinter = Tkinter
else:
    import tkinter
import asyncio
from contextvars import ContextVar

import numpy as np
from PIL import Image, ImageTk

from image_streamer import load_config, load_streamer

config = load_config("config.yaml")
fullscreen = config.get('fullscreen', False)
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

if config.get("fullscreen", False):
    toggle_fullscreen()


def update_global_state(update_image: Image.Image, event: asyncio.Event):
    global image
    print('update image var...')
    image = update_image
    event.set()

    # wait until the event is deactivated
    while event.set():
        print("waiting until event is cleared")
        asyncio.sleep(.5)


async def update_image(event: asyncio.Event):
    endless = config['mode'] == 'endless'
    once = True
    timeout = config.get("timeout", 10)

    while endless or once:

        streamer = load_streamer(config)
        for image in streamer:
            update_global_state(image, event)
            await asyncio.sleep(timeout)

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


async def main_thread(event: asyncio.Event):
    global image
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

            assert isinstance(
                image, Image.Image), f"image is {type(image)} type, instead of Image.Image"
            resized = resize_fit(image, w, h)

            tk_image = ImageTk.PhotoImage(resized)
            canvas.create_image(w // 2, h // 2, image=tk_image)

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

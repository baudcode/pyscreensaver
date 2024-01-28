import sys
# the tkinter library changed it's name from Python 2 to 3.
if sys.version_info[0] == 2:
    import Tkinter
    # I decided to use a library reference to avoid potential naming conflicts with people's programs.
    tkinter = Tkinter
else:
    import tkinter
from PIL import Image, ImageTk
import numpy as np
from image_streamer import load_streamer, load_config, resize_with_pad
import asyncio

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
image = np.zeros((h, w, 3), 'uint8')

if config.get("fullscreen", False):
    toggle_fullscreen()


def show_pil(update_image: Image.Image):
    global image
    image = update_image


async def update_image():
    endless = config['mode'] == 'endless'
    once = True
    timeout = config.get("timeout", 10)

    while endless or once:

        streamer = load_streamer(config)
        for image in streamer:
            try:
                show_pil(image)
            except tkinter.TclError:
                endless = False
                break

            await asyncio.sleep(timeout)

        once = False


async def main_thread():
    while 1:
        # update canvas
        w, h = root.winfo_width(), root.winfo_height()
        resized, _, _ = resize_with_pad(np.asarray(
            image), target_width=w, target_height=h)

        tk_image = ImageTk.PhotoImage(Image.fromarray(resized))
        canvas.create_image(w // 2, h // 2, image=tk_image)

        # run screen updates
        root.update_idletasks()
        root.update()

        await asyncio.sleep(.01)


async def main():
    await asyncio.gather(
        main_thread(),
        update_image()
    )

if __name__ == "__main__":
    asyncio.run(main())
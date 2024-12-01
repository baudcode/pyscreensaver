import asyncio
import copy
import sys
import time
from pathlib import Path
from timeit import default_timer

import numpy as np
from PIL import ExifTags, Image, ImageDraw, ImageFont, ImageTk

from image_streamer import Config, load_config, load_streamer

cur_dir = Path(__file__).parent
config = load_config(cur_dir / "config.yaml")

print(f"Waiting for {config.initial_sleep} seconds")  # noqa
time.sleep(config.initial_sleep)
print("Starting App")

# the tkinter library changed it's name from Python 2 to 3.
if sys.version_info[0] == 2:
    import Tkinter
    # I decided to use a library reference to avoid potential naming conflicts with people's programs.
    tkinter = Tkinter
else:
    import tkinter



root = tkinter.Tk()

w, h = root.winfo_screenwidth(), root.winfo_screenheight()
print(f"{w=} | {h=}")
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


async def update_global_state(update_image: Image.Image, update_path: Path, event: asyncio.Event):
    global image, current_path
    print('update image var...')
    image = update_image
    current_path = update_path

    # wait until image is copied
    event.set()
    await asyncio.sleep(.1)

    # wait until the event is deactivated
    while event.is_set():
        print("waiting until event is cleared")
        await asyncio.sleep(.5)

async def update_image(event: asyncio.Event):
    endless = config.mode == 'endless'
    once = True

    while endless or once:

        streamer = load_streamer(config)

        for image, path in streamer:
            await update_global_state(image, path, event)

        once = False


def resize_fit(image: Image.Image, target_width: int, target_height: int):
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

def get_avg_pixel_value(image, box):
    # Crop the image to the bounding box
    cropped_region = image.crop(box)

    # Get pixel values (as a list)
    pixel_values = list(cropped_region.getdata())
    return np.mean(pixel_values)

def get_text_box(image, x, y, text, font_size: int):
    draw = ImageDraw.Draw(image)

    # Specify the font
    font = ImageFont.truetype("arial.ttf", font_size)
    bbox = draw.textbbox((x, y), text, font=font)
    return bbox

def compute_intersection(box1, box2):
    """
    Calculate Intersection over Union (IoU) for two bounding boxes.

    Parameters:
        box1 (tuple): (x1, y1, x2, y2) format where (x1, y1) is the top-left 
                      and (x2, y2) is the bottom-right corner.
        box2 (tuple): Same format as box1.

    Returns:
        float: IoU value between 0 and 1.
    """
    # Unpack the coordinates
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2

    area1 = (x1_max - x1_min) * (y1_max - y1_min)

    # Calculate intersection coordinates
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)

    # Compute the area of intersection
    inter_width = max(0, inter_x_max - inter_x_min)
    inter_height = max(0, inter_y_max - inter_y_min)
    inter_area = inter_width * inter_height
    return inter_area / area1

def get_text_color(config: Config, resized_image: Image.Image, text: str):
    color = config.text.color
    text_box = get_text_box(resized_image, config.text.x, config.text.y, text, config.text.font_size)

    if config.text.contrast_color:
        # location of the image on the screen

        w, h = root.winfo_width(), root.winfo_height()
        image_box = [
            w // 2 - resized_image.width // 2,
            h // 2 - resized_image.height // 2,
            w // 2 + resized_image.width // 2,
            h // 2 + resized_image.height // 2,
        ]
        print(f"{text_box=} | {image_box=} | {w=} | {h=} | image={resized_image.size=}")
        inter = compute_intersection(text_box, image_box)
        print(f"text intersection with image: {inter}")

        if inter < 0.7:
            color = config.text.black_border_color or config.text.color
            print(f"switching to color {color} reason: {inter=}. Text on black.")
        else:
            image_text_box = [
                text_box[0] - image_box[0],
                text_box[1] - image_box[1],
                text_box[2] - image_box[0],
                text_box[3] - image_box[1],
            ]
            print("image text box: ", image_text_box)
            avg_pixel_value = get_avg_pixel_value(
                image, image_text_box
            )
            print("Avg Pixel value: ", avg_pixel_value)

            if avg_pixel_value > config.text.white_threshold:
                color = config.text.contrast_color or color
                print(f"switching to contrast color {color} reason: {avg_pixel_value} > {config.text.white_threshold}. Image too white")

    return color

def get_text(current_path: Path, config: Config):
    # format text by format given
    current = current_path
    text = copy.deepcopy(config.text.format)
    i = 0

    while current.parent != Path("/") and i != 50:
        if f"%{i}" in text:
            text = text.replace(f"%{i}", current.name)
        i += 1
        current = current.parent
    return text

async def main_thread(event: asyncio.Event):
    global image, current_path, config
    # run screen updates once to get the screen size
    root.update_idletasks()
    root.update()

    current_image = None
    last_update = default_timer()

    while 1:
        # update canvas
        w, h = root.winfo_width(), root.winfo_height()
        if w == 1 or h == 1:
            continue

        if event.is_set():
            # transform image
            print("processing starting image")
            start = default_timer()
            current_image = rotate_for_orientation(image)
            resized = resize_fit(current_image, w, h)
            print(f"processing image finished in {(default_timer() - start)}")

            event.clear()

            # delete the canvas
            print("updating image from image var...")
            canvas.delete("all")
            assert isinstance(
                resized, Image.Image), f"image is {type(resized)} type, instead of Image.Image"

            # write image
            tk_image = ImageTk.PhotoImage(resized)
            canvas.create_image(w // 2, h // 2, image=tk_image)
            
            if config.text:
                text = get_text(current_path, config)
                color = get_text_color(config, resized, text)
                
                canvas.create_text(
                    config.text.x, config.text.y,
                    text=text,
                    font=(config.text.font, config.text.font_size, config.text.type),
                    fill=color,
                    anchor=config.text.anchor # ["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]
                )
            
            root.update()

            # update to spend only config.timeout time
            time_for_update = default_timer() - last_update

            sleep_time = max(config.timeout - time_for_update, 0)
            print(f"sleeping for {sleep_time}")
            await asyncio.sleep(sleep_time)

            # mark the time of the last update
            last_update = default_timer()

        root.update_idletasks()

        # run screen updates
        await asyncio.sleep(.3)


async def main():
    event = asyncio.Event()
    await asyncio.gather(
        main_thread(event=event),
        update_image(event=event)
    )

if __name__ == "__main__":
    asyncio.run(main())

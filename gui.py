import dearpygui.dearpygui as dpg
import numpy as np
from image_streamer import resize_with_pad, load_streamer, load_config
from threading import Thread
import time
import sys
from screeninfo import get_monitors

# select first monitor
monitor = list(get_monitors())[0]


screen_size = (
    monitor.width,
    monitor.height
)


def save_callback():
    print("Save Clicked")


dpg.create_context()
dpg.create_viewport(decorated=False, always_on_top=True)
dpg.setup_dearpygui()


texture_tag = "testing"


def prepare_image(image: np.ndarray, force_rgb=True):
    image = np.asarray(image)
    image = (image.astype(np.float32) / 255.)

    if force_rgb:
        image = image[..., :3]

    if image.shape[-1] == 3:
        return np.concatenate([
            image,
            np.ones((image.shape[0], image.shape[1], 1), "float32")
        ], axis=-1)

    return image


def load_images():

    print("loading `config.yaml`")
    config = load_config("config.yaml")
    timeout = config.get("timeout", 10)
    print(f"using timeout of {timeout} seconds")

    mode = config.get("mode", 'once')
    assert mode in [
        'endless', 'once'], f"mode has to be 'endless' or 'once' but is '{mode}'"

    print(f"using mode {mode} [endless, once]")
    # streamer = FTPStreamer("localhost", user="baudcode", passwd="")
    endless = mode == 'endless'

    once = True  # once is always true, as it will alawys run once

    while endless or once:
        streamer = load_streamer(config)

        for image in streamer:
            rgba = prepare_image(np.asarray(image), force_rgb=True)
            rgba, _, _ = resize_with_pad(rgba, screen_size[0], screen_size[1])

            dpg.remove_alias(texture_tag)
            with dpg.texture_registry(show=False):
                dpg.add_static_texture(width=rgba.shape[1], height=rgba.shape[0], default_value=rgba,
                                       tag=texture_tag)

            dpg.configure_item('image_tag', texture_tag=texture_tag)
            time.sleep(timeout)

        once = False

    print("=> done iterating through images on cloud")
    dpg.destroy_context()
    sys.exit(0)


def quit_application_handler(sender, app_data):
    if dpg.is_key_down(dpg.mvKey_Q):
        print("Ctrl + Q")
        dpg.destroy_context()
        sys.exit(0)


with dpg.window(label="Example Window", width=screen_size[0], height=screen_size[1],
                menubar=False,
                indent=0,
                no_scrollbar=True,
                no_move=False,
                no_resize=False,
                no_collapse=True,
                no_title_bar=True):

    # register initial texture
    with dpg.texture_registry(show=False):
        empty = np.zeros((512, 512, 3), "uint8")
        rgba = prepare_image(empty)
        dpg.add_static_texture(width=rgba.shape[1], height=rgba.shape[0], default_value=rgba,
                               tag=texture_tag)

    dpg.add_image(
        texture_tag,
        indent=0,
        width=screen_size[0],
        height=screen_size[1],
        # border_color=(1.0, 0, 0),
        tag='image_tag')

    with dpg.handler_registry(tag='handler_registry') as ff:
        dpg.add_key_press_handler(
            dpg.mvKey_Control, callback=quit_application_handler)

with dpg.theme(default_theme=True) as global_theme:

    with dpg.theme_component(dpg.mvAll):
        # dpg.add_theme_color(dpg.mvThemeCol_FrameBg,
        #                     (255, 140, 23), category=dpg.mvThemeCat_Core)

        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,
                            0, 0, category=dpg.mvThemeCat_Core)

        dpg.add_theme_style(dpg.mvStyleVar_CellPadding,
                            0, 0, category=dpg.mvThemeCat_Core)

        dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize,
                            0, 0, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,
                            0, 0, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,
                            0, 0, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize,
                            0, 0, category=dpg.mvThemeCat_Core)

        dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing,
                            0, 0, category=dpg.mvThemeCat_Core)

        dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing,
                            0, 0, category=dpg.mvThemeCat_Core)

        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,
                            0, 0, category=dpg.mvThemeCat_Core)

        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding,
                            0, 0, category=dpg.mvThemeCat_Plots)


dpg.bind_theme(global_theme)


dpg.show_viewport()
dpg.toggle_viewport_fullscreen()


thread = Thread(target=load_images)
thread.start()

dpg.start_dearpygui()
dpg.destroy_context()

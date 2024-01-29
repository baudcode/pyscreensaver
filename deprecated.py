import cv2


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

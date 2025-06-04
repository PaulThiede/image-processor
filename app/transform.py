from PIL import Image
from io import BytesIO

from .schemas import TransformImageRequest

def transform_from_request(transform: TransformImageRequest, image: Image) -> Image:
    if transform.resize is not None:
        image = image.resize((transform.resize.width, transform.resize.height))

    if transform.crop is not None:
        left = transform.crop.x
        upper = transform.crop.y
        right = transform.crop.x + transform.crop.width
        lower = transform.crop.y + transform.crop.height
        image = image.crop((left, upper, right, lower))

    if transform.rotate is not None:
        image = image.rotate(transform.rotate, expand=True)  # expand sorgt dafür, dass das Bild nach der Rotation komplett bleibt

    if transform.filters is not None:
        if transform.filters.grayscale:
            image = image.convert("L")  # L = grayscale

        if transform.filters.sepia:
            image = image.convert("RGB")
            pixels = image.load()
            for y in range(image.height):
                for x in range(image.width):
                    r, g, b = pixels[x, y]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    pixels[x, y] = (min(255, tr), min(255, tg), min(255, tb))

    # format wird beim Speichern angewandt, nicht hier
    return image


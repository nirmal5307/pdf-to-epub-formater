"""E-ink oriented image optimization."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from .pdf_extract import ImageAsset


def optimize_image_for_eink(
    data: bytes,
    ext: str,
    *,
    max_edge: int = 1200,
    greyscale: bool = True,
    quality: int = 82,
) -> tuple[bytes, str, int, int]:
    """
    Downscale and optionally greyscale an image for e-ink devices.

    Returns (bytes, ext, width, height).
    """
    try:
        im = Image.open(BytesIO(data))
        im.load()
    except Exception:
        return data, ext, 0, 0

    if greyscale:
        im = im.convert("L")
    elif im.mode not in ("RGB", "L", "RGBA"):
        im = im.convert("RGB")

    w, h = im.size
    long_edge = max(w, h)
    if long_edge > max_edge and long_edge > 0:
        scale = max_edge / long_edge
        im = im.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))),
            Image.Resampling.LANCZOS,
        )

    buf = BytesIO()
    out_ext = "jpeg"
    if ext.lower() in {"png", "gif"} and not greyscale:
        out_ext = "png"
        im.save(buf, format="PNG", optimize=True)
    else:
        if im.mode == "RGBA":
            im = im.convert("RGB")
        im.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), out_ext, im.width, im.height


def optimize_book_images(
    images: dict[str, ImageAsset],
    *,
    max_edge: int = 1200,
    greyscale: bool = True,
) -> dict[str, ImageAsset]:
    """Return a new images dict with e-ink optimized payloads."""
    out: dict[str, ImageAsset] = {}
    for key, asset in images.items():
        data, ext, width, height = optimize_image_for_eink(
            asset.data,
            asset.ext,
            max_edge=max_edge,
            greyscale=greyscale,
        )
        out[key] = ImageAsset(
            id=asset.id,
            data=data,
            ext=ext,
            width=width or asset.width,
            height=height or asset.height,
            page=asset.page,
            y=asset.y,
            full_page=asset.full_page,
        )
    return out


def optimize_cover(
    cover: ImageAsset | None,
    *,
    max_edge: int = 1400,
    greyscale: bool = True,
) -> ImageAsset | None:
    if cover is None:
        return None
    data, ext, width, height = optimize_image_for_eink(
        cover.data,
        cover.ext,
        max_edge=max_edge,
        greyscale=greyscale,
    )
    return ImageAsset(
        id=cover.id,
        data=data,
        ext=ext,
        width=width or cover.width,
        height=height or cover.height,
        page=cover.page,
        y=cover.y,
        full_page=cover.full_page,
    )

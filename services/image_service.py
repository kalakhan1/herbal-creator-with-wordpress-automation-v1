"""Image service with filters, custom size, background, uniform output."""
import logging
import re
from pathlib import Path
from typing import Dict, Tuple
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from config import Config

log = logging.getLogger(__name__)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
MAX_SIZE_MB = 15

AVAILABLE_FILTERS = [
    "none", "grayscale", "sepia", "brightness",
    "contrast", "sharpen", "cool", "warm", "vintage",
]


def sanitize(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r'[^\w\s\-\.]', '', name)
    name = re.sub(r'\s+', '-', name)
    return name.lower().strip('-.')


def validate(filename: str, size: int) -> Tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return False, f"Unsupported: {ext}"
    if size > MAX_SIZE_MB * 1024 * 1024:
        return False, f"Too large (>{MAX_SIZE_MB}MB)"
    return True, ""


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = (hex_color or "#FFFFFF").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (255, 255, 255)


def apply_filter(img: Image.Image, filter_name: str) -> Image.Image:
    """Apply CSS-like filter for uniform look across all images."""
    if not filter_name or filter_name == "none":
        return img

    if filter_name == "grayscale":
        return ImageOps.grayscale(img).convert(img.mode)
    if filter_name == "sepia":
        gray = ImageOps.grayscale(img).convert("RGB")
        sepia = Image.new("RGB", gray.size, (112, 66, 20))
        return Image.blend(gray, sepia, 0.35)
    if filter_name == "brightness":
        return ImageEnhance.Brightness(img).enhance(1.12)
    if filter_name == "contrast":
        return ImageEnhance.Contrast(img).enhance(1.12)
    if filter_name == "sharpen":
        return img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    if filter_name == "cool":
        r, g, b = img.split() if img.mode == "RGB" else (None, None, None)
        if r is None:
            return img
        r = r.point(lambda x: max(0, x - 12))
        b = b.point(lambda x: min(255, x + 12))
        return Image.merge("RGB", (r, g, b))
    if filter_name == "warm":
        r, g, b = img.split() if img.mode == "RGB" else (None, None, None)
        if r is None:
            return img
        r = r.point(lambda x: min(255, x + 12))
        b = b.point(lambda x: max(0, x - 12))
        return Image.merge("RGB", (r, g, b))
    if filter_name == "vintage":
        img = ImageEnhance.Color(img).enhance(0.85)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        return img
    return img


def to_webp(src: Path, dst: Path, quality: int = 88,
            width: int = 0, height: int = 0,
            mode: str = "fit", bg_color: str = "#FFFFFF",
            filter_name: str = "none") -> bool:
    """
    Convert + resize + filter to WebP.
    mode='fit' → pad to exact size (uniform grid look) — DEFAULT
    mode='crop' → fill + crop
    mode='auto' → keep ratio
    """
    try:
        img = Image.open(src)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        # Target size
        if width and height:
            tw, th = width, height
        elif width:
            w0, h0 = img.size
            tw = width; th = int(h0 * (width / w0))
        elif height:
            w0, h0 = img.size
            th = height; tw = int(w0 * (height / h0))
        else:
            w0, h0 = img.size
            max_side = 1200
            if max(w0, h0) > max_side:
                ratio = max_side / max(w0, h0)
                tw, th = int(w0 * ratio), int(h0 * ratio)
            else:
                tw, th = w0, h0

        # Default mode is 'fit' — uniform grid look guaranteed
        if mode == "crop":
            sw, sh = img.size
            ratio = max(tw / sw, th / sh)
            img = img.resize((int(sw * ratio), int(sh * ratio)), Image.LANCZOS)
            left = (img.width - tw) // 2
            top = (img.height - th) // 2
            img = img.crop((left, top, left + tw, top + th))
        elif mode == "fit":
            img.thumbnail((tw, th), Image.LANCZOS)
            bg_rgb = _hex_to_rgb(bg_color)
            canvas = Image.new("RGB", (tw, th), bg_rgb)
            canvas.paste(img, ((tw - img.width) // 2, (th - img.height) // 2),
                         img if img.mode == "RGBA" else None)
            img = canvas
        else:
            if width or height:
                img.thumbnail((tw, th), Image.LANCZOS)

        # Apply filter
        img = apply_filter(img, filter_name)

        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst, "WEBP", quality=quality, method=6, optimize=True)
        return True
    except Exception as e:
        log.error(f"WebP failed: {e}")
        return False


def seo_meta(name: str, slug: str, kind: str = "product", index: int = 1) -> Dict:
    base = sanitize(f"{slug}-{kind}")
    if index > 1:
        base = f"{base}-{index}"
    if kind == "product":
        alt = f"{name} product image"
        title = name
        desc = f"Product image of {name}"
    else:
        alt = f"{name} featured image {index}"
        title = f"{name} - Image {index}"
        desc = f"Featured image {index} for {name}"
    return {"filename": f"{base}.webp", "alt": alt, "title": title, "description": desc}


def process_upload(data: bytes, original_name: str, name: str, slug: str,
                   kind: str, target_dir: Path,
                   width: int = 0, height: int = 0, mode: str = "fit",
                   bg_color: str = "#FFFFFF", quality: int = 88,
                   filter_name: str = "none",
                   image_index: int = 1) -> Dict:
    ok, err = validate(original_name, len(data))
    if not ok:
        return {"ok": False, "error": err}

    meta = seo_meta(name, slug, kind, image_index)
    target_dir.mkdir(parents=True, exist_ok=True)

    orig_ext = Path(original_name).suffix.lower()
    orig_path = target_dir / f"_{meta['filename'].rsplit('.', 1)[0]}{orig_ext}"
    orig_path.write_bytes(data)

    dst = target_dir / meta["filename"]
    if not to_webp(orig_path, dst, quality=quality,
                   width=width, height=height, mode=mode,
                   bg_color=bg_color, filter_name=filter_name):
        return {"ok": False, "error": "Conversion failed"}

    return {
        "ok": True,
        "filename": meta["filename"],
        "alt": meta["alt"],
        "title": meta["title"],
        "description": meta["description"],
        "size_bytes": dst.stat().st_size,
        "dimensions": f"{width or 'auto'}x{height or 'auto'}",
        "filter": filter_name,
    }


def delete(filename: str, kind: str = "product") -> bool:
    target = Config.PRODUCT_IMG_DIR if kind == "product" else Config.POST_IMG_DIR
    p = target / filename
    if p.exists():
        try:
            p.unlink()
            return True
        except Exception:
            return False
    return False
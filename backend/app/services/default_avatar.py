"""Default-Avatar Generierung — einfache Silhouette als Fallback."""

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from app.config import settings
from app.services.image import hash_email


def _generate_silhouette(size: int) -> Image.Image:
    """Generiert ein einfaches Silhouette-Bild (grauer Hintergrund, dunklerer Kopf/Schultern)."""
    img = Image.new("RGB", (size, size), color=(200, 200, 200))
    draw = ImageDraw.Draw(img)

    # Kopf (Kreis oben-mitte)
    head_r = size * 0.18
    cx, cy = size / 2, size * 0.36
    draw.ellipse(
        [cx - head_r, cy - head_r, cx + head_r, cy + head_r],
        fill=(160, 160, 160),
    )

    # Koerper (Ellipse unten)
    body_w = size * 0.36
    body_top = size * 0.58
    draw.ellipse(
        [cx - body_w, body_top, cx + body_w, size * 1.1],
        fill=(160, 160, 160),
    )

    return img


def publish_default(email: str) -> None:
    """Default-Silhouette in allen Groessen in die oeffentlichen Hash-Verzeichnisse schreiben."""
    hashes = hash_email(email)
    storage = Path(settings.avatar_storage_path)

    for hash_type, hash_value in hashes.items():
        hash_dir = storage / hash_type / hash_value
        hash_dir.mkdir(parents=True, exist_ok=True)

        for target_size in settings.avatar_sizes:
            img = _generate_silhouette(target_size)
            img.save(hash_dir / f"{target_size}.webp", "WEBP", quality=85)

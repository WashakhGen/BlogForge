import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from core.settings import settings

profile_dir = Path(settings.PROFILE_PICS_DIR)


# Pillow is CPU Bound 

def process_profile_image(content: bytes) -> str:
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)
        img = ImageOps.fit(img, (300,300), method=Image.Resampling.LANCZOS)

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = profile_dir / filename

        profile_dir.mkdir(parents=True, exist_ok=True)
        img.save(filepath, "JPEG", quality=85, optimize=True)

    return filename


def delete_profile_image(filename: str | None) -> None :
    if filename is None:
        return
    filepath = profile_dir/filename
    if filepath.exists():
        filepath.unlink()
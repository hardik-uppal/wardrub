"""Decode untrusted uploads once, before storage or model calls."""
import asyncio
from io import BytesIO
import warnings

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
FORMAT_MESSAGE = 'Use JPEG, PNG, WebP, HEIC, or HEIF photos.'


def normalize_photo(raw: bytes, *, min_edge=1, max_edge=2048, quality=95) -> bytes:
    """Return upright, metadata-free JPEG; inspect bytes, not claimed MIME/extension.

    Select the primary still image of HEIF containers. Reject animated inputs.
    Transparent pixels are composited on white rather than silently turning black.
    """
    if not raw or len(raw) > MAX_PHOTO_BYTES:
        raise ValueError('Each photo must be non-empty and no larger than 10 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP', 'HEIF'}:
                    raise ValueError(FORMAT_MESSAGE)
                if getattr(source, 'is_animated', False):
                    raise ValueError('Use a still photo, not an animation.')
                if source.width * source.height > MAX_PIXELS:
                    raise ValueError('Each photo must be no larger than 20 megapixels.')
                if min(source.size) < min_edge:
                    raise ValueError(f'Use a photo at least {min_edge} pixels wide and tall.')
                source.load()
                photo = ImageOps.exif_transpose(source)
                if source.info.get('icc_profile'):
                    try:
                        photo = ImageCms.profileToProfile(
                            photo, BytesIO(source.info['icc_profile']), ImageCms.createProfile('sRGB'),
                            outputMode='RGBA' if 'A' in photo.getbands() else 'RGB',
                        )
                    except ImageCms.PyCMSError as exc:
                        raise ValueError('This photo has an unreadable color profile. Export it as JPEG and retry.') from exc
                if 'A' in photo.getbands() or 'transparency' in photo.info:
                    rgba = photo.convert('RGBA')
                    photo = Image.new('RGB', rgba.size, 'white')
                    photo.paste(rgba, mask=rgba.getchannel('A'))
                else:
                    photo = photo.convert('RGB')
                photo.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
                output = BytesIO()
                # Do not forward EXIF/GPS or original MIME to downstream services.
                photo.save(output, format='JPEG', quality=quality)
                return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError(f'This photo could not be read. {FORMAT_MESSAGE}') from exc


async def read_photo(upload: UploadFile) -> bytes:
    raw = await upload.read(MAX_PHOTO_BYTES + 1)
    try:
        return await asyncio.to_thread(normalize_photo, raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

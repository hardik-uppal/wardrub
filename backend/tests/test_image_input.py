from io import BytesIO
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageCms
from pillow_heif import from_pillow
from starlette.datastructures import Headers
from app.services.image_input import normalize_photo, read_photo, MAX_PHOTO_BYTES
from app.services.style_analysis import prepare_photo


def photo(format='PNG', size=(320, 480), **kwargs):
    out = BytesIO()
    image = Image.new('RGB', size, (100, 150, 200))
    if format == 'HEIF':
        from_pillow(image).save(out)
    else:
        image.save(out, format=format, **kwargs)
    return out.getvalue()


class ImageInputTests(unittest.TestCase):
    def test_real_heif_and_existing_formats_normalize_to_jpeg(self):
        for format in ['HEIF', 'JPEG', 'PNG', 'WEBP']:
            with self.subTest(format=format):
                raw = photo(format)
                for normalize in [normalize_photo, prepare_photo]:
                    with Image.open(BytesIO(normalize(raw))) as result:
                        self.assertEqual(result.format, 'JPEG')
                        self.assertEqual(result.size, (320, 480))
                        self.assertEqual(result.mode, 'RGB')
                        self.assertFalse(result.getexif())

    def test_exif_orientation_is_applied_and_metadata_removed(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = 'Private identity'
        raw = photo('JPEG', exif=exif)
        with Image.open(BytesIO(normalize_photo(raw))) as result:
            self.assertEqual(result.size, (480, 320))
            self.assertFalse(result.getexif())

    def test_transparency_is_white_and_output_is_bounded(self):
        out = BytesIO()
        Image.new('RGBA', (2500, 300), (0, 0, 0, 0)).save(out, format='PNG')
        with Image.open(BytesIO(normalize_photo(out.getvalue()))) as result:
            self.assertEqual(max(result.size), 2048)
            self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))

    def test_color_profile_is_converted_then_removed(self):
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        with Image.open(BytesIO(normalize_photo(photo(icc_profile=profile)))) as result:
            self.assertNotIn('icc_profile', result.info)
            self.assertLess(abs(result.getpixel((0, 0))[0] - 100), 3)

    def test_invalid_oversized_and_unsupported_content_is_rejected(self):
        for raw in [b'', b'fake HEIC', b'x' * (MAX_PHOTO_BYTES + 1), photo('GIF'), photo(size=(5000, 4100))]:
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                normalize_photo(raw)
        with self.assertRaisesRegex(ValueError, '256 pixels'):
            prepare_photo(photo(size=(100, 100)))


class UploadBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_heic_with_missing_or_spoofed_mime_is_decoded_from_content(self):
        raw = photo('HEIF')
        for mime in ['', 'application/octet-stream', 'image/png']:
            upload = UploadFile(BytesIO(raw), filename='photo.heic', headers=Headers({'content-type': mime}))
            with Image.open(BytesIO(await read_photo(upload))) as result:
                self.assertEqual(result.format, 'JPEG')

    async def test_invalid_content_returns_actionable_400(self):
        upload = UploadFile(BytesIO(b'not a photo'), filename='fake.heic')
        with self.assertRaises(HTTPException) as caught:
            await read_photo(upload)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertIn('could not be read', caught.exception.detail)

    async def test_reads_are_bounded_before_decoding(self):
        upload = AsyncMock()
        upload.read.return_value = b'x' * (MAX_PHOTO_BYTES + 1)
        with self.assertRaises(HTTPException):
            await read_photo(upload)
        upload.read.assert_awaited_once_with(MAX_PHOTO_BYTES + 1)

    async def test_gallery_sends_decoded_heic_as_jpeg_to_model(self):
        from app.routers import garment
        with patch.object(garment.vertex_ai, 'detect_clothes_in_image', new=AsyncMock(return_value=[])) as detect:
            with self.assertRaises(HTTPException) as caught:
                await garment.process_uploaded_clothes(
                    file=UploadFile(BytesIO(photo('HEIF')), filename='photo.heic'), user={'uid': 'private-test'},
                )
            self.assertIn('No clothing items', caught.exception.detail)
            detect.assert_awaited_once()
            with Image.open(BytesIO(detect.call_args.args[0])) as result:
                self.assertEqual(result.format, 'JPEG')

    async def test_avatar_and_gallery_reject_bad_content_before_model_calls(self):
        from app.routers import avatar, garment
        for router, name, kwargs in [
            (avatar, 'create_avatar', {'files': [UploadFile(BytesIO(b'bad'), filename='bad.heic')], 'mode': 'selfie'}),
            (garment, 'process_uploaded_clothes', {'file': UploadFile(BytesIO(b'bad'), filename='bad.heic')}),
        ]:
            with self.subTest(route=name), patch.object(router, 'vertex_ai') as model:
                with self.assertRaises(HTTPException) as caught:
                    await getattr(router, name)(user={'uid': 'private-test'}, **kwargs)
                self.assertEqual(caught.exception.status_code, 400)
                self.assertEqual(model.mock_calls, [])

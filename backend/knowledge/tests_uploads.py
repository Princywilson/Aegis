import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from .file_uploads import MIB, validate_uploaded_file


class ContentUploadPolicyTests(SimpleTestCase):
    @staticmethod
    def presentation_package():
        package = io.BytesIO()
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("ppt/presentation.xml", "<presentation/>")
        return package.getvalue()

    def test_approved_formats_have_expected_mime_types_and_per_file_limits(self):
        uploads = (
            (
                "guide.pdf",
                b"%PDF-1.7\n",
                "application/pdf",
                "application/pdf",
                50 * MIB,
            ),
            (
                "slides.pptx",
                self.presentation_package(),
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                50 * MIB,
            ),
            ("photo.jpg", b"\xff\xd8\xff\xe0", "image/jpeg", "image/jpeg", 10 * MIB),
            ("photo.jpeg", b"\xff\xd8\xff\xe0", "image/jpeg", "image/jpeg", 10 * MIB),
            (
                "photo.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR",
                "image/png",
                "image/png",
                10 * MIB,
            ),
            (
                "photo.webp",
                b"RIFF\x00\x00\x00\x00WEBP",
                "image/webp",
                "image/webp",
                10 * MIB,
            ),
            (
                "video.mp4",
                b"\x00\x00\x00\x18ftypisom",
                "video/mp4",
                "video/mp4",
                250 * MIB,
            ),
        )

        for filename, payload, declared_mime, expected_mime, expected_limit in uploads:
            with self.subTest(filename=filename):
                upload = SimpleUploadedFile(
                    filename,
                    payload,
                    content_type=declared_mime,
                )
                validated = validate_uploaded_file(upload)

                self.assertEqual(validated.mime_type, expected_mime)
                self.assertEqual(validated.max_file_size, expected_limit)

    def test_windows_client_path_is_reduced_to_a_safe_filename(self):
        upload = SimpleUploadedFile(
            r"C:\client\folder\guide.pdf",
            b"%PDF-1.7\n",
            content_type="application/pdf",
        )

        validated = validate_uploaded_file(upload)

        self.assertEqual(validated.filename, "guide.pdf")

    def test_size_over_limit_is_rejected_before_storage(self):
        upload = SimpleUploadedFile(
            "guide.pdf",
            b"%PDF-1.7\n",
            content_type="application/pdf",
        )
        upload.size = 50 * MIB + 1

        with self.assertRaises(ValidationError):
            validate_uploaded_file(upload)

    def test_invalid_presentation_package_is_rejected(self):
        upload = SimpleUploadedFile(
            "slides.pptx",
            b"not a presentation package",
            content_type=(
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
        )

        with self.assertRaises(ValidationError):
            validate_uploaded_file(upload)

import os
import zipfile
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError


MIB = 1024 * 1024

_UPLOAD_POLICIES = {
    ".pdf": ("application/pdf", 50 * MIB),
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        50 * MIB,
    ),
    ".jpg": ("image/jpeg", 10 * MIB),
    ".jpeg": ("image/jpeg", 10 * MIB),
    ".png": ("image/png", 10 * MIB),
    ".webp": ("image/webp", 10 * MIB),
    ".mp4": ("video/mp4", 250 * MIB),
}


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    mime_type: str
    max_file_size: int


def validate_uploaded_file(uploaded_file):
    filename = _safe_filename(getattr(uploaded_file, "name", ""))
    extension = os.path.splitext(filename)[1].lower()
    policy = _UPLOAD_POLICIES.get(extension)
    if policy is None:
        raise ValidationError(
            {"file": ["This file extension is not supported."]}
        )

    expected_mime_type, max_file_size = policy
    declared_mime_type = (
        getattr(uploaded_file, "content_type", "") or ""
    ).split(";", 1)[0].strip().lower()
    if declared_mime_type != expected_mime_type:
        raise ValidationError(
            {"file": ["The declared MIME type does not match the file extension."]}
        )

    file_size = getattr(uploaded_file, "size", None)
    if file_size is None or file_size == 0:
        raise ValidationError({"file": ["Uploaded files cannot be empty."]})
    if file_size > max_file_size:
        raise ValidationError(
            {"file": ["The file exceeds the maximum size for this format."]}
        )

    actual_mime_type = _detect_mime_type(uploaded_file, extension)
    if actual_mime_type != expected_mime_type:
        raise ValidationError(
            {"file": ["The uploaded file content does not match its format."]}
        )
    return ValidatedUpload(filename, expected_mime_type, max_file_size)


def _safe_filename(filename):
    if not isinstance(filename, str):
        raise ValidationError({"file": ["A valid filename is required."]})
    filename = os.path.basename(filename.replace("\\", "/"))
    if not filename or filename in {".", ".."} or len(filename) > 255:
        raise ValidationError(
            {"file": ["The filename must be between 1 and 255 characters."]}
        )
    return filename


def _detect_mime_type(uploaded_file, extension):
    position = None
    try:
        position = uploaded_file.tell()
        uploaded_file.seek(0)
        header = uploaded_file.read(16)
        uploaded_file.seek(0)
        if extension == ".pdf" and header.startswith(b"%PDF-"):
            return "application/pdf"
        if extension == ".pptx" and _is_presentation_package(uploaded_file):
            return (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
        if extension in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if (
            extension == ".png"
            and header.startswith(b"\x89PNG\r\n\x1a\n")
            and header[12:16] == b"IHDR"
        ):
            return "image/png"
        if (
            extension == ".webp"
            and header[:4] == b"RIFF"
            and header[8:12] == b"WEBP"
        ):
            return "image/webp"
        if extension == ".mp4" and header[4:8] == b"ftyp":
            return "video/mp4"
        return ""
    except (OSError, ValueError, zipfile.BadZipFile):
        return ""
    finally:
        if position is not None:
            uploaded_file.seek(position)


def _is_presentation_package(uploaded_file):
    with zipfile.ZipFile(uploaded_file) as package:
        names = set(package.namelist())
    return {
        "[Content_Types].xml",
        "ppt/presentation.xml",
    }.issubset(names)

import io
import textwrap
import warnings
from dataclasses import dataclass
from datetime import timezone as datetime_timezone

import pypdfium2 as pdfium
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import APIException

from accountability.models import ActivityEvent
from identity.models import User

from .models import (
    Content,
    ContentAccess,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)
from .storage import StorageService


MAX_RENDER_EDGE = 2400
MAX_SOURCE_FILE_BYTES = 50 * 1024 * 1024
MAX_SOURCE_PIXELS = 20_000_000


class UnsupportedDeliveryFormat(APIException):
    status_code = 415
    default_detail = "This content format is not available in the protected viewer."
    default_code = "UNSUPPORTED_DELIVERY_FORMAT"


class InvalidContentRepresentation(APIException):
    status_code = 422
    default_detail = "The stored content could not be rendered."
    default_code = "INVALID_CONTENT_REPRESENTATION"


@dataclass(frozen=True)
class RenderedPage:
    content: bytes
    page_count: int


@transaction.atomic
def start_content_access(*, content_id, program_id, organization_id, user):
    now = timezone.now()
    try:
        content = Content.objects.select_for_update().get(
            pk=content_id,
            organization_id=organization_id,
            status=Content.Status.PUBLISHED,
            current_version__status=ContentVersion.Status.PUBLISHED,
        )
        program = Program.objects.select_for_update().get(
            pk=program_id,
            organization_id=organization_id,
            status=Program.Status.ACTIVE,
        )
    except (Content.DoesNotExist, Program.DoesNotExist) as exc:
        raise ContentAccess.DoesNotExist from exc

    if user.status != User.Status.ACTIVE:
        raise ContentAccess.DoesNotExist
    if not ProgramAccessGrant.objects.select_for_update().filter(
        organization_id=organization_id,
        user=user,
        program=program,
        status=ProgramAccessGrant.Status.ACTIVE,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).exists():
        raise ContentAccess.DoesNotExist

    if not ContentAssignment.objects.filter(
        organization_id=organization_id,
        program=program,
        content=content,
    ).exists():
        raise ContentAccess.DoesNotExist

    access = ContentAccess.objects.create(
        organization_id=organization_id,
        user=user,
        program=program,
        content=content,
        content_version=content.current_version,
        access_result=ContentAccess.Result.GRANTED,
    )
    ActivityEvent.objects.create(
        organization_id=organization_id,
        user=user,
        event_type=ActivityEvent.EventType.VIEWER_OPENED,
        content=content,
        content_version=content.current_version,
        program=program,
        content_access=access,
    )
    return access


def get_content_access_for_delivery(
    *,
    access_id,
    content_id,
    organization_id,
    user,
):
    now = timezone.now()
    try:
        access = ContentAccess.objects.select_related(
            "organization",
            "user",
            "content",
            "content_version",
            "program",
        ).get(
            pk=access_id,
            organization_id=organization_id,
            user=user,
            content_id=content_id,
            access_result=ContentAccess.Result.GRANTED,
            content__organization_id=organization_id,
            content__status=Content.Status.PUBLISHED,
            content__current_version_id=F("content_version_id"),
            content_version__organization_id=organization_id,
            content_version__content_id=content_id,
            content_version__status=ContentVersion.Status.PUBLISHED,
            program__organization_id=organization_id,
            program__status=Program.Status.ACTIVE,
        )
    except ContentAccess.DoesNotExist as exc:
        raise ContentAccess.DoesNotExist from exc

    if user.status != User.Status.ACTIVE:
        raise ContentAccess.DoesNotExist
    if not ProgramAccessGrant.objects.filter(
        organization_id=organization_id,
        user=user,
        program_id=access.program_id,
        status=ProgramAccessGrant.Status.ACTIVE,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).exists():
        raise ContentAccess.DoesNotExist
    if not ContentAssignment.objects.filter(
        organization_id=organization_id,
        program_id=access.program_id,
        content_id=content_id,
    ).exists():
        raise ContentAccess.DoesNotExist
    return access


def render_content_version(version, *, page_number):
    if version.mime_type == "application/pdf":
        source = _read_source(version)
        return _render_pdf_page(source, page_number=page_number)

    if version.mime_type in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        if page_number != 1:
            raise ValueError("Image content has only one viewer page.")
        source = _read_source(version)
        return _render_image(source)

    raise UnsupportedDeliveryFormat()


def apply_dynamic_watermark(rendered_page, access):
    with Image.open(io.BytesIO(rendered_page.content)) as source:
        image = source.convert("RGBA")

    font_size = max(12, min(24, image.width // 70))
    font = ImageFont.load_default(size=font_size)
    wrap_width = max(18, image.width // max(font_size, 1))
    lines = textwrap.wrap(
        build_watermark_text(access),
        width=wrap_width,
        break_long_words=True,
    )
    line_height = font_size + max(3, font_size // 3)
    padding = max(8, font_size)
    stamp_width = max(int(font.getlength(line)) for line in lines) + padding * 2
    stamp_height = len(lines) * line_height + padding * 2
    stamp = Image.new("RGBA", (stamp_width, stamp_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)
    for line_number, line in enumerate(lines):
        draw.text(
            (padding, padding + line_number * line_height),
            line,
            font=font,
            fill=(20, 20, 20, 76),
        )

    rotated = stamp.rotate(
        25,
        resample=Image.Resampling.BICUBIC,
        expand=True,
    )
    step_x = max(int(rotated.width * 1.5), image.width // 2)
    step_y = max(rotated.height * 2, image.height // 3)
    for y in range(-(rotated.height // 2), image.height, step_y):
        offset = step_x // 2 if (y // step_y) % 2 else 0
        for x in range(-(rotated.width // 2), image.width, step_x):
            _composite_clipped(image, rotated, x + offset, y)

    return RenderedPage(_encode_png(image), rendered_page.page_count)


def _composite_clipped(image, overlay, x, y):
    left = max(x, 0)
    top = max(y, 0)
    right = min(x + overlay.width, image.width)
    bottom = min(y + overlay.height, image.height)
    if left >= right or top >= bottom:
        return
    overlay_crop = overlay.crop(
        (left - x, top - y, right - x, bottom - y)
    )
    image.alpha_composite(overlay_crop, (left, top))


def build_watermark_text(access):
    local_part, separator, domain = access.user.email.partition("@")
    masked_email = (
        f"{local_part[:1]}***@{domain}"
        if separator
        else "***"
    )
    accessed_at = access.accessed_at.astimezone(datetime_timezone.utc)
    timestamp = accessed_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    content_reference = str(access.content_id).split("-")[0]
    return (
        f"{masked_email} | {access.organization.name} | {timestamp} | "
        f"Content {content_reference} v{access.content_version.version_number}"
    )


def _read_source(version):
    if version.file_size > MAX_SOURCE_FILE_BYTES:
        raise InvalidContentRepresentation(
            "The stored file exceeds the viewer input limit."
        )
    with StorageService().open_protected_file(version.storage_key) as stored_file:
        source = stored_file.read(MAX_SOURCE_FILE_BYTES + 1)
    if len(source) != version.file_size:
        raise InvalidContentRepresentation(
            "The stored file size does not match its recorded metadata."
        )
    return source


def _render_pdf_page(source, *, page_number):
    try:
        document = pdfium.PdfDocument(source)
    except pdfium.PdfiumError as exc:
        raise InvalidContentRepresentation() from exc

    with document:
        page_count = len(document)
        if page_number < 1 or page_number > page_count:
            raise ValueError("The requested page is outside this document.")
        page = document[page_number - 1]
        try:
            width, height = page.get_size()
            if width <= 0 or height <= 0:
                raise InvalidContentRepresentation()
            scale = min(2.0, MAX_RENDER_EDGE / max(width, height))
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil()
                return RenderedPage(_encode_png(image), page_count)
            finally:
                bitmap.close()
        except pdfium.PdfiumError as exc:
            raise InvalidContentRepresentation() from exc
        finally:
            page.close()


def _render_image(source):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(source))
            if image.width * image.height > MAX_SOURCE_PIXELS:
                raise InvalidContentRepresentation(
                    "The image dimensions exceed the viewer limit."
                )
            image = ImageOps.exif_transpose(image)
            image.load()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
    ) as exc:
        raise InvalidContentRepresentation() from exc

    image.thumbnail(
        (MAX_RENDER_EDGE, MAX_RENDER_EDGE),
        Image.Resampling.LANCZOS,
    )
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")
    return RenderedPage(_encode_png(image), 1)


def _encode_png(image):
    rendered = io.BytesIO()
    image.save(rendered, format="PNG", optimize=True)
    return rendered.getvalue()

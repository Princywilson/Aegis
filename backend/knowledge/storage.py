import hashlib
import re
import tempfile
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.core.files.storage import FileSystemStorage


_STORAGE_KEY_PATTERN = re.compile(
    r"organizations/[0-9a-f-]{36}/contents/[0-9a-f-]{36}/"
    r"versions/[0-9a-f-]{36}/file"
)
_CHUNK_SIZE = 1024 * 1024
_SPOOL_MAX_SIZE = 8 * 1024 * 1024


class PrivateFileSystemStorage(FileSystemStorage):
    def url(self, name):
        raise ValueError("Private content storage does not expose public URLs.")


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    file_size: int
    checksum: str


class UploadTooLarge(Exception):
    pass


class StorageService:
    def __init__(self, storage=None):
        self.storage = storage or PrivateFileSystemStorage(
            location=settings.AEGIS_PRIVATE_STORAGE_ROOT,
            base_url=None,
        )

    @staticmethod
    def build_storage_key(*, organization_id, content_id, version_id):
        identifiers = []
        for value in (organization_id, content_id, version_id):
            identifier = uuid.UUID(str(value))
            identifiers.append(str(identifier))
        organization_key, content_key, version_key = identifiers
        return (
            f"organizations/{organization_key}/contents/{content_key}/"
            f"versions/{version_key}/file"
        )

    def store(
        self,
        *,
        organization_id,
        content_id,
        version_id,
        uploaded_file,
        max_file_size=None,
    ):
        storage_key = self.build_storage_key(
            organization_id=organization_id,
            content_id=content_id,
            version_id=version_id,
        )
        digest = hashlib.sha256()
        file_size = 0

        with tempfile.SpooledTemporaryFile(
            max_size=_SPOOL_MAX_SIZE,
            mode="w+b",
        ) as staged_file:
            seek = getattr(uploaded_file, "seek", None)
            if not callable(seek):
                raise TypeError("Uploaded content must be a seekable binary file.")
            seek(0)
            for chunk in self._iter_chunks(uploaded_file):
                if not isinstance(chunk, bytes):
                    raise TypeError("Uploaded content must be provided as bytes.")
                digest.update(chunk)
                file_size += len(chunk)
                if max_file_size is not None and file_size > max_file_size:
                    raise UploadTooLarge()
                staged_file.write(chunk)

            staged_file.seek(0)
            saved_key = self.storage.save(storage_key, staged_file)
            if saved_key != storage_key:
                self.storage.delete(saved_key)
                raise FileExistsError(
                    "A file already exists for this content version."
                )

        return StoredFile(
            storage_key=storage_key,
            file_size=file_size,
            checksum=digest.hexdigest(),
        )

    def open_protected_file(self, storage_key):
        return self.storage.open(self._validate_storage_key(storage_key), "rb")

    def delete_file(self, storage_key):
        self.storage.delete(self._validate_storage_key(storage_key))

    @staticmethod
    def _iter_chunks(uploaded_file):
        chunks = getattr(uploaded_file, "chunks", None)
        if callable(chunks):
            yield from chunks(chunk_size=_CHUNK_SIZE)
            return

        read = getattr(uploaded_file, "read", None)
        if not callable(read):
            raise TypeError("Uploaded content must be a binary file.")
        while True:
            chunk = read(_CHUNK_SIZE)
            if not chunk:
                return
            yield chunk

    @staticmethod
    def _validate_storage_key(storage_key):
        if not isinstance(storage_key, str) or not _STORAGE_KEY_PATTERN.fullmatch(
            storage_key
        ):
            raise ValueError("Invalid AEGIS storage key.")
        segments = storage_key.split("/")
        for segment in (segments[1], segments[3], segments[5]):
            if str(uuid.UUID(segment)) != segment:
                raise ValueError("Invalid AEGIS storage key.")
        return storage_key

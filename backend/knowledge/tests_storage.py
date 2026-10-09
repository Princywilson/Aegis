import hashlib
import io
import tempfile
import uuid

from django.test import SimpleTestCase, override_settings

from .storage import (
    PrivateFileSystemStorage,
    StorageService,
    UploadTooLarge,
)


class StorageServiceTests(SimpleTestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.storage = PrivateFileSystemStorage(
            location=self.temp_directory.name,
            base_url=None,
        )
        self.service = StorageService(storage=self.storage)
        self.organization_id = uuid.uuid4()
        self.content_id = uuid.uuid4()
        self.version_id = uuid.uuid4()

    def test_storage_key_is_tenant_and_version_scoped(self):
        key = self.service.build_storage_key(
            organization_id=self.organization_id,
            content_id=self.content_id,
            version_id=self.version_id,
        )

        self.assertEqual(
            key,
            "organizations/"
            f"{self.organization_id}/contents/{self.content_id}/"
            f"versions/{self.version_id}/file",
        )

    def test_store_returns_size_and_sha256_and_file_is_private(self):
        payload = b"protected content bytes"

        metadata = self.service.store(
            organization_id=self.organization_id,
            content_id=self.content_id,
            version_id=self.version_id,
            uploaded_file=io.BytesIO(payload),
        )

        self.assertEqual(metadata.file_size, len(payload))
        self.assertEqual(metadata.checksum, hashlib.sha256(payload).hexdigest())
        self.assertTrue(self.storage.exists(metadata.storage_key))
        with self.service.open_protected_file(metadata.storage_key) as stored_file:
            self.assertEqual(stored_file.read(), payload)
        with self.assertRaises(ValueError):
            self.storage.url(metadata.storage_key)

    def test_duplicate_version_storage_does_not_overwrite_existing_file(self):
        original_payload = b"first payload"
        self.service.store(
            organization_id=self.organization_id,
            content_id=self.content_id,
            version_id=self.version_id,
            uploaded_file=io.BytesIO(original_payload),
        )

        with self.assertRaises(FileExistsError):
            self.service.store(
                organization_id=self.organization_id,
                content_id=self.content_id,
                version_id=self.version_id,
                uploaded_file=io.BytesIO(b"replacement payload"),
            )

        key = self.service.build_storage_key(
            organization_id=self.organization_id,
            content_id=self.content_id,
            version_id=self.version_id,
        )
        with self.service.open_protected_file(key) as stored_file:
            self.assertEqual(stored_file.read(), original_payload)

    def test_read_and_delete_reject_traversal_or_arbitrary_paths(self):
        invalid_keys = (
            "../../outside",
            "organizations/../../contents/x/versions/y/file",
        )
        for invalid_key in invalid_keys:
            with self.subTest(storage_key=invalid_key):
                with self.assertRaises(ValueError):
                    self.service.open_protected_file(invalid_key)
                with self.assertRaises(ValueError):
                    self.service.delete_file(invalid_key)

    def test_configured_private_storage_root_is_not_exposed_by_url(self):
        with tempfile.TemporaryDirectory() as private_root:
            with override_settings(AEGIS_PRIVATE_STORAGE_ROOT=private_root):
                service = StorageService()
                metadata = service.store(
                    organization_id=self.organization_id,
                    content_id=self.content_id,
                    version_id=self.version_id,
                    uploaded_file=io.BytesIO(b"private"),
                )
                with self.assertRaises(ValueError):
                    service.storage.url(metadata.storage_key)

    def test_text_streams_are_rejected(self):
        with self.assertRaises(TypeError):
            self.service.store(
                organization_id=self.organization_id,
                content_id=self.content_id,
                version_id=self.version_id,
                uploaded_file=io.StringIO("not bytes"),
            )

    def test_store_enforces_streamed_size_limit(self):
        with self.assertRaises(UploadTooLarge):
            self.service.store(
                organization_id=self.organization_id,
                content_id=self.content_id,
                version_id=self.version_id,
                uploaded_file=io.BytesIO(b"larger than the limit"),
                max_file_size=4,
            )
        self.assertFalse(
            self.storage.exists(
                self.service.build_storage_key(
                    organization_id=self.organization_id,
                    content_id=self.content_id,
                    version_id=self.version_id,
                )
            )
        )

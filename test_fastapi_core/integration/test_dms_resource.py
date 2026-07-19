from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import UploadFile
from fastapi.testclient import TestClient

from examples.dms_service.app import (
    DmsDocumentDeleted,
    DmsDocumentNotFound,
    InternalDocumentMetadata,
    build_dms_app,
)


class FakeDownload:
    def __init__(self, content: bytes):
        self.content = content
        self.closed = False

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._chunks()

    async def _chunks(self) -> AsyncIterator[bytes]:
        yield self.content

    async def aclose(self) -> None:
        self.closed = True


class FakeDmsSdk:
    def __init__(self):
        self.closed = False
        self.upload_file: UploadFile | None = None
        self.downloads: list[FakeDownload] = []
        self.deleted_ids = {"deleted"}

    async def healthcheck(self) -> bool:
        return True

    async def upload(self, upload: UploadFile) -> InternalDocumentMetadata:
        self.upload_file = upload
        content = await upload.read()
        assert content == b"document-body"
        return InternalDocumentMetadata(
            document_id="doc-1",
            filename=upload.filename or "unnamed",
            content_type=upload.content_type or "application/octet-stream",
            storage_key="private/bucket/doc-1",
        )

    async def metadata(self, document_id: str) -> InternalDocumentMetadata:
        if document_id == "missing":
            raise DmsDocumentNotFound(document_id)
        if document_id in self.deleted_ids:
            raise DmsDocumentDeleted(document_id)
        return InternalDocumentMetadata(
            document_id=document_id,
            filename="example.txt",
            content_type="text/plain",
            storage_key=f"private/bucket/{document_id}",
        )

    async def download(self, document_id: str) -> FakeDownload:
        await self.metadata(document_id)
        stream = FakeDownload(b"download-body")
        self.downloads.append(stream)
        return stream

    async def aclose(self) -> None:
        self.closed = True


def test_dms_reference_app_manages_sdk_readiness_upload_download_and_close():
    sdk = FakeDmsSdk()
    app = build_dms_app(lambda _app: sdk)

    with TestClient(app) as client:
        readiness = client.get("/health/readiness")
        upload = client.post(
            "/documents",
            files={"upload": ("example.txt", b"document-body", "text/plain")},
        )
        metadata = client.get("/documents/doc-1")
        download = client.get("/documents/doc-1/content")

        assert readiness.status_code == 200
        assert readiness.json()["details"]["dms"]["ok"] is True
        assert upload.status_code == 201
        assert upload.json() == {
            "document_id": "doc-1",
            "filename": "example.txt",
            "content_type": "text/plain",
        }
        assert "storage_key" not in metadata.json()
        assert download.content == b"download-body"
        assert sdk.upload_file is not None
        assert sdk.upload_file.file.closed is True
        assert sdk.downloads[-1].closed is True

    assert sdk.closed is True


def test_dms_reference_app_maps_missing_and_deleted_documents_to_problem_details():
    sdk = FakeDmsSdk()
    app = build_dms_app(lambda _app: sdk)

    with TestClient(app, raise_server_exceptions=False) as client:
        missing = client.get("/documents/missing")
        deleted = client.get("/documents/deleted/content")

    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/problem+json")
    assert missing.json()["detail"] == "Document 'missing' was not found"
    assert deleted.status_code == 410
    assert deleted.json()["detail"] == "Document 'deleted' was deleted"

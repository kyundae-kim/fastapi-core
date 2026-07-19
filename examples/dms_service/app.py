from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from fastapi import Depends, FastAPI, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from fastapi_core import (
    ErrorMapping,
    ManagedResource,
    ResourceKey,
    create_app,
    register_error_mapper,
)
from fastapi_core.config import AppConfig


@dataclass(frozen=True, slots=True)
class InternalDocumentMetadata:
    document_id: str
    filename: str
    content_type: str
    storage_key: str


class PublicDocumentMetadata(BaseModel):
    document_id: str
    filename: str
    content_type: str


class DmsDocumentError(Exception):
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(document_id)


class DmsDocumentNotFound(DmsDocumentError):
    pass


class DmsDocumentDeleted(DmsDocumentError):
    pass


class DmsDownload(Protocol):
    def __aiter__(self) -> AsyncIterator[bytes]: ...

    async def aclose(self) -> None: ...


class DmsSdk(Protocol):
    async def healthcheck(self) -> object: ...

    async def upload(self, upload: UploadFile) -> InternalDocumentMetadata: ...

    async def metadata(self, document_id: str) -> InternalDocumentMetadata: ...

    async def download(self, document_id: str) -> DmsDownload: ...

    async def aclose(self) -> None: ...


DMS_RESOURCE = ResourceKey[DmsSdk]("dms")
DmsFactory = Callable[[FastAPI], DmsSdk | Awaitable[DmsSdk]]


def _public_metadata(metadata: InternalDocumentMetadata) -> PublicDocumentMetadata:
    return PublicDocumentMetadata(
        document_id=metadata.document_id,
        filename=metadata.filename,
        content_type=metadata.content_type,
    )


def build_dms_app(factory: DmsFactory) -> FastAPI:
    async def healthcheck(sdk: DmsSdk) -> object:
        return await sdk.healthcheck()

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        resources=[
            ManagedResource(
                DMS_RESOURCE,
                factory=factory,
                healthcheck=healthcheck,
                required=True,
            )
        ]
    )

    register_error_mapper(
        app,
        DmsDocumentNotFound,
        lambda _request, exc: ErrorMapping(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Document not found",
            detail=f"Document '{exc.document_id}' was not found",
            code="DOCUMENT_NOT_FOUND",
        ),
    )
    register_error_mapper(
        app,
        DmsDocumentDeleted,
        lambda _request, exc: ErrorMapping(
            status_code=status.HTTP_410_GONE,
            title="Document deleted",
            detail=f"Document '{exc.document_id}' was deleted",
            code="DOCUMENT_DELETED",
        ),
    )

    @app.post(
        "/documents",
        response_model=PublicDocumentMetadata,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_document(
        upload: UploadFile,
        sdk: DmsSdk = Depends(DMS_RESOURCE.dependency),
    ) -> PublicDocumentMetadata:
        try:
            metadata = await sdk.upload(upload)
            return _public_metadata(metadata)
        finally:
            await upload.close()

    @app.get("/documents/{document_id}", response_model=PublicDocumentMetadata)
    async def document_metadata(
        document_id: str,
        sdk: DmsSdk = Depends(DMS_RESOURCE.dependency),
    ) -> PublicDocumentMetadata:
        return _public_metadata(await sdk.metadata(document_id))

    @app.get("/documents/{document_id}/content")
    async def download_document(
        document_id: str,
        sdk: DmsSdk = Depends(DMS_RESOURCE.dependency),
    ) -> StreamingResponse:
        metadata = await sdk.metadata(document_id)
        stream = await sdk.download(document_id)

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in stream:
                    yield chunk
            finally:
                await stream.aclose()

        return StreamingResponse(body(), media_type=metadata.content_type)

    return app


__all__ = [
    "DMS_RESOURCE",
    "DmsDocumentDeleted",
    "DmsDocumentNotFound",
    "DmsSdk",
    "InternalDocumentMetadata",
    "PublicDocumentMetadata",
    "build_dms_app",
]

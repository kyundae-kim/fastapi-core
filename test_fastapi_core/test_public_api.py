import fastapi_core


def test_public_api_exports_curated_symbols_only():
    exported = set(fastapi_core.__all__)

    assert "create_app" in exported
    assert "KeycloakAuthProvider" in exported
    assert "create_milvus_client" in exported
    assert "create_async_milvus_client" in exported
    assert "get_langfuse_client" in exported

    removed_exports = {
        "extract_roles",
        "extract_scopes",
        "run_in_transaction",
        "create_langfuse_client",
        "check_milvus_connection",
        "check_async_milvus_connection",
        "ensure_collection_exists",
        "ensure_async_collection_exists",
        "list_collection_names",
        "list_async_collection_names",
        "check_ollama_connection",
        "list_model_names",
        "generate_text",
        "generate_presigned_get_url",
        "generate_presigned_put_url",
    }
    assert exported.isdisjoint(removed_exports)

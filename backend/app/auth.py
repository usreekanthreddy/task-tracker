"""Entra ID JWT validation using fastapi-azure-auth (single-tenant SPA flow).

The React SPA acquires a token for our API scope and includes it as a Bearer
header. fastapi-azure-auth validates the signature, issuer, and audience.
"""
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer

from .settings import get_settings

_settings = get_settings()

azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=_settings.API_CLIENT_ID,
    tenant_id=_settings.TENANT_ID,
    scopes={
        f"api://{_settings.API_CLIENT_ID}/{_settings.API_SCOPE_NAME}": _settings.API_SCOPE_NAME,
    },
)

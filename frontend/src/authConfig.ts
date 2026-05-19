import { Configuration, LogLevel } from "@azure/msal-browser";

const tenantId = import.meta.env.VITE_TENANT_ID;
const spaClientId = import.meta.env.VITE_SPA_CLIENT_ID;
const apiClientId = import.meta.env.VITE_API_CLIENT_ID;
const apiScopeName = import.meta.env.VITE_API_SCOPE_NAME ?? "access_as_user";

export const msalConfig: Configuration = {
  auth: {
    clientId: spaClientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (_level, message) => console.log(message),
      logLevel: LogLevel.Warning,
    },
  },
};

// Scope to request when calling our FastAPI backend
export const apiRequest = {
  scopes: [`api://${apiClientId}/${apiScopeName}`],
};

export const apiBaseUrl: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

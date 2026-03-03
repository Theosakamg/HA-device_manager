/**
 * Base API client with authentication and error handling.
 */

/** Home Assistant element interface for auth token extraction. */
interface HomeAssistantElement extends HTMLElement {
  hass?: {
    auth?: { data?: { access_token?: string } };
    connection?: { options?: { auth?: { data?: { access_token?: string } } } };
  };
}

/**
 * Convert a snake_case key to camelCase.
 */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

/**
 * Convert a camelCase key to snake_case.
 */
function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

/**
 * Recursively convert all keys in an object from snake_case to camelCase.
 */
function camelizeKeys(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(camelizeKeys);
  }
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        toCamelCase(k),
        camelizeKeys(v),
      ])
    );
  }
  return obj;
}

/**
 * Recursively convert all keys in an object from camelCase to snake_case.
 */
function snakeizeKeys(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(snakeizeKeys);
  }
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        toSnakeCase(k),
        snakeizeKeys(v),
      ])
    );
  }
  return obj;
}

export class BaseClient {
  protected baseUrl: string;

  constructor(basePath: string = "/api/device_manager") {
    this.baseUrl = basePath;
  }

  /**
   * Get the Home Assistant authentication token.
   * Checks current document and parent frame (iframe context).
   */
  protected getAuthToken(): string {
    try {
      // Try current document first, then parent (iframe context)
      const docs = [document];
      try {
        if (window.parent && window.parent !== window) {
          docs.push(window.parent.document);
        }
      } catch {
        /* cross-origin, ignore */
      }

      for (const doc of docs) {
        const ha = doc.querySelector(
          "home-assistant"
        ) as HomeAssistantElement | null;
        if (ha?.hass?.auth?.data?.access_token) {
          return ha.hass.auth.data.access_token;
        }
        if (ha?.hass?.connection?.options?.auth?.data?.access_token) {
          return ha.hass.connection.options.auth.data.access_token;
        }
      }
    } catch (e) {
      console.error("Failed to get auth token:", e);
    }
    return "";
  }

  /**
   * Build request headers. Only includes Authorization if a token is available,
   * allowing HA to fall back to cookie/session auth in iframe context.
   */
  protected buildHeaders(contentType?: string): Record<string, string> {
    const headers: Record<string, string> = {};
    const token = this.getAuthToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (contentType) {
      headers["Content-Type"] = contentType;
    }
    return headers;
  }

  /**
   * Send a GET request and return camelCase-converted JSON.
   */
  protected async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "GET",
      headers: this.buildHeaders("application/json"),
      credentials: "same-origin",
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `Request failed: ${response.statusText}`);
    }
    const data = await response.json();
    return camelizeKeys(data) as T;
  }

  /**
   * Send a POST request with snake_case-converted body.
   */
  protected async post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.buildHeaders("application/json"),
      credentials: "same-origin",
      body: JSON.stringify(snakeizeKeys(body)),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `Request failed: ${response.statusText}`);
    }
    const data = await response.json();
    return camelizeKeys(data) as T;
  }

  /**
   * Send a PUT request with snake_case-converted body.
   */
  protected async put<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "PUT",
      headers: this.buildHeaders("application/json"),
      credentials: "same-origin",
      body: JSON.stringify(snakeizeKeys(body)),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `Request failed: ${response.statusText}`);
    }
    const data = await response.json();
    return camelizeKeys(data) as T;
  }

  /**
   * Send a DELETE request.
   */
  protected async del<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: this.buildHeaders("application/json"),
      credentials: "same-origin",
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `Request failed: ${response.statusText}`);
    }
    const data = await response.json();
    return camelizeKeys(data) as T;
  }

  /**
   * Send a file upload via multipart/form-data.
   */
  protected async upload<T>(
    path: string,
    file: File,
    fieldName: string = "file"
  ): Promise<T> {
    const form = new FormData();
    form.append(fieldName, file, file.name);
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.buildHeaders(),
      credentials: "same-origin",
      body: form,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `Request failed: ${response.statusText}`);
    }
    const data = await response.json();
    return camelizeKeys(data) as T;
  }
}

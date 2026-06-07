const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

async function apiFetch(urlOrPath, options = {}) {
    const token = localStorage.getItem("session_token");
    const headers = {
        ...(options.headers || {})
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    let requestBody = options.body;
    if (requestBody && !(requestBody instanceof FormData)) {
        if (typeof requestBody === "object") {
            requestBody = JSON.stringify(requestBody);
        }
        if (!headers["Content-Type"]) {
            headers["Content-Type"] = "application/json";
        }
    }

    const fullUrl = urlOrPath.startsWith("http")
        ? urlOrPath
        : `${API_BASE_URL}${urlOrPath}`;

    return fetch(fullUrl, {
        ...options,
        body: requestBody,
        headers
    });
}

async function request(path, options = {}) {
    const response = await apiFetch(path, options);

    if (!response.ok) {
        let detail = "Error inesperado";
        try {
            const payload = await response.json();
            detail = payload.detail || detail;
        } catch (_error) {
            detail = response.statusText || detail;
        }
        throw new Error(detail);
    }

    return response.json();
}

export const apiClient = {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body: body })
};

export { API_BASE_URL, apiFetch };

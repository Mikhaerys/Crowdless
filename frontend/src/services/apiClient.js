const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    });

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
    post: (path, body) => request(path, { method: "POST", body: JSON.stringify(body) })
};

export { API_BASE_URL };

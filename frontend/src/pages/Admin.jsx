import { useState } from "react";

const ADMIN_USER = "museo";
const ADMIN_PASS = "unicauca2026";
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

function LoginForm({ onLogin }) {
    const [user, setUser] = useState("");
    const [pass, setPass] = useState("");
    const [error, setError] = useState("");

    function handleSubmit() {
        if (user === ADMIN_USER && pass === ADMIN_PASS) {
            onLogin();
            return;
        }
        setError("Usuario o contrasena incorrectos.");
    }

    return (
        <section className="card flow-section" style={{ maxWidth: 420, margin: "4rem auto" }}>
            <p className="eyebrow">Panel administrativo</p>
            <h1>Acceso museo</h1>
            <p className="subtext">Ingresa tus credenciales para gestionar los tiquetes.</p>

            {error ? <p className="error-box">{error}</p> : null}

            <div className="field">
                <label htmlFor="admin-user">Usuario</label>
                <input
                    id="admin-user"
                    type="text"
                    value={user}
                    onChange={(event) => setUser(event.target.value)}
                    placeholder="usuario"
                    autoComplete="username"
                />
            </div>

            <div className="field">
                <label htmlFor="admin-pass">Contrasena</label>
                <input
                    id="admin-pass"
                    type="password"
                    value={pass}
                    onChange={(event) => setPass(event.target.value)}
                    placeholder="********"
                    autoComplete="current-password"
                    onKeyDown={(event) => event.key === "Enter" && handleSubmit()}
                />
            </div>

            <div className="hero-actions">
                <button type="button" className="button button-primary" onClick={handleSubmit}>
                    Ingresar
                </button>
            </div>
        </section>
    );
}

function AdminPanel({ onLogout }) {
    const [ticketId, setTicketId] = useState("");
    const [ticket, setTicket] = useState(null);
    const [error, setError] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const [renewLoading, setRenewLoading] = useState(false);

    async function handleRenew() {
        const cleanId = ticketId.trim();
        if (!cleanId) {
            return;
        }

        setRenewLoading(true);
        setError("");
        setSuccessMsg("");

        try {
            const response = await fetch(`${API_BASE}/validation/tickets/${cleanId}/renew`, {
                method: "POST"
            });

            if (response.status === 404) {
                setError("No se encontro el tiquete.");
                return;
            }
            if (response.status === 409) {
                const data = await response.json();
                setError(data.detail || "Este tiquete ya fue usado en la entrada.");
                return;
            }
            if (!response.ok) {
                setError("Error al renovar el tiquete. Intenta de nuevo.");
                return;
            }

            const renewed = await response.json();
            setTicket(renewed);
            setSuccessMsg("QR renovado correctamente. El codigo anterior ya no es valido.");
        } catch {
            setError("No se pudo conectar con el servidor.");
        } finally {
            setRenewLoading(false);
        }
    }

    function handleReset() {
        setTicketId("");
        setTicket(null);
        setError("");
        setSuccessMsg("");
    }

    return (
        <section className="card flow-section">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                    <p className="eyebrow">Panel administrativo</p>
                    <h1 style={{ marginBottom: 0 }}>Gestion de tiquetes</h1>
                </div>
                <button type="button" className="button button-secondary" onClick={onLogout}>
                    Cerrar sesion
                </button>
            </div>

            <p className="subtext">
                Ingresa el ID de un tiquete para renovar su codigo QR. El visitante debera volver a la
                pantalla de confirmacion para ver el nuevo QR.
            </p>

            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                <div className="field" style={{ flex: 1, minWidth: 260 }}>
                    <label htmlFor="ticket-id">ID del tiquete</label>
                    <input
                        id="ticket-id"
                        type="text"
                        value={ticketId}
                        onChange={(event) => {
                            setTicketId(event.target.value);
                            setTicket(null);
                            setError("");
                            setSuccessMsg("");
                        }}
                        placeholder="Ej: aB3kLmNpQr..."
                        onKeyDown={(event) => event.key === "Enter" && handleRenew()}
                    />
                </div>
            </div>

            {error ? <p className="error-box">{error}</p> : null}
            {successMsg ? <p className="success-box">{successMsg}</p> : null}

            {ticket && ticket.qr_code ? (
                <div className="qr-section">
                    <h2>Nuevo QR generado</h2>
                    <div className="qr-grid">
                        <div className="qr-card">
                            <p className="qr-visitor-name">{ticket.visitor_name}</p>
                            <img
                                src={ticket.qr_code}
                                alt={`Nuevo QR de ${ticket.visitor_name}`}
                                className="qr-image"
                            />
                            <small className="qr-ticket-id">ID: {ticket.ticket_id}</small>
                        </div>
                    </div>
                    <p className="admin-notice">
                        Muestrale este QR al visitante o indicale que revise su pantalla de confirmacion
                        para obtener el codigo actualizado.
                    </p>
                </div>
            ) : null}

            <div className="hero-actions">
                <button
                    type="button"
                    className="button button-primary"
                    onClick={handleRenew}
                    disabled={!ticketId.trim() || renewLoading}
                >
                    {renewLoading ? "Renovando..." : "Renovar QR"}
                </button>
                {ticket ? (
                    <button type="button" className="button button-secondary" onClick={handleReset}>
                        Buscar otro tiquete
                    </button>
                ) : null}
            </div>

            <p className="admin-notice">
                <strong>Importante:</strong> solo renueva el QR si el visitante reporto perdida, robo o
                sospecha de fraude. El codigo anterior queda inmediatamente invalido.
            </p>
        </section>
    );
}

function AdminPage() {
    const [authenticated, setAuthenticated] = useState(false);

    if (!authenticated) {
        return <LoginForm onLogin={() => setAuthenticated(true)} />;
    }

    return <AdminPanel onLogout={() => setAuthenticated(false)} />;
}

export default AdminPage;

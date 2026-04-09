import { useState } from "react";
import { useNavigate } from "react-router-dom";

// Credenciales hardcodeadas para el proyecto académico
const ADMIN_USER = "museo";
const ADMIN_PASS = "unicauca2026";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

// ── Login ────────────────────────────────────────────────
function LoginForm({ onLogin }) {
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState("");

  function handleSubmit() {
    if (user === ADMIN_USER && pass === ADMIN_PASS) {
      onLogin();
    } else {
      setError("Usuario o contraseña incorrectos.");
    }
  }

  return (
    <section className="card flow-section" style={{ maxWidth: 420, margin: "4rem auto" }}>
      <p className="eyebrow">Panel administrativo</p>
      <h1>Acceso museo</h1>
      <p className="subtext">
        Ingresa tus credenciales para gestionar los tiquetes.
      </p>

      {error && <p className="error-box">{error}</p>}

      <div className="field">
        <label htmlFor="admin-user">Usuario</label>
        <input
          id="admin-user"
          type="text"
          value={user}
          onChange={(e) => setUser(e.target.value)}
          placeholder="usuario"
          autoComplete="username"
        />
      </div>

      <div className="field">
        <label htmlFor="admin-pass">Contraseña</label>
        <input
          id="admin-pass"
          type="password"
          value={pass}
          onChange={(e) => setPass(e.target.value)}
          placeholder="••••••••"
          autoComplete="current-password"
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />
      </div>

      <div className="hero-actions">
        <button className="button button-primary" onClick={handleSubmit}>
          Ingresar
        </button>
      </div>
    </section>
  );
}

// ── Panel principal ──────────────────────────────────────
function AdminPanel({ onLogout }) {
  const [ticketId, setTicketId] = useState("");
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [renewLoading, setRenewLoading] = useState(false);

  // Buscar ticket por ID
  async function handleSearch() {
    if (!ticketId.trim()) return;
    setLoading(true);
    setError("");
    setTicket(null);
    setSuccessMsg("");

    try {
      const res = await fetch(`${API_BASE}/validation/tickets/${ticketId.trim()}`);
      if (res.status === 404) {
        setError("No se encontró ningún tiquete con ese ID.");
        return;
      }
      if (!res.ok) {
        setError("Error al buscar el tiquete. Intenta de nuevo.");
        return;
      }
      // El endpoint de validación no retorna el ticket completo,
      // usamos el endpoint de tickets por booking si existe,
      // pero como solo tenemos el ticket_id, construimos la info desde
      // el renew (que sí retorna TicketResponse completo)
      // Por ahora mostramos un estado provisional
      setTicket({ ticket_id: ticketId.trim(), found: true });
    } catch {
      setError("No se pudo conectar con el servidor.");
    } finally {
      setLoading(false);
    }
  }

  // Renovar QR
  async function handleRenew() {
    if (!ticketId.trim()) return;
    setRenewLoading(true);
    setError("");
    setSuccessMsg("");

    try {
      const res = await fetch(
        `${API_BASE}/validation/tickets/${ticketId.trim()}/renew`,
        { method: "POST" }
      );

      if (res.status === 404) {
        setError("No se encontró el tiquete.");
        return;
      }
      if (res.status === 409) {
        const data = await res.json();
        setError(data.detail ?? "Este tiquete ya fue usado en la entrada.");
        return;
      }
      if (!res.ok) {
        setError("Error al renovar el tiquete. Intenta de nuevo.");
        return;
      }

      const renewed = await res.json();
      setTicket(renewed);
      setSuccessMsg(
        `✓ QR renovado correctamente. El código anterior ya no es válido.`
      );
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
      {/* Encabezado */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <p className="eyebrow">Panel administrativo</p>
          <h1 style={{ marginBottom: 0 }}>Gestión de tiquetes</h1>
        </div>
        <button className="button button-secondary" onClick={onLogout}>
          Cerrar sesión
        </button>
      </div>

      <p className="subtext">
        Ingresa el ID de un tiquete para renovar su código QR. El visitante
        deberá volver a la pantalla de confirmación para ver el nuevo QR.
      </p>

      {/* Buscador */}
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <div className="field" style={{ flex: 1, minWidth: 260 }}>
          <label htmlFor="ticket-id">ID del tiquete</label>
          <input
            id="ticket-id"
            type="text"
            value={ticketId}
            onChange={(e) => { setTicketId(e.target.value); setTicket(null); setError(""); setSuccessMsg(""); }}
            placeholder="Ej: aB3kLmNpQr..."
            onKeyDown={(e) => e.key === "Enter" && handleRenew()}
          />
        </div>
      </div>

      {/* Mensajes */}
      {error && <p className="error-box">{error}</p>}
      {successMsg && (
        <p style={{
          border: "1px solid #a3d4bc",
          background: "#eaf7f1",
          color: "#176b52",
          borderRadius: 12,
          padding: "0.65rem 0.8rem",
          margin: 0,
        }}>
          {successMsg}
        </p>
      )}

      {/* Ticket renovado — muestra el nuevo QR */}
      {ticket && ticket.qr_code && (
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
            Muéstrale este QR al visitante o indícale que revise su pantalla
            de confirmación para obtener el código actualizado.
          </p>
        </div>
      )}

      {/* Acciones */}
      <div className="hero-actions">
        <button
          className="button button-primary"
          onClick={handleRenew}
          disabled={!ticketId.trim() || renewLoading}
        >
          {renewLoading ? "Renovando..." : "Renovar QR"}
        </button>
        {ticket && (
          <button className="button button-secondary" onClick={handleReset}>
            Buscar otro tiquete
          </button>
        )}
      </div>

      <p className="admin-notice">
        <strong>Importante:</strong> Solo renueva el QR si el visitante reportó
        pérdida, robo o sospecha de fraude. El código anterior queda
        inmediatamente inválido.
      </p>
    </section>
  );
}

// ── Página principal ─────────────────────────────────────
function AdminPage() {
  const [authenticated, setAuthenticated] = useState(false);

  if (!authenticated) {
    return <LoginForm onLogin={() => setAuthenticated(true)} />;
  }

  return <AdminPanel onLogout={() => setAuthenticated(false)} />;
}

export default AdminPage;
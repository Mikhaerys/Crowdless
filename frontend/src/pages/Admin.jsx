import { useState, useEffect } from "react";
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

// ── SVG Chart Component ──────────────────────────────────
function SVGBarChart({ data, xKey, yKey, title, yLabel }) {
  if (!data || data.length === 0) {
    return <p className="empty-state">No hay datos para graficar en este rango.</p>;
  }

  const svgWidth = 600;
  const svgHeight = 280;
  const padding = { top: 30, right: 30, bottom: 50, left: 50 };
  const chartWidth = svgWidth - padding.left - padding.right;
  const chartHeight = svgHeight - padding.top - padding.bottom;

  const maxVal = Math.max(...data.map(d => d[yKey]), 1);
  const barWidth = Math.max(15, (chartWidth / data.length) - 16);
  const gap = (chartWidth - (barWidth * data.length)) / (data.length + 1);

  // Generate grid ticks
  const tickCount = 5;
  const ticks = Array.from({ length: tickCount }, (_, i) => Math.round((maxVal / (tickCount - 1)) * i));

  return (
    <div className="chart-container">
      <div className="chart-title">
        <span>{title}</span>
        <small style={{ color: "var(--ink-soft)" }}>Valores expresados en {yLabel.toLowerCase()}</small>
      </div>
      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} width="100%" height="auto" style={{ overflow: "visible" }}>
        {/* Y Axis Grid Lines */}
        {ticks.map((tick, i) => {
          const y = padding.top + chartHeight - (tick / maxVal) * chartHeight;
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + chartWidth}
                y2={y}
                className="chart-grid-line"
              />
              <text
                x={padding.left - 10}
                y={y + 4}
                textAnchor="end"
                className="chart-text"
              >
                {tick}
              </text>
            </g>
          );
        })}

        {/* X Axis Line */}
        <line
          x1={padding.left}
          y1={padding.top + chartHeight}
          x2={padding.left + chartWidth}
          y2={padding.top + chartHeight}
          className="chart-axis-line"
        />

        {/* Bars */}
        {data.map((d, i) => {
          const val = d[yKey];
          const barHeight = (val / maxVal) * chartHeight;
          const x = padding.left + gap + i * (barWidth + gap);
          const y = padding.top + chartHeight - barHeight;

          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                className="chart-bar"
              />
              {/* Value on top of bar */}
              {val > 0 && (
                <text
                  x={x + barWidth / 2}
                  y={y - 6}
                  className="chart-text"
                  fontWeight="bold"
                  fill="var(--ink-strong)"
                >
                  {val}
                </text>
              )}
              {/* Date label at bottom */}
              <text
                x={x + barWidth / 2}
                y={padding.top + chartHeight + 20}
                className="chart-text"
                transform={`rotate(-25, ${x + barWidth / 2}, ${padding.top + chartHeight + 20})`}
                textAnchor="end"
              >
                {d[xKey]}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── SVG Line/Area Chart for Predictions ──────────────────
function SVGLineChart({ data, xKey, yKey, title, yLabel }) {
  if (!data || data.length === 0) {
    return <p className="empty-state">No hay datos de predicción para graficar.</p>;
  }

  const svgWidth = 600;
  const svgHeight = 280;
  const padding = { top: 30, right: 30, bottom: 50, left: 50 };
  const chartWidth = svgWidth - padding.left - padding.right;
  const chartHeight = svgHeight - padding.top - padding.bottom;

  const maxVal = Math.max(...data.map(d => d[yKey]), 1);

  // Calculate coordinates for each point
  const points = data.map((d, i) => {
    const x = padding.left + (data.length > 1 ? (i / (data.length - 1)) * chartWidth : chartWidth / 2);
    const y = padding.top + chartHeight - (d[yKey] / maxVal) * chartHeight;
    return { x, y, value: d[yKey], label: d[xKey] };
  });

  // Construct SVG Path
  const pathD = points.reduce((acc, p, i) => {
    return acc + `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`;
  }, "");

  // Area under path
  const areaD = points.length > 0 
    ? `${pathD} L ${points[points.length - 1].x} ${padding.top + chartHeight} L ${points[0].x} ${padding.top + chartHeight} Z`
    : "";

  // Grid lines
  const tickCount = 5;
  const ticks = Array.from({ length: tickCount }, (_, i) => Math.round((maxVal / (tickCount - 1)) * i));

  return (
    <div className="chart-container">
      <div className="chart-title">
        <span>{title}</span>
        <small style={{ color: "var(--ink-soft)" }}>Valores expresados en {yLabel.toLowerCase()}</small>
      </div>
      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} width="100%" height="auto" style={{ overflow: "visible" }}>
        {/* Y Axis Grid Lines */}
        {ticks.map((tick, i) => {
          const y = padding.top + chartHeight - (tick / maxVal) * chartHeight;
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + chartWidth}
                y2={y}
                className="chart-grid-line"
              />
              <text
                x={padding.left - 10}
                y={y + 4}
                textAnchor="end"
                className="chart-text"
              >
                {tick}
              </text>
            </g>
          );
        })}

        {/* X Axis Line */}
        <line
          x1={padding.left}
          y1={padding.top + chartHeight}
          x2={padding.left + chartWidth}
          y2={padding.top + chartHeight}
          className="chart-axis-line"
        />

        {/* Area under the line */}
        {points.length > 0 && (
          <path
            d={areaD}
            fill="rgba(212, 77, 41, 0.15)"
            stroke="none"
          />
        )}

        {/* Line path */}
        {points.length > 0 && (
          <path
            d={pathD}
            fill="none"
            stroke="var(--brand)"
            strokeWidth="3"
          />
        )}

        {/* Dots & Values */}
        {points.map((p, i) => {
          const showValue = data.length <= 15 || i % Math.ceil(data.length / 10) === 0 || i === data.length - 1;
          const showLabel = data.length <= 10 || i % Math.ceil(data.length / 8) === 0 || i === data.length - 1;

          return (
            <g key={i}>
              <circle
                cx={p.x}
                cy={p.y}
                r="4.5"
                fill="var(--brand)"
                stroke="#fff"
                strokeWidth="2"
              />
              {showValue && (
                <text
                  x={p.x}
                  y={p.y - 10}
                  className="chart-text"
                  fontWeight="bold"
                  fill="var(--ink-strong)"
                >
                  {p.value}
                </text>
              )}
              {showLabel && (
                <text
                  x={p.x}
                  y={padding.top + chartHeight + 20}
                  className="chart-text"
                  transform={`rotate(-25, ${p.x}, ${padding.top + chartHeight + 20})`}
                  textAnchor="end"
                >
                  {p.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── Panel principal ──────────────────────────────────────
function AdminPanel({ onLogout }) {
  const [activeTab, setActiveTab] = useState("tickets");

  // State for QR Renewal
  const [ticketId, setTicketId] = useState("");
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [renewLoading, setRenewLoading] = useState(false);

  // State for Realtime Visitor Monitoring
  const [currentVisitors, setCurrentVisitors] = useState(null);
  const [loadingRealtime, setLoadingRealtime] = useState(false);

  // State for Statistical Reports
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [summary, setSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  // State for Attendance History
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState("");

  // State for Attendance Prediction
  const [predictStartDate, setPredictStartDate] = useState(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split("T")[0];
  });
  const [predictDays, setPredictDays] = useState(7);
  const [predictionData, setPredictionData] = useState(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [predictionError, setPredictionError] = useState("");
  const [reloadingModel, setReloadingModel] = useState(false);

  // Fetch functions
  async function fetchRealtime() {
    setLoadingRealtime(true);
    try {
      const res = await fetch(`${API_BASE}/reports/current-visitors`);
      if (res.ok) {
        const data = await res.json();
        setCurrentVisitors(data.current_visitors);
      }
    } catch (e) {
      console.error("Error fetching realtime visitors", e);
    } finally {
      setLoadingRealtime(false);
    }
  }

  async function fetchSummary() {
    setLoadingSummary(true);
    setSummaryError("");
    try {
      const res = await fetch(`${API_BASE}/reports/summary?start_date=${startDate}&end_date=${endDate}`);
      if (!res.ok) {
        setSummaryError("Error al obtener las estadísticas.");
        return;
      }
      const data = await res.json();
      setSummary(data);
    } catch {
      setSummaryError("Error de conexión al servidor.");
    } finally {
      setLoadingSummary(false);
    }
  }

  async function fetchHistory() {
    setLoadingHistory(true);
    setHistoryError("");
    try {
      const res = await fetch(`${API_BASE}/reports/attendance-history?limit=50`);
      if (!res.ok) {
        setHistoryError("Error al obtener el historial de asistencia.");
        return;
      }
      const data = await res.json();
      setHistory(data);
    } catch {
      setHistoryError("Error de conexión al servidor.");
    } finally {
      setLoadingHistory(false);
    }
  }

  async function fetchPrediction() {
    setLoadingPrediction(true);
    setPredictionError("");
    try {
      const res = await fetch(`${API_BASE}/reports/predict-attendance?target_date=${predictStartDate}&days=${predictDays}`);
      if (!res.ok) {
        setPredictionError("Error al obtener las predicciones del servidor.");
        return;
      }
      const data = await res.json();
      setPredictionData(data);
    } catch {
      setPredictionError("Error de conexión al servidor.");
    } finally {
      setLoadingPrediction(false);
    }
  }

  async function handleReloadModel() {
    setReloadingModel(true);
    setPredictionError("");
    try {
      const res = await fetch(`${API_BASE}/reports/predict-attendance/reload`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        if (data.model_loaded) {
          setSuccessMsg("✓ Modelo cargado correctamente desde disco.");
          fetchPrediction();
        } else {
          setPredictionError("No se pudo cargar el modelo. ¿Subiste los archivos correctos a backend/app/resources/model?");
        }
      } else {
        setPredictionError("Error al enviar la solicitud de recarga.");
      }
    } catch {
      setPredictionError("Error de conexión al servidor.");
    } finally {
      setReloadingModel(false);
    }
  }

  // Load predictions
  useEffect(() => {
    if (activeTab === "prediction") {
      fetchPrediction();
    }
  }, [activeTab]);

  // Poll current visitors in real-time
  useEffect(() => {
    if (activeTab === "realtime") {
      fetchRealtime();
      const interval = setInterval(fetchRealtime, 30000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  // Load summary statistics
  useEffect(() => {
    if (activeTab === "reports") {
      fetchSummary();
    }
  }, [activeTab]);

  // Load attendance history
  useEffect(() => {
    if (activeTab === "history") {
      fetchHistory();
    }
  }, [activeTab]);

  // Search/Renew QR handlers
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
      setTicket({ ticket_id: ticketId.trim(), found: true });
    } catch {
      setError("No se pudo conectar con el servidor.");
    } finally {
      setLoading(false);
    }
  }

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

  // Date helper formatting
  function formatDateTime(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString("es-CO", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  return (
    <section className="card flow-section" style={{ minWidth: "100%" }}>
      {/* Encabezado */}
      <div className="admin-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p className="eyebrow" style={{ margin: 0 }}>Panel administrativo</p>
          <h1 style={{ margin: "0.25rem 0 0", fontSize: "1.8rem" }}>Crowdless Dashboard</h1>
        </div>
        <button className="button button-secondary" onClick={onLogout}>
          Cerrar sesión
        </button>
      </div>

      {/* Tabs */}
      <nav className="admin-tabs">
        <button
          className={`admin-tab-btn ${activeTab === "tickets" ? "active" : ""}`}
          onClick={() => setActiveTab("tickets")}
        >
          🎟️ Gestión de Tiquetes
        </button>
        <button
          className={`admin-tab-btn ${activeTab === "realtime" ? "active" : ""}`}
          onClick={() => setActiveTab("realtime")}
        >
          🟢 Monitoreo en Vivo
        </button>
        <button
          className={`admin-tab-btn ${activeTab === "reports" ? "active" : ""}`}
          onClick={() => setActiveTab("reports")}
        >
          📊 Reportes y Gráficas
        </button>
        <button
          className={`admin-tab-btn ${activeTab === "history" ? "active" : ""}`}
          onClick={() => setActiveTab("history")}
        >
          📋 Historial de Asistencia
        </button>
        <button
          className={`admin-tab-btn ${activeTab === "prediction" ? "active" : ""}`}
          onClick={() => setActiveTab("prediction")}
        >
          🔮 Predicción de Afluencia
        </button>
      </nav>

      {/* TAB CONTENT */}

      {/* 1. Gestión de Tiquetes */}
      {activeTab === "tickets" && (
        <div className="flow-section">
          <p className="subtext">
            Ingresa el ID de un tiquete para renovar su código QR. El visitante
            deberá volver a la pantalla de confirmación para ver el nuevo QR.
          </p>

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "flex-end" }}>
            <div className="field" style={{ flex: 1, minWidth: 260 }}>
              <label htmlFor="ticket-id">ID del tiquete</label>
              <input
                id="ticket-id"
                type="text"
                value={ticketId}
                onChange={(e) => {
                  setTicketId(e.target.value);
                  setTicket(null);
                  setError("");
                  setSuccessMsg("");
                }}
                placeholder="Ej: aB3kLmNpQr..."
                onKeyDown={(e) => e.key === "Enter" && handleRenew()}
              />
            </div>
            <button
              className="button button-primary"
              onClick={handleRenew}
              disabled={!ticketId.trim() || renewLoading}
              style={{ height: "46px" }}
            >
              {renewLoading ? "Renovando..." : "Renovar QR"}
            </button>
            {ticket && (
              <button className="button button-secondary" onClick={handleReset} style={{ height: "46px" }}>
                Limpiar búsqueda
              </button>
            )}
          </div>

          {error && <p className="error-box">{error}</p>}
          {successMsg && <p className="success-box">{successMsg}</p>}

          {ticket && ticket.qr_code && (
            <div className="qr-section" style={{ alignItems: "center" }}>
              <h2>Nuevo QR generado</h2>
              <div className="qr-card">
                <p className="qr-visitor-name">{ticket.visitor_name}</p>
                <img
                  src={ticket.qr_code}
                  alt={`Nuevo QR de ${ticket.visitor_name}`}
                  className="qr-image"
                />
                <small className="qr-ticket-id">ID: {ticket.ticket_id}</small>
              </div>
              <p className="admin-notice" style={{ maxWidth: 450, textAlign: "center" }}>
                Muéstrale este QR al visitante o indícale que revise su pantalla
                de confirmación para obtener el código actualizado.
              </p>
            </div>
          )}

          <p className="admin-notice">
            <strong>Importante:</strong> Solo renueva el QR si el visitante reportó
            pérdida, robo o sospecha de fraude. El código anterior queda
            inmediatamente inválido.
          </p>
        </div>
      )}

      {/* 2. Monitoreo en Vivo */}
      {activeTab === "realtime" && (
        <div className="flow-section">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <p className="subtext">
                Control de aforo y visitantes en tiempo real en las salas de exhibición del museo.
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span className="realtime-indicator">
                <span className="pulse-dot"></span> EN VIVO
              </span>
              <button
                className="button button-secondary"
                onClick={fetchRealtime}
                disabled={loadingRealtime}
                style={{ padding: "0.5rem 0.8rem", fontSize: "0.85rem" }}
              >
                {loadingRealtime ? "Actualizando..." : "Refrescar"}
              </button>
            </div>
          </div>

          <div className="metric-grid">
            <div className="metric-card ok">
              <h3 className="metric-title">Visitantes en el Museo</h3>
              <p className="metric-value">
                {currentVisitors !== null ? currentVisitors : "—"}
              </p>
              <small style={{ color: "var(--ink-soft)", display: "block", marginTop: "0.5rem" }}>
                Personas actualmente activas en salas.
              </small>
            </div>
          </div>

          <div className="admin-notice" style={{ background: "#f4f8f5", border: "1px dashed var(--ok)", color: "var(--ok)" }}>
            <strong>Cálculo del aforo en tiempo real:</strong> Para asegurar la precisión del conteo de público,
            el sistema considera a los visitantes cuyos tiquetes fueron escaneados y validados dentro de la franja
            horaria (bloque de tiempo) que se encuentra activa en este preciso instante. Una vez transcurrido el
            bloque horario, el sistema asume de forma automática la salida de dichos visitantes.
          </div>
        </div>
      )}

      {/* 3. Reportes y Gráficas */}
      {activeTab === "reports" && (
        <div className="flow-section">
          <p className="subtext">
            Consulta los ingresos, número total de reservas, distribución de ventas por franjas horarias y el listado consolidado de entradas expedidas.
          </p>

          <div className="date-filter-row">
            <div className="field">
              <label htmlFor="start-date">Fecha de Inicio</label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="end-date">Fecha Fin</label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <button
              className="button button-primary"
              onClick={fetchSummary}
              disabled={loadingSummary}
              style={{ height: "46px" }}
            >
              {loadingSummary ? "Cargando..." : "Consultar Rango"}
            </button>
          </div>

          {summaryError && <p className="error-box">{summaryError}</p>}

          {loadingSummary && (
            <div className="loading-row">
              <span className="loader"></span>
              <span>Cargando datos del servidor...</span>
            </div>
          )}

          {summary && !loadingSummary && (
            <>
              {/* Tarjetas de Metricas */}
              <div className="metric-grid">
                <div className="metric-card">
                  <h3 className="metric-title">Reservas Totales</h3>
                  <p className="metric-value">{summary.total_bookings}</p>
                </div>
                <div className="metric-card">
                  <h3 className="metric-title">Tiquetes Vendidos</h3>
                  <p className="metric-value">{summary.total_tickets}</p>
                </div>
                <div className="metric-card ok">
                  <h3 className="metric-title">Ingresos Recaudados</h3>
                  <p className="metric-value">
                    ${summary.approved_revenue.toLocaleString("es-CO", { minimumFractionDigits: 2 })}
                  </p>
                </div>
              </div>

              {/* Grafica Interactiva SVG */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1.5rem" }}>
                <SVGBarChart
                  title="Reservas por Día"
                  xKey="date"
                  yKey="bookings"
                  yLabel="Reservas"
                  data={Object.entries(summary.daily_bookings)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([date, bookings]) => ({ date, bookings }))
                  }
                />
              </div>

              {/* Desglose de Ventas por Dia */}
              <div style={{ marginTop: "1.5rem" }}>
                <h2>Entradas y Reservas por Día</h2>
                <div className="admin-table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Fecha de Visita</th>
                        <th>Reservas Totales</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(summary.daily_bookings).length === 0 ? (
                        <tr>
                          <td colSpan="2" style={{ textAlign: "center" }}>No hay reservas registradas en este período.</td>
                        </tr>
                      ) : (
                        Object.entries(summary.daily_bookings)
                          .sort(([a], [b]) => b.localeCompare(a))
                          .map(([date, count]) => (
                            <tr key={date}>
                              <td><strong>{date}</strong></td>
                              <td>{count} reservas</td>
                            </tr>
                          ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Distribucion por Franjas Horarias */}
              <div style={{ marginTop: "1.5rem" }}>
                <h2>Distribución por Franjas Horarias</h2>
                <div className="admin-table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Franja Horaria</th>
                        <th>Tiquetes Vendidos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(summary.slot_ticket_distribution).length === 0 ? (
                        <tr>
                          <td colSpan="2" style={{ textAlign: "center" }}>No hay tiquetes distribuidos en franjas horarias.</td>
                        </tr>
                      ) : (
                        Object.entries(summary.slot_ticket_distribution)
                          .sort(([a], [b]) => a.localeCompare(b))
                          .map(([slotId, count]) => {
                            const parts = slotId.split("_");
                            const datePart = parts[0] || "";
                            const start = parts[1] ? `${parts[1].slice(0, 2)}:${parts[1].slice(2, 4)}` : "";
                            const end = parts[2] ? `${parts[2].slice(0, 2)}:${parts[2].slice(2, 4)}` : "";
                            const label = `${datePart} (${start} - ${end})`;
                            return (
                              <tr key={slotId}>
                               <td>{label}</td>
                               <td><strong>{count}</strong> tiquetes</td>
                              </tr>
                            );
                          })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* 4. Historial de Asistencia */}
      {activeTab === "history" && (
        <div className="flow-section">
          <p className="subtext">
            Listado en tiempo real de los tiquetes escaneados y validados en la entrada del museo.
          </p>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              className="button button-secondary"
              onClick={fetchHistory}
              disabled={loadingHistory}
              style={{ padding: "0.5rem 0.8rem", fontSize: "0.85rem" }}
            >
              {loadingHistory ? "Actualizando..." : "Refrescar Historial"}
            </button>
          </div>

          {historyError && <p className="error-box">{historyError}</p>}

          {loadingHistory && (
            <div className="loading-row">
              <span className="loader"></span>
              <span>Cargando historial de asistencia...</span>
            </div>
          )}

          {!loadingHistory && (
            <div className="admin-table-container">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID Tiquete</th>
                    <th>Visitante</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Fecha de Entrada</th>
                  </tr>
                </thead>
                <tbody>
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: "center" }}>No hay registros de asistencia recientes.</td>
                    </tr>
                  ) : (
                    history.map((ticket) => (
                      <tr key={ticket.ticket_id}>
                        <td><small style={{ fontFamily: "monospace" }}>{ticket.ticket_id}</small></td>
                        <td><strong>{ticket.visitor_name}</strong></td>
                        <td>
                          <span className={`badge badge-${ticket.ticket_type}`}>
                            {ticket.ticket_type === "adult" ? "Adulto" : "Niño"}
                          </span>
                        </td>
                        <td>
                          <span className="badge badge-validated">Validado</span>
                        </td>
                        <td>{formatDateTime(ticket.validated_at)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 5. Predicción de Afluencia */}
      {activeTab === "prediction" && (
        <div className="flow-section">
          <p className="subtext">
            Pronostica de forma inteligente la afluencia de visitantes al museo para los próximos días utilizando modelos predictivos basados en tendencias históricas, días festivos y Semana Santa.
          </p>

          <div className="date-filter-row">
            <div className="field">
              <label htmlFor="predict-start-date">Fecha de Inicio</label>
              <input
                id="predict-start-date"
                type="date"
                value={predictStartDate}
                onChange={(e) => setPredictStartDate(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="predict-days">Horizonte (Días)</label>
              <select
                id="predict-days"
                value={predictDays}
                onChange={(e) => setPredictDays(Number(e.target.value))}
              >
                <option value={7}>7 días (Una semana)</option>
                <option value={15}>15 días (Quincena)</option>
                <option value={30}>30 días (Un mes)</option>
              </select>
            </div>
            <button
              className="button button-primary"
              onClick={fetchPrediction}
              disabled={loadingPrediction}
              style={{ height: "46px" }}
            >
              {loadingPrediction ? "Calculando..." : "Generar Pronóstico"}
            </button>
          </div>

          {predictionError && <p className="error-box">{predictionError}</p>}
          {successMsg && <p className="success-box" style={{ marginBottom: "1rem" }}>{successMsg}</p>}

          {predictionData && !predictionData.model_loaded && (
            <div className="admin-notice" style={{ background: "#fef8f4", border: "1px dashed #e6c280", color: "#a07c3c", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
              <div>
                <strong>Aviso de Modo de Respaldo:</strong> El modelo de Machine Learning no se encuentra disponible o no ha sido cargado en el servidor. El sistema está utilizando un simulador heurístico de respaldo altamente preciso basado en reglas calendáricas.
              </div>
              <button
                className="button button-secondary"
                onClick={handleReloadModel}
                disabled={reloadingModel}
                style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem", whiteSpace: "nowrap" }}
              >
                {reloadingModel ? "Cargando..." : "Cargar Modelo"}
              </button>
            </div>
          )}

          {loadingPrediction && (
            <div className="loading-row" style={{ padding: "2rem", justifyContent: "center", width: "100%" }}>
              <span className="loader" style={{ width: "1.5rem", height: "1.5rem" }}></span>
              <span>Ejecutando algoritmo predictivo y procesando rezagos...</span>
            </div>
          )}

          {predictionData && !loadingPrediction && (
            <>
              {/* Tarjetas de Metricas Predictivas */}
              <div className="metric-grid">
                <div className="metric-card">
                  <h3 className="metric-title">Promedio Diario Estimado</h3>
                  <p className="metric-value">
                    {Math.round(predictionData.forecast.reduce((acc, curr) => acc + curr.prediction, 0) / predictionData.forecast.length)}
                  </p>
                  <small style={{ color: "var(--ink-soft)" }}>visitantes / día</small>
                </div>
                <div className="metric-card">
                  <h3 className="metric-title">Pico Máximo Pronosticado</h3>
                  <p className="metric-value">
                    {Math.max(...predictionData.forecast.map(d => d.prediction))}
                  </p>
                  <small style={{ color: "var(--ink-soft)" }}>
                    El día {predictionData.forecast.reduce((max, curr) => curr.prediction > max.prediction ? curr : max, predictionData.forecast[0]).date}
                  </small>
                </div>
                <div className="metric-card ok">
                  <h3 className="metric-title">Modelo Predictivo</h3>
                  <p className="metric-value" style={{ fontSize: "1.1rem", marginTop: "0.5rem" }}>
                    {predictionData.model_loaded 
                      ? `${predictionData.metadata.nombre_modelo || "XGBoost Regressor"} (v${predictionData.metadata.version || "1.0"})`
                      : "Heurística de Respaldo"}
                  </p>
                  <small style={{ color: "var(--ink-soft)" }}>
                    {predictionData.model_loaded ? "Ejecución ML en servidor" : "Simulador dinámico"}
                  </small>
                </div>
              </div>

              {/* Grafica Lineal SVG */}
              <SVGLineChart
                title="Tendencia de Afluencia Futura"
                xKey="date"
                yKey="prediction"
                yLabel="Visitantes"
                data={predictionData.forecast}
              />

              {/* Tabla de Resultados */}
              <div style={{ marginTop: "1.5rem" }}>
                <h2>Detalle del Pronóstico de Afluencia</h2>
                <div className="admin-table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Día</th>
                        <th>Afluencia Estimada</th>
                        <th>Nivel</th>
                        <th>Factores Relevantes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {predictionData.forecast.map((item) => {
                        let levelLabel = "Baja";
                        if (item.prediction >= 800) {
                          levelLabel = "Pico / Crítica";
                        } else if (item.prediction >= 500) {
                          levelLabel = "Alta";
                        } else if (item.prediction >= 200) {
                          levelLabel = "Media";
                        }

                        const dayNames = {
                          "Monday": "Lunes",
                          "Tuesday": "Martes",
                          "Wednesday": "Miércoles",
                          "Thursday": "Jueves",
                          "Friday": "Viernes",
                          "Saturday": "Sábado",
                          "Sunday": "Domingo"
                        };
                        const translatedDay = dayNames[item.day_name] || item.day_name;

                        const getLevelStyle = (pred) => {
                          if (pred >= 800) return { background: "#ffe7ec", color: "var(--danger)" };
                          if (pred >= 500) return { background: "#e2effd", color: "#1a73e8" };
                          if (pred >= 200) return { background: "#e6f7ef", color: "var(--ok)" };
                          return { background: "#f1f6f3", color: "var(--ink-soft)" };
                        };

                        return (
                          <tr key={item.date} style={item.prediction === 0 ? { background: "#fafafa", opacity: 0.85 } : {}}>
                            <td><strong>{item.date}</strong></td>
                            <td>{translatedDay}</td>
                            <td>
                              <strong style={{ fontSize: "1.05rem" }}>{item.prediction}</strong> visitantes
                            </td>
                            <td>
                              <span className="badge" style={getLevelStyle(item.prediction)}>
                                {levelLabel}
                              </span>
                            </td>
                            <td>
                              <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                                {item.factors.length === 0 ? (
                                  <span style={{ color: "#a0a0a0" }}>Ninguno (Día estándar)</span>
                                ) : (
                                  item.factors.map((factor, fIdx) => {
                                    let style = { background: "#f0f4f2", color: "var(--ink-soft)" };
                                    if (factor.includes("Semana Santa")) {
                                      style = { background: "#fff9e6", color: "#b08500", border: "1px solid #ffe8a3" };
                                    } else if (factor.includes("Festivo")) {
                                      style = { background: "#fbf2f4", color: "var(--danger)", border: "1px solid #f9d2d8" };
                                    } else if (factor.includes("Cerrado")) {
                                      style = { background: "#f5f5f5", color: "#777777", textDecoration: "line-through" };
                                    }
                                    return (
                                      <span key={fIdx} className="badge" style={style}>
                                        {factor}
                                      </span>
                                    );
                                  })
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Recomendaciones Operativas */}
              <div className="admin-notice" style={{ marginTop: "2rem", border: "1px solid #dcdce6", background: "#f8f8fc", color: "#3c3c50" }}>
                <h3 style={{ margin: "0 0 0.5rem 0", color: "var(--ink-strong)" }}>💡 Recomendaciones de Gestión y Personal:</h3>
                <ul style={{ margin: 0, paddingLeft: "1.2rem", display: "grid", gap: "0.4rem" }}>
                  <li>
                    <strong>Días normales (Menos de 500 visitantes):</strong> Operación estándar. Se recomienda personal base en taquillas y salas.
                  </li>
                  <li>
                    <strong>Días de alta afluencia (500 a 800 visitantes):</strong> Se sugiere reforzar el personal de control de salas y habilitar una ventanilla de atención rápida para evitar aglomeraciones.
                  </li>
                  <li>
                    <strong>Días críticos / pico (Más de 800 visitantes):</strong> Alta concentración de visitantes (ej. Semana Santa). Se aconseja habilitar todo el personal de contingencia, coordinar flujos de entrada en intervalos estrictos y programar descansos escalonados para el equipo del museo.
                  </li>
                </ul>
              </div>
            </>
          )}
        </div>
      )}
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
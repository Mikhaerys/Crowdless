import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useBookingContext } from "../context/BookingContext";
import { bookingService } from "../services/bookingService";

function createVisitorsTemplate(count) {
  return Array.from({ length: count }, () => ({
    name: "",
    birth_date: "",
    id_number: "",
  }));
}

function VisitorInfoPage() {
  const navigate = useNavigate();
  const { state, setTickets } = useBookingContext();
  const booking = state.booking;

  const initialVisitors = useMemo(
    () => createVisitorsTemplate(booking?.total_tickets || 0),
    [booking?.total_tickets]
  );

  const [contactEmail, setContactEmail] = useState("");
  const [visitors, setVisitors] = useState(initialVisitors);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!booking) {
    return (
      <section className="card flow-section">
        <h1>No hay una reserva activa</h1>
        <p>Debes completar la reserva y el pago antes de registrar visitantes.</p>
        <Link to="/reserva" className="button button-primary">
          Ir a reserva
        </Link>
      </section>
    );
  }

  function updateVisitor(index, field, value) {
    setVisitors((previous) =>
      previous.map((visitor, currentIndex) =>
        currentIndex === index ? { ...visitor, [field]: value } : visitor
      )
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();

    // Validar email
    if (!contactEmail || !contactEmail.includes("@")) {
      setError("Ingresa un correo electrónico válido para recibir tus entradas.");
      return;
    }

    // Validar visitantes
    if (
      visitors.some(
        (visitor) => !visitor.name || !visitor.birth_date || !visitor.id_number
      )
    ) {
      setError("Completa todos los campos de cada visitante.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const tickets = await bookingService.registerVisitors(
        booking.booking_id,
        contactEmail,
        visitors
      );
      setTickets(tickets);
      navigate("/confirmacion");
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card flow-section">
      <h1>Información de visitantes</h1>
      <p className="subtext">Registra una persona por cada entrada comprada.</p>

      <form onSubmit={handleSubmit} className="visitor-form">

        {/* Email de contacto */}
        <article className="visitor-card">
          <h2>Correo de contacto</h2>
          <p className="subtext" style={{ margin: 0, fontSize: "0.9rem" }}>
            Aquí enviaremos todos los códigos QR de tu reserva.
          </p>
          <label className="field">
            <span>Correo electrónico</span>
            <input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="Ej: correo@ejemplo.com"
              required
            />
          </label>
        </article>

        {/* Datos de cada visitante */}
        {visitors.map((visitor, index) => (
          <article className="visitor-card" key={`visitor-${index}`}>
            <h2>Visitante {index + 1}</h2>
            <label className="field">
              <span>Nombre completo</span>
              <input
                type="text"
                value={visitor.name}
                onChange={(e) => updateVisitor(index, "name", e.target.value)}
                placeholder="Ej: Ana Pérez"
              />
            </label>
            <label className="field">
              <span>Fecha de nacimiento</span>
              <input
                type="date"
                value={visitor.birth_date}
                onChange={(e) =>
                  updateVisitor(index, "birth_date", e.target.value)
                }
              />
            </label>
            <label className="field">
              <span>Documento de identidad</span>
              <input
                type="text"
                value={visitor.id_number}
                onChange={(e) =>
                  updateVisitor(index, "id_number", e.target.value)
                }
                placeholder="Ej: 1020456789"
              />
            </label>
          </article>
        ))}

        {error ? <p className="error-box">{error}</p> : null}

        <button
          type="submit"
          className="button button-primary"
          disabled={saving}
        >
          {saving ? "Guardando y enviando entradas..." : "Finalizar reserva"}
        </button>
      </form>
    </section>
  );
}

export default VisitorInfoPage;

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useBookingContext } from "../context/BookingContext";
import { paymentService } from "../services/paymentService";

function PaymentPage() {
  const navigate = useNavigate();
  const { state, setPayment } = useBookingContext();
  const booking = state.booking;

  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState("approved");
  const [error, setError] = useState("");

  if (!booking) {
    return (
      <section className="card flow-section">
        <h1>No hay una reserva activa</h1>
        <p>Primero debes crear una reserva para poder simular el pago.</p>
        <Link to="/reserva" className="button button-primary">
          Ir a reserva
        </Link>
      </section>
    );
  }

  async function handlePayment(event) {
    event.preventDefault();
    setProcessing(true);
    setError("");
    try {
      const payment = await paymentService.verifyPayment(booking.booking_id, status);
      setPayment(payment);
      if (status === "approved") {
        navigate("/visitantes");
      } else {
        setError("El pago no fue aprobado. Puedes intentar de nuevo.");
      }
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setProcessing(false);
    }
  }

  return (
    <section className="card flow-section">
      <h1>Pago simulado</h1>
      <p className="subtext">Esta pantalla simula una pasarela de pago para continuar el flujo.</p>

      <div className="payment-summary">
        <p>
          Reserva: <strong>{booking.booking_id}</strong>
        </p>
        <p>
          Total: <strong>{booking.amount} {booking.currency}</strong>
        </p>
        <p>
          Entradas: <strong>{booking.total_tickets}</strong>
        </p>
      </div>

      <form onSubmit={handlePayment} className="ticket-form">
        <label className="field">
          <span>Resultado de la simulacion</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="approved">Aprobado</option>
            <option value="failed">Fallido</option>
            <option value="cancelled">Cancelado</option>
          </select>
        </label>

        {error ? <p className="error-box">{error}</p> : null}

        <button type="submit" className="button button-primary" disabled={processing}>
          {processing ? "Procesando..." : "Confirmar pago"}
        </button>
      </form>
    </section>
  );
}

export default PaymentPage;

import { Link } from "react-router-dom";

import { useBookingContext } from "../context/BookingContext";

function ConfirmationPage() {
  const { state, resetFlow } = useBookingContext();
  const { booking, payment, tickets } = state;

  if (!booking) {
    return (
      <section className="card flow-section">
        <h1>No hay datos para mostrar</h1>
        <p>Inicia una nueva reserva para ver esta pantalla.</p>
        <Link to="/" className="button button-primary">
          Ir al inicio
        </Link>
      </section>
    );
  }

  return (
    <section className="card flow-section confirmation">
      <p className="eyebrow">Reserva finalizada</p>
      <h1>Todo listo para tu visita</h1>
      <p>
        Tu reserva fue procesada correctamente. En una siguiente iteracion podras validar los
        tiquetes por QR directamente en el museo.
      </p>

      <div className="confirmation-grid">
        <article>
          <h2>Resumen</h2>
          <p>Reserva: {booking.booking_id}</p>
          <p>Fecha: {booking.visit_date}</p>
          <p>Total entradas: {booking.total_tickets}</p>
          <p>Monto: {booking.amount} {booking.currency}</p>
          <p>Pago: {payment?.status || booking.payment_status}</p>
        </article>
        <article>
          <h2>Tiquetes generados</h2>
          <p>{tickets.length} tiquetes creados</p>
          <ul className="ticket-list">
            {tickets.map((ticket) => (
              <li key={ticket.ticket_id}>
                <span>{ticket.visitor_name}</span>
                <small>{ticket.ticket_id}</small>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <div className="hero-actions">
        <Link to="/" className="button button-primary" onClick={resetFlow}>
          Hacer otra reserva
        </Link>
      </div>
    </section>
  );
}

export default ConfirmationPage;

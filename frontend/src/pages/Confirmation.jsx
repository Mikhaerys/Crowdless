import { Link } from "react-router-dom";
import { useBookingContext } from "../context/BookingContext";

function getTicketTypeLabel(ticketType) {
    return ticketType === "adult" ? "Adulto" : "Niño";
}

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
                Tu reserva fue procesada correctamente. A continuación encontrarás
                los códigos QR de cada visitante. Preséntalo en la entrada del museo.
            </p>

            {/* Resumen de la reserva */}
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
                                <span>
                                    {ticket.visitor_name} · {getTicketTypeLabel(ticket.ticket_type)}
                                </span>
                                <small>{ticket.ticket_id}</small>
                            </li>
                        ))}
                    </ul>
                </article>
            </div>

            {/* Códigos QR por visitante */}
            <div className="qr-section">
                <h2>Códigos QR de ingreso</h2>
                <p className="qr-hint">
                    Cada visitante debe presentar su código QR en la entrada del museo.
                </p>
                <div className="qr-grid">
                    {tickets.map((ticket) => (
                        <div key={ticket.ticket_id} className="qr-card">
                            <p className="qr-visitor-name">
                                {ticket.visitor_name} · {getTicketTypeLabel(ticket.ticket_type)}
                            </p>
                            <img
                                src={ticket.qr_code}
                                alt={`Código QR de ${ticket.visitor_name}`}
                                className="qr-image"
                            />
                            <small className="qr-ticket-id">ID: {ticket.ticket_id}</small>
                        </div>
                    ))}
                </div>
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

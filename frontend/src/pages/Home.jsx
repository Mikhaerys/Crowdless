import { Link } from "react-router-dom";

import { API_BASE_URL } from "../services/apiClient";

function HomePage() {
  return (
    <section className="hero card">
      <p className="eyebrow">Planifica tu visita al museo</p>
      <h1>Reserva en minutos sin filas ni sobrecupos.</h1>
      <p>
        Selecciona fecha, franja horaria, cantidad de entradas y completa el pago simulado.
        Al final podras registrar a cada visitante y generar tus tiquetes.
      </p>
      <div className="hero-actions">
        <Link to="/reserva" className="button button-primary">
          Comprar entradas
        </Link>
        <span className="api-hint">Backend: {API_BASE_URL}</span>
      </div>
    </section>
  );
}

export default HomePage;

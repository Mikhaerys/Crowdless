# Frontend Crowdless

Aplicacion web en React + Vite para el flujo de reserva de visitas al museo.

## Requisitos

- Node.js 18+
- Backend de FastAPI ejecutandose

## Configuracion

1. Copia `.env.example` como `.env`.
2. Ajusta la URL del backend en `VITE_API_BASE_URL`.

Ejemplo:

VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

## Desarrollo

npm install
npm run dev

## Build de produccion

npm run build
npm run preview

## Flujo implementado

1. Inicio: boton para iniciar compra.
2. Reserva: seleccion de fecha, franja, cantidad de entradas y moneda.
3. Pago: simulacion de pago (aprobado, fallido o cancelado).
4. Visitantes: registro de personas segun entradas compradas.
5. Confirmacion: resumen final y listado de tiquetes generados.

## Endpoints usados

- GET /slots?visit_date=YYYY-MM-DD
- POST /bookings
- GET /bookings/{booking_id}
- POST /payments/{booking_id}/verify
- POST /bookings/{booking_id}/visitors
- GET /bookings/{booking_id}/tickets

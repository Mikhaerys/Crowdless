import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { useBookingContext } from "../context/BookingContext";
import LoadingState from "../components/LoadingState";
import { bookingService } from "../services/bookingService";
import { paymentService } from "../services/paymentService";

const BOLD_LIBRARY_URL = "https://checkout.bold.co/library/boldPaymentButton.js";

function extractBookingIdFromOrderId(orderId) {
    if (!orderId) {
        return null;
    }
    const match = orderId.match(/^(.*)-\d{10,}$/);
    return match ? match[1] : null;
}

function formatPrice(amount, locale = 'es-ES') {
    return new Intl.NumberFormat(locale, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

function PaymentPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { state, setBooking, setPayment } = useBookingContext();
    const booking = state.booking;
    const buttonContainerRef = useRef(null);
    const hasVerifiedRef = useRef(false);

    const [loadingCheckout, setLoadingCheckout] = useState(false);
    const [verifying, setVerifying] = useState(false);
    const [simulating, setSimulating] = useState(false);
    const [simulatedStatus, setSimulatedStatus] = useState("approved");
    const [checkoutConfig, setCheckoutConfig] = useState(null);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    const boldOrderId = searchParams.get("bold-order-id");
    const boldTxStatus = searchParams.get("bold-tx-status");

    const paymentStatus = state.payment?.status || booking?.payment_status || "pending";
    const isApproved = paymentStatus === "approved";

    const paymentSummary = useMemo(() => {
        if (!booking) {
            return null;
        }
        return {
            bookingId: booking.booking_id,
            amount: booking.amount,
            currency: booking.currency,
            totalTickets: booking.total_tickets
        };
    }, [booking]);

    const prepareCheckout = useCallback(async (targetBookingId) => {
        if (!targetBookingId) {
            return;
        }
        setLoadingCheckout(true);
        setError("");
        setMessage("");
        setCheckoutConfig(null);
        try {
            const config = await paymentService.prepareBoldPayment(targetBookingId);
            setCheckoutConfig(config);
        } catch (apiError) {
            setError(apiError.message);
        } finally {
            setLoadingCheckout(false);
        }
    }, []);

    useEffect(() => {
        async function hydrateBookingFromRedirect() {
            if (booking || !boldOrderId) {
                return;
            }
            const recoveredBookingId = extractBookingIdFromOrderId(boldOrderId);
            if (!recoveredBookingId) {
                setError("No fue posible identificar la reserva asociada al pago.");
                return;
            }

            try {
                const recoveredBooking = await bookingService.getBooking(recoveredBookingId);
                setBooking(recoveredBooking);
            } catch (apiError) {
                setError(apiError.message);
            }
        }

        hydrateBookingFromRedirect();
    }, [booking, boldOrderId, setBooking]);

    useEffect(() => {
        async function verifyPaymentResult() {
            if (!booking || !boldOrderId || !boldTxStatus || hasVerifiedRef.current) {
                return;
            }
            hasVerifiedRef.current = true;
            setVerifying(true);
            setError("");
            setMessage("");
            try {
                const payment = await paymentService.verifyBoldPayment({
                    bookingId: booking.booking_id,
                    boldOrderId,
                    boldTxStatus
                });
                setPayment(payment);
                const refreshedBooking = await bookingService.getBooking(booking.booking_id);
                setBooking(refreshedBooking);

                if (payment.status === "approved") {
                    setMessage("Pago aprobado. Ya puedes continuar con el registro de visitantes.");
                } else {
                    setError("El pago no fue aprobado. Puedes intentarlo nuevamente.");
                    await prepareCheckout(booking.booking_id);
                }
            } catch (apiError) {
                setError(apiError.message);
            } finally {
                setVerifying(false);
            }
        }

        verifyPaymentResult();
    }, [booking, boldOrderId, boldTxStatus, prepareCheckout, setBooking, setPayment]);

    useEffect(() => {
        if (!booking || isApproved || (boldOrderId && boldTxStatus)) {
            return;
        }
        prepareCheckout(booking.booking_id);
    }, [booking, isApproved, boldOrderId, boldTxStatus, prepareCheckout]);

    useEffect(() => {
        if (!checkoutConfig || isApproved || !buttonContainerRef.current) {
            return;
        }

        buttonContainerRef.current.innerHTML = "";
        const checkoutScript = document.createElement("script");
        checkoutScript.src = BOLD_LIBRARY_URL;
        checkoutScript.async = true;
        checkoutScript.setAttribute("data-bold-button", "dark-L");
        checkoutScript.setAttribute("data-api-key", checkoutConfig.api_key);
        checkoutScript.setAttribute("data-amount", String(checkoutConfig.amount));
        checkoutScript.setAttribute("data-currency", checkoutConfig.currency);
        checkoutScript.setAttribute("data-order-id", checkoutConfig.order_id);
        checkoutScript.setAttribute("data-integrity-signature", checkoutConfig.integrity_signature);
        checkoutScript.setAttribute("data-description", checkoutConfig.description);
        checkoutScript.setAttribute("data-redirection-url", checkoutConfig.redirection_url);
        checkoutScript.setAttribute("data-origin-url", checkoutConfig.redirection_url);
        checkoutScript.setAttribute("data-render-mode", "embedded");
        checkoutScript.onerror = () => {
            setError("No fue posible cargar el checkout embebido de Bold.");
        };

        if (buttonContainerRef.current) {
            buttonContainerRef.current.appendChild(checkoutScript);
        }
    }, [checkoutConfig, isApproved]);

    async function handleSimulatedPayment() {
        if (!booking) {
            return;
        }
        setSimulating(true);
        setError("");
        setMessage("");
        try {
            const payment = await paymentService.verifyPayment(booking.booking_id, simulatedStatus);
            setPayment(payment);
            if (payment.status === "approved") {
                setMessage("Pago simulado aprobado. Ya puedes continuar con el registro de visitantes.");
            } else {
                setError("Pago simulado no aprobado. Puedes probar con otro estado.");
            }
        } catch (apiError) {
            setError(apiError.message);
        } finally {
            setSimulating(false);
        }
    }

    if (!booking) {
        return (
            <section className="card flow-section">
                <h1>No hay una reserva activa</h1>
                <p>Primero debes crear una reserva para continuar con el pago.</p>
                <Link to="/reserva" className="button button-primary">
                    Ir a reserva
                </Link>
            </section>
        );
    }

    return (
        <section className="card flow-section">
            <h1>Pago con Bold</h1>
            <p className="subtext">Finaliza tu compra con el boton de pago embebido de Bold.</p>

            <div className="payment-summary">
                <p>
                    Reserva: <strong>{paymentSummary.bookingId}</strong>
                </p>
                <p>
                    Total: <strong>{formatPrice(paymentSummary.amount)} {paymentSummary.currency}</strong>
                </p>
                <p>
                    Entradas: <strong>{paymentSummary.totalTickets}</strong>
                </p>
                <p>
                    Estado actual: <strong>{paymentStatus}</strong>
                </p>
            </div>

            {verifying ? <LoadingState label="Verificando estado de la transaccion..." /> : null}
            {message ? <p className="success-box">{message}</p> : null}
            {error ? <p className="error-box">{error}</p> : null}

            {isApproved ? (
                <button type="button" className="button button-primary" onClick={() => navigate("/visitantes")}>
                    Continuar con visitantes
                </button>
            ) : (
                <div className="ticket-form">
                    {loadingCheckout ? <LoadingState label="Preparando checkout de Bold..." /> : null}
                    <div ref={buttonContainerRef} />
                    {!loadingCheckout && !checkoutConfig ? (
                        <button
                            type="button"
                            className="button button-primary"
                            onClick={() => prepareCheckout(booking.booking_id)}
                        >
                            Reintentar pago
                        </button>
                    ) : null}

                    <div className="payment-summary">
                        <p>
                            <strong>Modo pruebas:</strong> si Bold falla o no esta disponible, puedes continuar con pago simulado.
                        </p>
                        <label className="field">
                            <span>Resultado simulado</span>
                            <select value={simulatedStatus} onChange={(event) => setSimulatedStatus(event.target.value)}>
                                <option value="approved">Aprobado</option>
                                <option value="failed">Fallido</option>
                                <option value="cancelled">Cancelado</option>
                            </select>
                        </label>

                        <button
                            type="button"
                            style={{ marginTop: '20px' }}
                            className="button button-primary"
                            onClick={handleSimulatedPayment}
                            disabled={simulating}
                        >
                            {simulating ? "Procesando simulacion..." : "Usar pago simulado"}
                        </button>
                    </div>
                </div>
            )}
        </section>
    );
}

export default PaymentPage;

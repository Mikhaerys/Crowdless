import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import LoadingState from "../components/LoadingState";
import SlotGrid from "../components/SlotGrid";
import { useBookingContext } from "../context/BookingContext";
import { bookingService } from "../services/bookingService";
import { mergeSlotsWithDefaults, toLocalDateInputValue } from "../utils/time";

function BookingPage() {
    const navigate = useNavigate();
    const { state, setVisitDate, setSelectedSlot, setBooking } = useBookingContext();

    const [slots, setSlots] = useState([]);
    const [adults, setAdults] = useState(1);
    const [children, setChildren] = useState(0);
    const [currency, setCurrency] = useState("USD");
    const [loadingSlots, setLoadingSlots] = useState(false);
    const [savingBooking, setSavingBooking] = useState(false);
    const [error, setError] = useState("");

    const visitDate = state.visitDate || toLocalDateInputValue();
    const selectedSlot = state.selectedSlot;
    const totalTickets = adults + children;

    useEffect(() => {
        if (!state.visitDate) {
            setVisitDate(visitDate);
        }
    }, [state.visitDate, setVisitDate, visitDate]);

    useEffect(() => {
        async function loadSlots() {
            setLoadingSlots(true);
            setError("");
            try {
                const data = await bookingService.listSlotsByDate(visitDate);
                setSlots(mergeSlotsWithDefaults(visitDate, data));
            } catch (apiError) {
                setError(apiError.message);
                setSlots([]);
            } finally {
                setLoadingSlots(false);
            }
        }

        if (visitDate) {
            loadSlots();
        }
    }, [visitDate]);

    const maxSelectableTickets = useMemo(() => {
        if (!selectedSlot) {
            return 0;
        }
        return selectedSlot.available;
    }, [selectedSlot]);

    async function handleCreateBooking(event) {
        event.preventDefault();
        if (!selectedSlot) {
            setError("Selecciona una franja horaria.");
            return;
        }
        if (totalTickets <= 0) {
            setError("Debes seleccionar al menos una entrada.");
            return;
        }
        if (totalTickets > selectedSlot.available) {
            setError("La cantidad de entradas supera los cupos disponibles.");
            return;
        }

        setSavingBooking(true);
        setError("");
        try {
            let slotId = selectedSlot.slot_id;

            if (selectedSlot.is_virtual) {
                try {
                    const createdSlot = await bookingService.createSlot({
                        visitDate,
                        startTime: selectedSlot.start_time,
                        endTime: selectedSlot.end_time,
                        capacity: 15
                    });
                    slotId = createdSlot.slot_id;
                } catch (slotError) {
                    const conflictError = slotError.message.toLowerCase().includes("already exists");
                    if (!conflictError) {
                        throw slotError;
                    }
                }
            }

            const booking = await bookingService.createBooking({
                slotId,
                adults,
                children,
                currency
            });
            setBooking(booking);
            navigate("/pago");
        } catch (apiError) {
            setError(apiError.message);
        } finally {
            setSavingBooking(false);
        }
    }

    function onDateChange(nextDate) {
        setVisitDate(nextDate);
        setSelectedSlot(null);
        setSlots([]);
    }

    return (
        <section className="card flow-section">
            <h1>Reserva de entradas</h1>
            <p className="subtext">Escoge una fecha y selecciona una franja con cupos disponibles.</p>

            <label className="field">
                <span>Fecha de visita</span>
                <input type="date" value={visitDate} min={toLocalDateInputValue()} onChange={(e) => onDateChange(e.target.value)} />
            </label>

            {loadingSlots ? (
                <LoadingState label="Consultando franjas horarias..." />
            ) : (
                <SlotGrid
                    slots={slots}
                    selectedSlotId={selectedSlot?.slot_id || null}
                    onSelect={(slot) => {
                        setSelectedSlot(slot);
                        setError("");
                    }}
                />
            )}

            <form onSubmit={handleCreateBooking} className="ticket-form">
                <h2>Detalle de entradas</h2>
                <div className="ticket-grid">
                    <label className="field">
                        <span>Adultos</span>
                        <input
                            type="number"
                            min="0"
                            max={maxSelectableTickets || 15}
                            value={adults}
                            onChange={(e) => setAdults(Number(e.target.value))}
                        />
                    </label>
                    <label className="field">
                        <span>Ninos</span>
                        <input
                            type="number"
                            min="0"
                            max={maxSelectableTickets || 15}
                            value={children}
                            onChange={(e) => setChildren(Number(e.target.value))}
                        />
                    </label>
                    <label className="field">
                        <span>Moneda</span>
                        <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
                            <option value="USD">USD</option>
                            <option value="COP">COP</option>
                        </select>
                    </label>
                </div>

                <p className="summary-line">
                    Entradas seleccionadas: <strong>{totalTickets}</strong>
                </p>

                {error ? <p className="error-box">{error}</p> : null}

                <button type="submit" className="button button-primary" disabled={savingBooking || !selectedSlot}>
                    {savingBooking ? "Reservando..." : "Continuar a pago"}
                </button>
            </form>
        </section>
    );
}

export default BookingPage;

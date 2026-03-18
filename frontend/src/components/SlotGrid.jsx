import { formatTimeRange, isMorningSlot } from "../utils/time";

function SlotCard({ slot, selected, onSelect }) {
    const full = slot.available <= 0;
    return (
        <button
            type="button"
            className={`slot-card ${selected ? "selected" : ""}`}
            disabled={full}
            onClick={() => onSelect(slot)}
        >
            <p className="slot-time">{formatTimeRange(slot.start_time, slot.end_time)}</p>
            <p className="slot-availability">{full ? "Sin cupos" : `${slot.available} cupos disponibles`}</p>
        </button>
    );
}

function SlotColumn({ title, slots, selectedSlotId, onSelect }) {
    return (
        <section className="slot-column">
            <h3>{title}</h3>
            <div className="slot-list">
                {slots.length === 0 ? (
                    <p className="empty-state">No hay franjas disponibles.</p>
                ) : (
                    slots.map((slot) => (
                        <SlotCard
                            key={slot.slot_id}
                            slot={slot}
                            selected={selectedSlotId === slot.slot_id}
                            onSelect={onSelect}
                        />
                    ))
                )}
            </div>
        </section>
    );
}

function SlotGrid({ slots, selectedSlotId, onSelect }) {
    const morning = slots.filter((slot) => isMorningSlot(slot.start_time));
    const afternoon = slots.filter((slot) => !isMorningSlot(slot.start_time));

    return (
        <div className="slot-grid">
            <SlotColumn title="Mañana" slots={morning} selectedSlotId={selectedSlotId} onSelect={onSelect} />
            <SlotColumn title="Tarde" slots={afternoon} selectedSlotId={selectedSlotId} onSelect={onSelect} />
        </div>
    );
}

export default SlotGrid;

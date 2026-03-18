export function formatTimeRange(startTime, endTime) {
    return `${startTime.slice(0, 5)} - ${endTime.slice(0, 5)}`;
}

export function toLocalDateInputValue(date = new Date()) {
    const timezoneOffset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 10);
}

export function isMorningSlot(startTime) {
    const hour = Number(startTime.split(":")[0]);
    return hour < 13;
}

export function buildSlotId(visitDate, startTime, endTime) {
    const startCompact = startTime.replace(":", "");
    const endCompact = endTime.replace(":", "");
    return `${visitDate}_${startCompact}_${endCompact}`;
}

function minutesToTime(minutes) {
    const hours = String(Math.floor(minutes / 60)).padStart(2, "0");
    const mins = String(minutes % 60).padStart(2, "0");
    return `${hours}:${mins}`;
}

export function generateMuseumDefaultSlots(visitDate, capacity = 15) {
    const startOfDay = 9 * 60;
    const endOfDay = 17 * 60;
    const duration = 30;
    const result = [];

    for (let start = startOfDay; start < endOfDay; start += duration) {
        const startTime = minutesToTime(start);
        const endTime = minutesToTime(start + duration);

        result.push({
            slot_id: buildSlotId(visitDate, startTime, endTime),
            visit_date: visitDate,
            start_time: startTime,
            end_time: endTime,
            capacity,
            booked: 0,
            available: capacity,
            is_virtual: true
        });
    }

    return result;
}

export function mergeSlotsWithDefaults(visitDate, savedSlots, defaultCapacity = 15) {
    const defaults = generateMuseumDefaultSlots(visitDate, defaultCapacity);
    const savedById = new Map(
        savedSlots.map((slot) => [slot.slot_id, { ...slot, is_virtual: false }])
    );

    return defaults.map((slot) => savedById.get(slot.slot_id) || slot);
}

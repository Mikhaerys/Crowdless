import { apiClient } from "./apiClient";

export const bookingService = {
    listSlotsByDate: (visitDate) =>
        apiClient.get(`/slots?visit_date=${encodeURIComponent(visitDate)}`),

    createSlot: ({ visitDate, startTime, endTime, capacity = 15 }) =>
        apiClient.post("/slots", {
            visit_date: visitDate,
            start_time: startTime,
            end_time: endTime,
            capacity
        }),

    createBooking: ({ slotId, adults, children, currency = "USD" }) =>
        apiClient.post("/bookings", {
            slot_id: slotId,
            adults,
            children,
            currency
        }),

    getBooking: (bookingId) => apiClient.get(`/bookings/${bookingId}`),

    // contactEmail agregado para envío de QRs por email
    registerVisitors: (bookingId, contactEmail, visitors) =>
        apiClient.post(`/bookings/${bookingId}/visitors`, {
            contact_email: contactEmail,
            visitors,
        }),

    getTicketsByBooking: (bookingId) => apiClient.get(`/bookings/${bookingId}/tickets`),
};

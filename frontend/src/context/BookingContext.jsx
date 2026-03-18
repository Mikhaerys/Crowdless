import { createContext, useContext, useMemo, useState } from "react";

const BookingContext = createContext(null);

const initialState = {
  visitDate: "",
  selectedSlot: null,
  booking: null,
  payment: null,
  tickets: []
};

export function BookingProvider({ children }) {
  const [state, setState] = useState(initialState);

  const value = useMemo(
    () => ({
      state,
      setVisitDate: (visitDate) =>
        setState((previous) => ({
          ...previous,
          visitDate,
          selectedSlot: null,
          booking: null,
          payment: null,
          tickets: []
        })),
      setSelectedSlot: (selectedSlot) =>
        setState((previous) => ({ ...previous, selectedSlot })),
      setBooking: (booking) =>
        setState((previous) => ({ ...previous, booking })),
      setPayment: (payment) =>
        setState((previous) => ({ ...previous, payment })),
      setTickets: (tickets) =>
        setState((previous) => ({ ...previous, tickets })),
      resetFlow: () => setState(initialState)
    }),
    [state]
  );

  return <BookingContext.Provider value={value}>{children}</BookingContext.Provider>;
}

export function useBookingContext() {
  const context = useContext(BookingContext);
  if (!context) {
    throw new Error("useBookingContext debe usarse dentro de BookingProvider");
  }
  return context;
}

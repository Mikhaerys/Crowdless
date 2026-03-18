import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import BookingPage from "./pages/Booking";
import ConfirmationPage from "./pages/Confirmation";
import HomePage from "./pages/Home";
import PaymentPage from "./pages/Payment";
import VisitorInfoPage from "./pages/VisitorInfo";

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/reserva" element={<BookingPage />} />
        <Route path="/pago" element={<PaymentPage />} />
        <Route path="/visitantes" element={<VisitorInfoPage />} />
        <Route path="/confirmacion" element={<ConfirmationPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

export default App;

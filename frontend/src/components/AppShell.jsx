import { Link, useLocation } from "react-router-dom";

const steps = [
    { path: "/", label: "Inicio" },
    { path: "/reserva", label: "Reserva" },
    { path: "/pago", label: "Pago" },
    { path: "/visitantes", label: "Visitantes" },
    { path: "/confirmacion", label: "Confirmacion" }
];

function AppShell({ children }) {
    const location = useLocation();

    return (
        <div className="app-bg">
            <header className="topbar">
                <Link to="/" className="brand">
                    <span className="brand-dot" />
                    Crowdless
                </Link>
                <nav className="step-nav" aria-label="Pasos del proceso">
                    {steps.map((step) => {
                        const active = location.pathname === step.path;
                        return (
                            <Link key={step.path} to={step.path} className={`step-pill ${active ? "is-active" : ""}`}>
                                {step.label}
                            </Link>
                        );
                    })}
                </nav>
            </header>
            <main className="page-wrapper">{children}</main>
        </div>
    );
}

export default AppShell;

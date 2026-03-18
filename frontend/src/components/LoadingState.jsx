function LoadingState({ label = "Cargando..." }) {
  return (
    <div className="loading-row" role="status" aria-live="polite">
      <span className="loader" />
      <span>{label}</span>
    </div>
  );
}

export default LoadingState;

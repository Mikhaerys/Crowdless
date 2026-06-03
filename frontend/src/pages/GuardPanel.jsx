import { useState, useEffect, useRef } from "react";
import { Html5QrcodeScanner } from "html5-qrcode";
import { apiClient, API_BASE_URL } from "../services/apiClient";

export default function GuardPanel() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return localStorage.getItem("guard_logged_in") === "true";
  });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");

  // Verification state
  // phases: "qr", "identity", "success"
  const [phase, setPhase] = useState("qr");
  const [ticket, setTicket] = useState(null);
  const [qrError, setQrError] = useState("");
  const [qrLoading, setQrLoading] = useState(false);

  // Identity verification state
  const [selectedFile, setSelectedFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [idLoading, setIdLoading] = useState(false);
  const [idResult, setIdResult] = useState(null);
  const [scanAttempt, setScanAttempt] = useState(0);

  const [isCapturingId, setIsCapturingId] = useState(false);
  const [idStream, setIdStream] = useState(null);

  const fileInputRef = useRef(null);
  const videoRef = useRef(null);

  // Login handler
  async function handleLogin(e) {
    e.preventDefault();
    setLoginError("");
    try {
      const response = await apiClient.post("/validation/guard/login", {
        username,
        password,
      });
      if (response.success) {
        setIsLoggedIn(true);
        localStorage.setItem("guard_logged_in", "true");
      }
    } catch (err) {
      setLoginError(err.message || "Credenciales incorrectas");
    }
  }

  function handleLogout() {
    setIsLoggedIn(false);
    localStorage.removeItem("guard_logged_in");
    resetVerification();
  }

  // Phase Reset
  function resetVerification() {
    setPhase("qr");
    setTicket(null);
    setQrError("");
    setQrLoading(false);
    setSelectedFile(null);
    setImagePreview(null);
    setIdLoading(false);
    setIdResult(null);
    setScanAttempt((prev) => prev + 1);

    // Stop ID camera if active
    if (idStream) {
      idStream.getTracks().forEach((track) => track.stop());
      setIdStream(null);
    }
    setIsCapturingId(false);
  }

  // ID Camera functions
  async function startIdCamera() {
    setIsCapturingId(true);
    setSelectedFile(null);
    setImagePreview(null);
    setIdResult(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      setIdStream(stream);
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      }, 100);
    } catch (err) {
      console.error("Error accessing camera for ID capture", err);
      setIsCapturingId(false);
      alert("No se pudo acceder a la cámara. Por favor use la opción de subir archivo.");
    }
  }

  function stopIdCamera() {
    if (idStream) {
      idStream.getTracks().forEach((track) => track.stop());
      setIdStream(null);
    }
    setIsCapturingId(false);
  }

  function captureIdPhoto() {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg");
      setImagePreview(dataUrl);

      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], "cedula.jpg", { type: "image/jpeg" });
          setSelectedFile(file);
        }
      }, "image/jpeg", 0.9);
    }

    stopIdCamera();
  }

  // Cleanup ID camera stream on unmount
  useEffect(() => {
    return () => {
      if (idStream) {
        idStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [idStream]);

  // QR Code Success handler
  async function handleQrSuccess(decodedText) {
    if (qrLoading) return;
    setQrLoading(true);
    setQrError("");

    try {
      const response = await apiClient.post("/validation/guard/verify-qr", {
        qr_payload: decodedText,
      });
      setTicket(response);
      setPhase("identity");
    } catch (err) {
      setQrError(err.message || "Error al validar el código QR");
    } finally {
      setQrLoading(false);
    }
  }

  // Effect to manage QR Scanner
  useEffect(() => {
    if (!isLoggedIn || phase !== "qr") return;

    // Use a delay to ensure the DOM element #reader is mounted
    const timer = setTimeout(() => {
      const scanner = new Html5QrcodeScanner(
        "reader",
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          rememberLastUsedCamera: true,
          aspectRatio: 1.0,
        },
        /* verbose= */ false
      );

      scanner.render(
        (decodedText) => {
          scanner.clear()
            .then(() => handleQrSuccess(decodedText))
            .catch((err) => console.error("Error clearing scanner after success", err));
        },
        (error) => {
          // Silent scan failures
        }
      );

      return () => {
        scanner.clear().catch((err) => console.error("Error clearing scanner on cleanup", err));
      };
    }, 100);

    return () => clearTimeout(timer);
  }, [isLoggedIn, phase, scanAttempt]);

  // Photo change handler
  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  }

  // Identify / Upload photo
  async function handleVerifyIdentity() {
    if (!selectedFile || !ticket) return;
    setIdLoading(true);
    setIdResult(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch(
        `${API_BASE_URL}/validation/guard/verify-identity?ticket_id=${ticket.ticket_id}`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Error en la verificación de identidad");
      }

      setIdResult(data);
      if (data.valid) {
        setPhase("success");
      }
    } catch (err) {
      setIdResult({
        valid: false,
        detail: err.message || "Error al procesar la imagen de la cédula.",
      });
    } finally {
      setIdLoading(false);
    }
  }

  if (!isLoggedIn) {
    return (
      <section className="card flow-section guard-panel">
        <p className="eyebrow">Control de Accesos</p>
        <h1>Ingreso Vigilantes</h1>
        <p className="subtext">
          Inicia sesión para comenzar la validación de tiquetes e identidad.
        </p>

        {loginError && <p className="error-box">{loginError}</p>}

        <form onSubmit={handleLogin} className="flow-section">
          <div className="field">
            <label htmlFor="guard-user">Usuario de Seguridad</label>
            <input
              id="guard-user"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Ej: guardia"
              required
              autoComplete="username"
            />
          </div>

          <div className="field">
            <label htmlFor="guard-pass">Contraseña</label>
            <input
              id="guard-pass"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
            />
          </div>

          <div className="hero-actions">
            <button type="submit" className="button button-primary" style={{ width: "100%" }}>
              Iniciar Sesión
            </button>
          </div>
        </form>
      </section>
    );
  }

  return (
    <section className="card flow-section guard-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p className="eyebrow" style={{ margin: 0 }}>Vigilancia y Control</p>
          <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Verificación de Entrada</h1>
        </div>
        <button className="button button-secondary" onClick={handleLogout} style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}>
          Salir 🚪
        </button>
      </div>

      {/* Paso/Fase indicator */}
      <div className="guard-step-indicator">
        <div className={`guard-step ${phase === "qr" ? "active" : phase !== "qr" ? "completed" : ""}`}>
          1. Escanear QR
        </div>
        <div className={`guard-step ${phase === "identity" ? "active" : phase === "success" ? "completed" : ""}`}>
          2. Cédula y Roboflow
        </div>
      </div>

      {/* PHASE 1: QR CODE SCANNING */}
      {phase === "qr" && (
        <div className="flow-section">
          <p className="subtext" style={{ textAlign: "center" }}>
            Enfoque el código QR del visitante con la cámara del celular.
          </p>

          {qrError && (
            <div className="flow-section" style={{ marginBottom: "1rem" }}>
              <div className="error-box">
                <strong>Error de tiquete:</strong> {qrError}
              </div>
              <button 
                className="button button-secondary"
                onClick={resetVerification}
                style={{ width: "100%" }}
              >
                🔄 Volver a Empezar / Intentar de Nuevo
              </button>
            </div>
          )}

          {qrLoading ? (
            <div className="loading-row" style={{ justifyContent: "center", padding: "2rem" }}>
              <span className="loader"></span>
              <span>Validando código QR con el servidor...</span>
            </div>
          ) : (
            <div className="scanner-container">
              <div id="reader"></div>
            </div>
          )}

          <div className="admin-notice">
            <strong>Reglas de validación horaria:</strong> El sistema acepta tiquetes cuya franja sea la hora actual, o la franja que comienza inmediatamente después (por ejemplo, si son las 3:10, se pueden registrar entradas para la franja de las 3:15).
          </div>
        </div>
      )}

      {/* PHASE 2: ID CARD PHOTO CAPTURE & MATCHING */}
      {phase === "identity" && ticket && (
        <div className="flow-section">
          <h2>Datos Registrados en el Tiquete</h2>
          
          <div className="visitor-info-card">
            <div className="visitor-info-row">
              <span className="visitor-info-label">Visitante:</span>
              <span className="visitor-info-value">{ticket.visitor_name}</span>
            </div>
            <div className="visitor-info-row">
              <span className="visitor-info-label">Cédula:</span>
              <span className="visitor-info-value">{ticket.id_number}</span>
            </div>
            <div className="visitor-info-row">
              <span className="visitor-info-label">Nacimiento:</span>
              <span className="visitor-info-value">{ticket.birth_date}</span>
            </div>
            <div className="visitor-info-row">
              <span className="visitor-info-label">Tipo:</span>
              <span className="visitor-info-value">
                {ticket.ticket_type === "adult" ? "🧑 Adulto" : "👶 Niño"}
              </span>
            </div>
            <div className="visitor-info-row">
              <span className="visitor-info-label">Franja Horaria:</span>
              <span className="visitor-info-value" style={{ color: "var(--ok)", fontWeight: 700 }}>
                ⏰ {ticket.slot_start_time} - {ticket.slot_end_time}
              </span>
            </div>
          </div>

          <h3>Escanear Cédula del Visitante</h3>
          <p className="subtext">
            Tome una foto clara del documento de identidad físico (Cédula de Ciudadanía) para realizar la comparación de datos con Roboflow.
          </p>

          {/* Error de verificación */}
          {idResult && !idResult.valid && (
            <div className="flow-section" style={{ marginBottom: "1rem" }}>
              <div className="error-box" style={{ display: "grid", gap: "0.5rem" }}>
                <strong>Error de Validación:</strong>
                <span>{idResult.detail}</span>
                
                {idResult.identity_match && (
                  <div className="ocr-match-list">
                    <div className={`ocr-match-item ${idResult.identity_match.name ? "matched" : "failed"}`}>
                      {idResult.identity_match.name ? "✓ Nombre coincide" : "✗ Nombre no coincide"}
                    </div>
                    <div className={`ocr-match-item ${idResult.identity_match.id_number ? "matched" : "failed"}`}>
                      {idResult.identity_match.id_number ? "✓ Cédula coincide" : "✗ Cédula no coincide"}
                    </div>
                    <div className={`ocr-match-item ${idResult.identity_match.birth_date ? "matched" : "failed"}`}>
                      {idResult.identity_match.birth_date ? "✓ Fecha de nacimiento coincide" : "✗ Fecha de nacimiento no coincide"}
                    </div>
                  </div>
                )}
              </div>
              <div style={{ display: "flex", gap: "1rem" }}>
                <button
                  className="button button-secondary"
                  style={{ flex: 1 }}
                  onClick={() => {
                    setSelectedFile(null);
                    setImagePreview(null);
                    setIdResult(null);
                  }}
                >
                  📸 Tomar Nueva Foto
                </button>
                <button
                  className="button button-secondary"
                  style={{ flex: 1, border: "1px dashed var(--danger)", color: "var(--danger)" }}
                  onClick={resetVerification}
                >
                  🔄 Volver a Empezar (Inicio)
                </button>
              </div>
            </div>
          )}

          {idLoading ? (
            <div className="loading-row" style={{ justifyContent: "center", padding: "2rem", flexDirection: "column", gap: "1rem" }}>
              <span className="loader" style={{ width: "2rem", height: "2rem" }}></span>
              <span style={{ fontWeight: 700 }}>Procesando imagen con Roboflow...</span>
              <small style={{ color: "var(--ink-soft)" }}>
                Validando que sea un documento auténtico y comparando los datos OCR...
              </small>
            </div>
          ) : isCapturingId ? (
            <div className="flow-section">
              <div className="id-camera-container">
                <video ref={videoRef} autoPlay playsInline className="id-camera-video"></video>
                <div className="id-camera-guide"></div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <button className="button button-secondary" onClick={stopIdCamera}>
                  ◀ Cancelar Cámara
                </button>
                <button 
                  className="button button-primary" 
                  onClick={captureIdPhoto}
                  style={{ background: "var(--ok)" }}
                >
                  Capturar Foto 📸
                </button>
              </div>
            </div>
          ) : (
            <>
              {imagePreview ? (
                <div 
                  className="camera-preview-box"
                  style={{ borderStyle: "solid", borderColor: "var(--ok)", background: "#f1fcf7" }}
                >
                  <p style={{ fontWeight: 700, margin: 0, color: "var(--ok)" }}>✓ Foto del Documento Cargada</p>
                  <img 
                    src={imagePreview} 
                    alt="Cédula cargada" 
                    className="preview-thumbnail" 
                  />
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "0.5rem" }}>
                    <button 
                      className="button button-secondary"
                      style={{ padding: "0.4rem 0.6rem", fontSize: "0.8rem" }}
                      onClick={startIdCamera}
                    >
                      📸 Tomar Otra
                    </button>
                    <button 
                      className="button button-secondary"
                      style={{ padding: "0.4rem 0.6rem", fontSize: "0.8rem" }}
                      onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    >
                      📁 Subir Otra
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flow-section" style={{ marginBottom: "1.25rem" }}>
                  <div className="camera-preview-box" style={{ marginBottom: "0.75rem" }}>
                    <span style={{ fontSize: "2.5rem" }}>🪪</span>
                    <p style={{ fontWeight: 700, margin: "0.5rem 0 0" }}>Cédula del Visitante</p>
                    <p style={{ fontSize: "0.85rem", color: "var(--ink-soft)", margin: 0 }}>
                      Seleccione una opción para escanear el documento
                    </p>
                  </div>
                  
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                    <button 
                      className="button button-primary" 
                      onClick={startIdCamera}
                      style={{ background: "var(--ok)" }}
                    >
                      Tomar Foto 📸
                    </button>
                    <button 
                      className="button button-secondary" 
                      onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    >
                      Subir Archivo 📁
                    </button>
                  </div>
                </div>
              )}

              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", borderTop: "1px solid var(--line)", paddingTop: "1.25rem", marginTop: "0.5rem" }}>
                <button 
                  className="button button-secondary"
                  onClick={resetVerification}
                >
                  ◀ Volver a Empezar
                </button>
                <button
                  className="button button-primary"
                  onClick={handleVerifyIdentity}
                  disabled={!selectedFile || idLoading}
                >
                  Validar Identidad 🔍
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* PHASE 3: SUCCESS */}
      {phase === "success" && ticket && (
        <div className="flow-section success-hero">
          <div className="success-icon-circle">✓</div>
          <h2 style={{ color: "var(--ok)", fontSize: "1.8rem", margin: "0 0 0.5rem" }}>
            ENTRADA AUTORIZADA
          </h2>
          <p className="subtext" style={{ fontSize: "1.1rem", marginBottom: "2rem" }}>
            El visitante <strong>{ticket.visitor_name}</strong> ha sido verificado con éxito y el tiquete se ha registrado en el sistema.
          </p>

          <div className="visitor-info-card" style={{ textAlign: "left", margin: "0 auto 2rem", maxWidth: "400px" }}>
            <div className="visitor-info-row">
              <span className="visitor-info-label">Visitante:</span>
              <span className="visitor-info-value">{ticket.visitor_name}</span>
            </div>
            <div className="visitor-info-row">
              <span className="visitor-info-label">Cédula:</span>
              <span className="visitor-info-value">{ticket.id_number}</span>
            </div>
            <div className="visitor-info-row">
              <span className="visitor-info-label">Tiquete ID:</span>
              <span className="visitor-info-value" style={{ fontSize: "0.85rem", color: "var(--ink-soft)" }}>
                {ticket.ticket_id}
              </span>
            </div>
          </div>

          <button 
            className="button button-primary"
            onClick={resetVerification}
            style={{ width: "100%", padding: "1rem" }}
          >
            Siguiente Visitante 🔄
          </button>
        </div>
      )}
    </section>
  );
}

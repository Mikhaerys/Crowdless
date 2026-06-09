import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, status, Depends
from app.services.runtime import ticket_service

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_or_initialize_credentials(role: str, default_user: str, default_pass: str) -> dict:
    """Gets or initializes the credentials document in Firestore for a given role."""
    doc_ref = ticket_service.firestore.client.collection("credentials").document(role)
    doc_snap = doc_ref.get()
    if not doc_snap.exists:
        data = {
            "username": default_user,
            "password_hash": hash_password(default_pass),
            "updated_at": ticket_service.firestore.now()
        }
        doc_ref.set(data)
        return data
    return doc_snap.to_dict()

def verify_credentials(role: str, username: str, password: str) -> bool:
    """Verifies user credentials against the stored credentials in Firestore (or defaults)."""
    if role == "admin":
        creds = get_or_initialize_credentials("admin", "museo", "unicauca2026")
    elif role == "guard":
        creds = get_or_initialize_credentials("guard", "guardia", "seguridad2026")
    else:
        return False
    
    return creds.get("username") == username and creds.get("password_hash") == hash_password(password)

def update_password(role: str, new_password: str) -> None:
    """Updates the password in Firestore for the specified role."""
    doc_ref = ticket_service.firestore.client.collection("credentials").document(role)
    doc_ref.update({
        "password_hash": hash_password(new_password),
        "updated_at": ticket_service.firestore.now()
    })

def create_session(role: str, username: str) -> str:
    """Creates a new session token in Firestore, expiring in 7 days."""
    token = secrets.token_hex(24)
    now = ticket_service.firestore.now()
    session_data = {
        "role": role,
        "username": username,
        "created_at": now,
        "expires_at": now + timedelta(days=7)
    }
    ticket_service.firestore.client.collection("sessions").document(token).set(session_data)
    return token

def get_current_user_role(authorization: str | None = Header(None)) -> str:
    """FastAPI Dependency: verifies the session token and returns the user's role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autorización o es inválido",
        )
    token = authorization.split(" ")[1]
    session_ref = ticket_service.firestore.client.collection("sessions").document(token)
    session_snap = session_ref.get()
    if not session_snap.exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada",
        )
    session = session_snap.to_dict()
    expires_at = session.get("expires_at")
    if expires_at:
        if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        now = ticket_service.firestore.now()
        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="La sesión ha expirado",
            )
    return session.get("role")

def require_admin(role: str = Depends(get_current_user_role)) -> str:
    """FastAPI Dependency: ensures the user has the admin role."""
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de administrador",
        )
    return role

def require_guard_or_admin(role: str = Depends(get_current_user_role)) -> str:
    """FastAPI Dependency: ensures the user is either a guard or an admin."""
    if role not in {"admin", "guard"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requiere rol de guardia o administrador",
        )
    return role

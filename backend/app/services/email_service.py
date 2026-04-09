from __future__ import annotations

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings


class EmailService:
    def __init__(self) -> None:
        self.client = SendGridAPIClient(settings.sendgrid_api_key)

    def send_tickets_email(
        self,
        to_email: str,
        visitor_name: str,
        visit_date: str,
        tickets: list[dict],
    ) -> None:
        tickets_html = "".join(
            f"<li><strong>{t['visitor_name']}</strong> — ID: {t['ticket_id']}</li>"
            for t in tickets
        )

        html_content = f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;">
            <h2>¡Tu visita está confirmada!</h2>
            <p>Hola <strong>{visitor_name}</strong>, tu reserva para el 
            <strong>{visit_date}</strong> fue procesada correctamente.</p>
            <p>Tus tiquetes:</p>
            <ul>{tickets_html}</ul>
            <p>Presenta los códigos QR en la entrada del museo. 
            Puedes verlos en la pantalla de confirmación del sistema.</p>
            <hr/>
            <small>Museo de Historia Natural · Universidad del Cauca · Popayán</small>
        </div>
        """

        message = Mail(
            from_email=(settings.sendgrid_from_email, settings.sendgrid_from_name),
            to_emails=to_email,
            subject=f"Tus entradas · Museo de Historia Natural · {visit_date}",
            html_content=html_content,
        )

        response = self.client.send(message)
        print(f"[email] Status: {response.status_code}")
        print(f"[email] Body: {response.body}")


email_service = EmailService()
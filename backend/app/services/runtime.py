from app.services.firestore_service import FirestoreService
from app.services.payment_service import PaymentService
from app.services.report_service import ReportService
from app.services.reservation_service import ReservationService
from app.services.ticket_service import TicketService


firestore_service = FirestoreService()
reservation_service = ReservationService(firestore_service)
payment_service = PaymentService(firestore_service)
ticket_service = TicketService(firestore_service)
report_service = ReportService(firestore_service)

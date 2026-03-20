import { apiClient } from "./apiClient";

export const paymentService = {
    prepareBoldPayment: (bookingId) =>
        apiClient.post(`/payments/${bookingId}/bold/prepare`, {}),

    verifyBoldPayment: ({ bookingId, boldOrderId, boldTxStatus, transactionId }) =>
        apiClient.post("/payments/bold/verify", {
            booking_id: bookingId,
            bold_order_id: boldOrderId,
            bold_tx_status: boldTxStatus,
            transaction_id: transactionId || null
        }),

    verifyPayment: (bookingId, status = "approved") =>
        apiClient.post(`/payments/${bookingId}/verify`, {
            status,
            provider: "simulador"
        })
};

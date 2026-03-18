import { apiClient } from "./apiClient";

export const paymentService = {
  verifyPayment: (bookingId, status = "approved") =>
    apiClient.post(`/payments/${bookingId}/verify`, {
      status,
      provider: "simulador"
    })
};

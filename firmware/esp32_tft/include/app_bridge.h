#ifndef APP_BRIDGE_H
#define APP_BRIDGE_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C"
{
#endif

    bool app_capture_qr_and_validate();
    bool app_capture_document_for_entry();
    bool app_capture_document_for_booking();
    bool app_verify_payment_simulated();
    void app_set_booking_ticket_type(const char *ticketType);

#ifdef __cplusplus
}
#endif

#endif // APP_BRIDGE_H

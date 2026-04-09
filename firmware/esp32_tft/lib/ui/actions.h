#ifndef EEZ_LVGL_UI_EVENTS_H
#define EEZ_LVGL_UI_EVENTS_H

#include <lvgl.h>

#ifdef __cplusplus
extern "C"
{
#endif

    extern void action_go_to_scan_qr_page(lv_event_t *e);
    extern void action_go_to_booking_page(lv_event_t *e);
    extern void action_scan_qr_code(lv_event_t *e);
    extern void action_scan_id_card1(lv_event_t *e);
    extern void action_go_to_main_page(lv_event_t *e);
    extern void action_verify_payment(lv_event_t *e);
    extern void action_go_to_payment_page(lv_event_t *e);
    extern void action_scan_id_card2(lv_event_t *e);
    extern void action_go_to_registration_page_kids(lv_event_t *e);
    extern void action_go_to_registration_page_adults(lv_event_t *e);

#ifdef __cplusplus
}
#endif

#endif /*EEZ_LVGL_UI_EVENTS_H*/
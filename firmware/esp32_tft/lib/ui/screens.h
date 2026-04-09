#ifndef EEZ_LVGL_UI_SCREENS_H
#define EEZ_LVGL_UI_SCREENS_H

#include <lvgl.h>

#ifdef __cplusplus
extern "C"
{
#endif

    // Screens

    enum ScreensEnum
    {
        _SCREEN_ID_FIRST = 1,
        SCREEN_ID_MAIN_PAGE = 1,
        SCREEN_ID_SCAN_QR_PAGE = 2,
        SCREEN_ID_SCAN_ID_CARD_PAGE = 3,
        SCREEN_ID_APPROVED_ENTRY_PAGE = 4,
        SCREEN_ID_INCORRECT_IDENTITY_PAGE = 5,
        SCREEN_ID_INVALID_QR_PAGE = 6,
        SCREEN_ID_BOOKING_PAGE = 7,
        SCREEN_ID_REGISTRATION_PAGE = 8,
        SCREEN_ID_PAYMENT_PAGE = 9,
        _SCREEN_ID_LAST = 9
    };

    typedef struct _objects_t
    {
        lv_obj_t *main_page;
        lv_obj_t *scan_qr_page;
        lv_obj_t *scan_id_card_page;
        lv_obj_t *approved_entry_page;
        lv_obj_t *incorrect_identity_page;
        lv_obj_t *invalid_qr_page;
        lv_obj_t *booking_page;
        lv_obj_t *registration_page;
        lv_obj_t *payment_page;
        lv_obj_t *entry_button;
        lv_obj_t *booking_button;
        lv_obj_t *obj0;
        lv_obj_t *qr_scan_button;
        lv_obj_t *waiting_panel_1;
        lv_obj_t *obj1;
        lv_obj_t *validate_id_button_1;
        lv_obj_t *waiting_panel_2;
        lv_obj_t *obj2;
        lv_obj_t *obj3;
        lv_obj_t *obj4;
        lv_obj_t *obj5;
        lv_obj_t *obj6;
        lv_obj_t *obj7;
        lv_obj_t *obj8;
        lv_obj_t *obj9;
        lv_obj_t *obj10;
        lv_obj_t *validate_id_button_2;
        lv_obj_t *waiting_panel_3;
        lv_obj_t *obj11;
    } objects_t;

    extern objects_t objects;

    void create_screen_main_page();
    void tick_screen_main_page();

    void create_screen_scan_qr_page();
    void tick_screen_scan_qr_page();

    void create_screen_scan_id_card_page();
    void tick_screen_scan_id_card_page();

    void create_screen_approved_entry_page();
    void tick_screen_approved_entry_page();

    void create_screen_incorrect_identity_page();
    void tick_screen_incorrect_identity_page();

    void create_screen_invalid_qr_page();
    void tick_screen_invalid_qr_page();

    void create_screen_booking_page();
    void tick_screen_booking_page();

    void create_screen_registration_page();
    void tick_screen_registration_page();

    void create_screen_payment_page();
    void tick_screen_payment_page();

    void tick_screen_by_id(enum ScreensEnum screenId);
    void tick_screen(int screen_index);

    void create_screens();

#ifdef __cplusplus
}
#endif

#endif /*EEZ_LVGL_UI_SCREENS_H*/
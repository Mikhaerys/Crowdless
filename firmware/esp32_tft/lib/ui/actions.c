#include <lvgl.h>

#include "actions.h"

#include "app_bridge.h"
#include "screens.h"
#include "ui.h"

static void set_waiting_panel_visible(lv_obj_t *panel, bool visible)
{
    if (panel == NULL)
    {
        return;
    }

    if (visible)
    {
        lv_obj_clear_flag(panel, LV_OBJ_FLAG_HIDDEN);
        lv_obj_move_foreground(panel);
    }
    else
    {
        lv_obj_add_flag(panel, LV_OBJ_FLAG_HIDDEN);
    }

    lv_timer_handler();
}

static void go_to_main_page()
{
    loadScreen(SCREEN_ID_MAIN_PAGE);
}

void action_go_to_scan_qr_page(lv_event_t *e)
{
    LV_UNUSED(e);
    loadScreen(SCREEN_ID_SCAN_QR_PAGE);
}

void action_go_to_booking_page(lv_event_t *e)
{
    LV_UNUSED(e);
    loadScreen(SCREEN_ID_BOOKING_PAGE);
}

void action_scan_qr_code(lv_event_t *e)
{
    LV_UNUSED(e);

    set_waiting_panel_visible(objects.waiting_panel_1, true);
    const bool qr_ok = app_capture_qr_and_validate();
    set_waiting_panel_visible(objects.waiting_panel_1, false);

    if (qr_ok)
    {
        loadScreen(SCREEN_ID_SCAN_ID_CARD_PAGE);
    }
    else
    {
        loadScreen(SCREEN_ID_INVALID_QR_PAGE);
    }
}

void action_scan_id_card1(lv_event_t *e)
{
    LV_UNUSED(e);

    set_waiting_panel_visible(objects.waiting_panel_2, true);
    const bool id_ok = app_capture_document_for_entry();
    set_waiting_panel_visible(objects.waiting_panel_2, false);

    if (id_ok)
    {
        loadScreen(SCREEN_ID_APPROVED_ENTRY_PAGE);
    }
    else
    {
        loadScreen(SCREEN_ID_INCORRECT_IDENTITY_PAGE);
    }
}

void action_go_to_main_page(lv_event_t *e)
{
    LV_UNUSED(e);
    go_to_main_page();
}

void action_verify_payment(lv_event_t *e)
{
    LV_UNUSED(e);

    if (app_verify_payment_simulated())
    {
        go_to_main_page();
    }
}

void action_go_to_payment_page(lv_event_t *e)
{
    LV_UNUSED(e);
    loadScreen(SCREEN_ID_PAYMENT_PAGE);
}

void action_scan_id_card2(lv_event_t *e)
{
    LV_UNUSED(e);

    set_waiting_panel_visible(objects.waiting_panel_3, true);
    const bool booking_id_ok = app_capture_document_for_booking();
    set_waiting_panel_visible(objects.waiting_panel_3, false);

    if (booking_id_ok)
    {
        loadScreen(SCREEN_ID_PAYMENT_PAGE);
    }
    else
    {
        loadScreen(SCREEN_ID_INCORRECT_IDENTITY_PAGE);
    }
}

void action_go_to_registration_page_kids(lv_event_t *e)
{
    LV_UNUSED(e);
    app_set_booking_ticket_type("NINOS");
    loadScreen(SCREEN_ID_REGISTRATION_PAGE);
}

void action_go_to_registration_page_adults(lv_event_t *e)
{
    LV_UNUSED(e);
    app_set_booking_ticket_type("ADULTOS");
    loadScreen(SCREEN_ID_REGISTRATION_PAGE);
}

/**
 * @file lv_conf.h
 * Minimal LVGL v9 project configuration override.
 * Keep this file in the project include path and set LV_CONF_INCLUDE_SIMPLE.
 */

#if 1
#ifndef LV_CONF_H
#define LV_CONF_H

/* Match the ILI9341 RGB565 format used by TFT_eSPI. */
#define LV_COLOR_DEPTH 16

/* Avoid a large static LVGL heap in DRAM on ESP32. */
#define LV_USE_STDLIB_MALLOC LV_STDLIB_CLIB
#define LV_USE_STDLIB_STRING LV_STDLIB_CLIB
#define LV_USE_STDLIB_SPRINTF LV_STDLIB_CLIB

/* We increment LVGL ticks manually in pumpUi(). */
#define LV_TICK_CUSTOM 0

/* Keep warnings enabled to help diagnose touch/display calibration issues. */
#define LV_USE_LOG 1
#define LV_LOG_LEVEL LV_LOG_LEVEL_WARN

/* EEZ-generated screens reference these fonts explicitly. */
#define LV_FONT_MONTSERRAT_10 1
#define LV_FONT_MONTSERRAT_18 1
#define LV_FONT_MONTSERRAT_22 1
#define LV_FONT_MONTSERRAT_30 1
#define LV_FONT_MONTSERRAT_32 1

/* Payment screen uses the QR widget. */
#define LV_USE_QRCODE 1

#endif /* LV_CONF_H */
#endif

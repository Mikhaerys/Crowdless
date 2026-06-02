from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from typing import Any

import holidays
import joblib
import numpy as np
import pandas as pd
from google.cloud.firestore_v1 import FieldFilter

from app.services.firestore_service import FirestoreService

logger = logging.getLogger(__name__)

DEFAULT_FEATURE_COLS = [
    "dia_semana", "mes", "dia_mes", "semana_anio", "dia_anio", "anio", "es_fin_semana",
    "sin_dia_semana", "cos_dia_semana", "sin_mes", "cos_mes", "sin_dia_anio", "cos_dia_anio",
    "es_festivo_co", "es_semana_santa",
    "lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "lag_6", "lag_7", "lag_8", "lag_9", "lag_10",
    "lag_11", "lag_12", "lag_13", "lag_14", "lag_15",
    "media_movil_7", "media_movil_15", "std_movil_7"
]


class PredictionService:
    def __init__(self, firestore_service: FirestoreService) -> None:
        self.firestore = firestore_service
        self.model = None
        self.feature_cols = DEFAULT_FEATURE_COLS
        self.model_loaded = False
        self.metadata = {}

        # Intentar cargar el modelo y las features
        self._load_model()

    def _load_model(self) -> None:
        resources_dir = os.path.join(os.path.dirname(__file__), "..", "resources", "model")
        model_path = os.path.join(resources_dir, "modelo_afluencia_museo.pkl")
        features_path = os.path.join(resources_dir, "feature_cols.json")
        metadata_path = os.path.join(resources_dir, "metadata_modelo.json")

        if os.path.exists(model_path) and os.path.exists(features_path):
            try:
                self.model = joblib.load(model_path)
                with open(features_path, "r", encoding="utf-8") as f:
                    self.feature_cols = json.load(f)
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                self.model_loaded = True
                logger.info("✅ Modelo de predicción cargado correctamente.")
            except Exception as e:
                logger.error(f"❌ Error al cargar el modelo de predicción: {e}")
        else:
            logger.warning(
                f"⚠️ Archivos del modelo no encontrados en {resources_dir}. "
                "Se utilizará el predictor simulado de respaldo."
            )

    def reload_model(self) -> bool:
        """Permite recargar el modelo desde disco una vez el usuario suba los archivos."""
        self._load_model()
        return self.model_loaded

    def es_semana_santa(self, fecha: date) -> bool:
        """Determina si una fecha cae en Semana Santa en Colombia usando Butcher-Meeus."""
        anio = fecha.year
        a = anio % 19
        b = anio // 100
        c = anio % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        mes = (h + l - 7 * m + 114) // 31
        dia = ((h + l - 7 * m + 114) % 31) + 1
        
        pascua = date(anio, mes, dia)
        inicio_ss = pascua - timedelta(days=7)
        fin_ss = pascua
        return inicio_ss <= fecha <= fin_ss

    def _get_historical_visitors(self, start_date: date, end_date: date) -> list[int]:
        """Obtiene de Firestore el conteo real de visitantes por día en un rango de fechas."""
        # Consultar reservas aprobadas en el rango
        bookings_query = (
            self.firestore.bookings
            .where(filter=FieldFilter("visit_date", ">=", start_date.isoformat()))
            .where(filter=FieldFilter("visit_date", "<=", end_date.isoformat()))
        )

        daily_totals: dict[str, int] = {}
        for document in bookings_query.stream():
            booking = document.to_dict()
            if booking.get("payment_status") == "approved":
                visit_date_str = booking["visit_date"]
                tickets = int(booking.get("total_tickets", 0))
                daily_totals[visit_date_str] = daily_totals.get(visit_date_str, 0) + tickets

        # Asegurar un valor para cada día en el rango de fechas
        num_days = (end_date - start_date).days + 1
        historical_counts = []
        for i in range(num_days):
            current_day = start_date + timedelta(days=i)
            historical_counts.append(daily_totals.get(current_day.isoformat(), 0))

        return historical_counts

    def predict_single_day(
        self,
        fecha_objetivo: date,
        historial_15_dias: list[int]
    ) -> int:
        """Predice la afluencia para un único día."""
        if len(historial_15_dias) != 15:
            raise ValueError(f"Se requieren exactamente 15 días de historial, recibidos: {len(historial_15_dias)}")

        # Si el modelo no está cargado, usar la fórmula simulada (fallback)
        if not self.model_loaded:
            return self._predict_fallback(fecha_objetivo)

        # Generar festivos colombianos para el año objetivo
        festivos_co = holidays.Colombia(years=[fecha_objetivo.year])
        
        fecha_ts = pd.Timestamp(fecha_objetivo)
        
        # Construir el diccionario de características
        fila: dict[str, Any] = {}
        fila["dia_semana"] = fecha_ts.dayofweek
        fila["mes"] = fecha_ts.month
        fila["dia_mes"] = fecha_ts.day
        fila["semana_anio"] = int(fecha_ts.isocalendar()[1])
        fila["dia_anio"] = fecha_ts.dayofyear
        fila["anio"] = fecha_ts.year
        fila["es_fin_semana"] = int(fecha_ts.dayofweek >= 5)
        
        # Codificación cíclica
        fila["sin_dia_semana"] = np.sin(2 * np.pi * fila["dia_semana"] / 7)
        fila["cos_dia_semana"] = np.cos(2 * np.pi * fila["dia_semana"] / 7)
        fila["sin_mes"] = np.sin(2 * np.pi * fila["mes"] / 12)
        fila["cos_mes"] = np.cos(2 * np.pi * fila["mes"] / 12)
        fila["sin_dia_anio"] = np.sin(2 * np.pi * fila["dia_anio"] / 365)
        fila["cos_dia_anio"] = np.cos(2 * np.pi * fila["dia_anio"] / 365)
        
        fila["es_festivo_co"] = int(fecha_objetivo in festivos_co)
        fila["es_semana_santa"] = int(self.es_semana_santa(fecha_objetivo))

        # Reversar el historial para que lag_1 sea ayer, lag_2 anteayer, etc.
        historial_rev = list(reversed(historial_15_dias))
        for i in range(1, 16):
            fila[f"lag_{i}"] = historial_rev[i - 1]

        # Estadísticas móviles
        fila["media_movil_7"] = float(np.mean(historial_15_dias[-7:]))
        fila["media_movil_15"] = float(np.mean(historial_15_dias))
        # numpy.std por defecto usa ddof=0 como pandas (cuando rolling se calcula)
        fila["std_movil_7"] = float(np.std(historial_15_dias[-7:]))

        # Crear DataFrame en el orden correcto de features
        X_pred = pd.DataFrame([{col: fila.get(col, 0) for col in self.feature_cols}])

        try:
            prediction = self.model.predict(X_pred)[0]
            return int(np.clip(prediction, 0, None))
        except Exception as e:
            logger.error(f"Error ejecutando predicción con el modelo: {e}")
            return self._predict_fallback(fecha_objetivo)

    def _predict_fallback(self, fecha: date) -> int:
        """Fórmula matemática determinista basada en el generador sintético para fallback."""
        dia_semana = fecha.weekday()
        mes = fecha.month
        es_ss = self.es_semana_santa(fecha)
        festivos_co = holidays.Colombia(years=[fecha.year])
        es_festivo = fecha in festivos_co

        # Museo cerrado los lunes usualmente
        if dia_semana == 0 and not es_ss:
            return 0

        base_por_dia = {
            0: 180,  # Lunes
            1: 220,  # Martes
            2: 230,  # Miércoles
            3: 240,  # Jueves
            4: 310,  # Viernes
            5: 520,  # Sábado
            6: 480,  # Domingo
        }
        base = base_por_dia.get(dia_semana, 230)
        mult = 1.0

        if es_ss:
            mult *= 3.5
        elif mes in [6, 7]:
            mult *= 1.95
        elif mes == 12 and fecha.day <= 24:
            mult *= 1.7
        elif mes == 10 and 12 <= fecha.day <= 20:
            mult *= 1.45
        elif mes in [1, 2]:
            mult *= 0.8

        if es_festivo and not es_ss:
            mult *= 1.35

        # Añadir pequeña variabilidad determinista basada en el día del mes
        ruido = 1.0 + (0.05 * (1 if fecha.day % 2 == 0 else -1))
        
        visitantes = int(base * mult * ruido)
        return max(0, min(visitantes, 1200))

    def forecast_range(
        self,
        start_date: date,
        days: int = 7
    ) -> list[dict[str, Any]]:
        """Predice de forma encadenada (recursiva) un rango de días futuros."""
        if days < 1:
            return []

        # Obtener los 15 días de historial justo antes de start_date
        seed_start = start_date - timedelta(days=15)
        seed_end = start_date - timedelta(days=1)
        
        historial = self._get_historical_visitors(seed_start, seed_end)
        
        # En caso de que falten días (por ejemplo, al inicio de la BD), rellenar con 0s
        if len(historial) < 15:
            historial = [0] * (15 - len(historial)) + historial

        forecast = []
        festivos_co = holidays.Colombia(years=list(range(start_date.year, start_date.year + 2)))

        for i in range(days):
            current_date = start_date + timedelta(days=i)
            
            # Predicción para el día actual
            pred = self.predict_single_day(current_date, historial[-15:])
            
            # Identificar factores explicativos para enviar al frontend
            factores = []
            if self.es_semana_santa(current_date):
                factores.append("Semana Santa")
            if current_date in festivos_co:
                factores.append(f"Festivo ({festivos_co.get(current_date)})")
            if current_date.weekday() >= 5:
                factores.append("Fin de semana")
            if current_date.weekday() == 0 and not self.es_semana_santa(current_date):
                factores.append("Cerrado por mantenimiento")

            forecast.append({
                "date": current_date.isoformat(),
                "day_name": current_date.strftime("%A"),
                "prediction": pred,
                "factors": factores,
                "is_holiday": current_date in festivos_co or self.es_semana_santa(current_date),
            })
            
            # Añadir la predicción como lag para la siguiente iteración
            historial.append(pred)

        return forecast

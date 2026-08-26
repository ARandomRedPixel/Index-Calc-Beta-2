"""Lectura del libro de referencia y exportación del informe de resultados."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from calculos import ESCENARIOS, normalizar_valores_esvd, numero, texto


HOJA_VALORES = "VALORES_ESVD"
HOJA_CONFIG = "CONFIGURACION"


def _abrir(origen: str | Path | bytes | BinaryIO):
    if isinstance(origen, bytes):
        origen = BytesIO(origen)
    return load_workbook(origen, read_only=True, data_only=False)


def cargar_libro_referencia(origen: str | Path | bytes | BinaryIO) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    libro = _abrir(origen)
    if HOJA_CONFIG not in libro.sheetnames or HOJA_VALORES not in libro.sheetnames:
        raise ValueError("El archivo debe contener las hojas CONFIGURACION y VALORES_ESVD.")

    ws_cfg = libro[HOJA_CONFIG]
    config: dict[str, Any] = {}
    for fila in ws_cfg.iter_rows(min_row=5, values_only=True):
        clave = texto(fila[0])
        if clave:
            config[clave] = fila[1]

    ws = libro[HOJA_VALORES]
    encabezados = [texto(c.value) for c in ws[5]]
    if "ID_PARAMETRO" not in encabezados or "SERVICIO_ECOSISTEMICO" not in encabezados:
        raise ValueError("La hoja VALORES_ESVD no tiene los encabezados esperados en la fila 5.")
    parametros: list[dict[str, Any]] = []
    for valores in ws.iter_rows(min_row=6, values_only=True):
        fila = dict(zip(encabezados, valores))
        if not texto(fila.get("ID_PARAMETRO")):
            continue
        parametros.append(normalizar_valores_esvd(fila))
    libro.close()
    return config, parametros


def _limpiar(valor: Any) -> Any:
    if valor is None:
        return ""
    if isinstance(valor, (str, int, float, bool, datetime)):
        return valor
    return str(valor)


def _ajustar_hoja(ws) -> None:
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for celda in ws[1]:
        celda.fill = PatternFill("solid", fgColor="147D80")
        celda.font = Font(color="FFFFFF", bold=True)
        celda.alignment = Alignment(wrap_text=True, vertical="center")
    for col in range(1, ws.max_column + 1):
        largo = max((len(str(ws.cell(r, col).value or "")) for r in range(1, min(ws.max_row, 100) + 1)), default=8)
        ws.column_dimensions[get_column_letter(col)].width = min(42, max(11, largo + 2))
    for fila in ws.iter_rows(min_row=2):
        for celda in fila:
            celda.alignment = Alignment(wrap_text=True, vertical="top")


def crear_reporte_xlsx(
    caso: dict[str, Any],
    resultado: dict[str, Any],
    vida_silvestre: list[dict[str, Any]],
    servicios: list[dict[str, Any]],
    costos: list[dict[str, Any]],
) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "RESUMEN"
    moneda = texto(caso.get("moneda")) or "moneda del modelo"
    ws.append(["Cuenta", "Descripción", "Bajo", "Central", "Alto", "Tratamiento"])
    nombres = {
        "A": "Daño biológico monetizable",
        "B": "Pérdida de servicios ecosistémicos",
        "C": "Respuesta pública incremental",
        "D": "Rescate, rehabilitación y cuidado",
        "E": "Efectos conexos demostrados",
        "R": "Reparación/restauración/equivalencia",
    }
    for cuenta in ("A", "B", "C", "D", "E", "R"):
        valores = resultado["principal_por_cuenta"][cuenta]
        tratamiento = "Separada del subtotal de daños" if cuenta == "R" else "Cuenta principal"
        ws.append([cuenta, nombres[cuenta], *(valores[e] for e in ESCENARIOS), tratamiento])
    if caso.get("permitir_agregacion"):
        ws.append(["SUBTOTAL", f"Subtotal de daños ({moneda})", *(resultado["subtotal_danos"][e] for e in ESCENARIOS), "Agregación autorizada"])
    else:
        ws.append(["SUBTOTAL", "No mostrado: falta autorización de agregación", "", "", "", "Revise doble conteo"])
    ws.append(["EXPLORATORIO", "Total de líneas exploratorias", *(resultado["total_exploratorio"][e] for e in ESCENARIOS), "No integrar al escenario central"])
    for row in ws.iter_rows(min_row=2, min_col=3, max_col=5):
        for cell in row:
            cell.number_format = '#,##0.00'
    _ajustar_hoja(ws)

    hojas = [
        ("DETALLE_CALCULO", resultado["detalle"]),
        ("VIDA_SILVESTRE", vida_silvestre),
        ("SERVICIOS_ENTRADA", servicios),
        ("COSTOS_ENTRADA", costos),
    ]
    for nombre, filas in hojas:
        tab = wb.create_sheet(nombre)
        if filas:
            encabezados = list(filas[0].keys())
            tab.append(encabezados)
            for fila in filas:
                tab.append([_limpiar(fila.get(c)) for c in encabezados])
        else:
            tab.append(["Sin registros"])
        _ajustar_hoja(tab)

    adv = wb.create_sheet("ADVERTENCIAS")
    adv.append(["Advertencia"])
    for mensaje in resultado["advertencias"] or ["Sin advertencias automáticas."]:
        adv.append([mensaje])
    _ajustar_hoja(adv)

    meta = wb.create_sheet("METADATOS")
    meta.append(["Campo", "Valor"])
    for clave, valor in caso.items():
        meta.append([clave, _limpiar(valor)])
    meta.append(["fecha_exportacion", datetime.now().isoformat(timespec="seconds")])
    meta.append(["nota", "Estimación preliminar. Requiere validación ecológica, económica y jurídica."])
    _ajustar_hoja(meta)

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


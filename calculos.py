"""Motor de cálculo para la valoración del daño para efectos procesales (VDEP).

El módulo no depende de Streamlit. Esto permite probar la matemática de forma
aislada y reutilizarla en otras interfaces.
"""

from __future__ import annotations

from collections import Counter
from math import ceil, isfinite
from typing import Any, Iterable


ESCENARIOS = ("bajo", "central", "alto")
CUENTAS_DANOS = ("A1", "A2", "B", "C", "D", "E")
CUENTAS_VALIDAS = (*CUENTAS_DANOS, "R")
RANGO_EVIDENCIA = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "X": 6}


def numero(valor: Any, predeterminado: float = 0.0) -> float:
    """Convierte un valor de formulario a float sin propagar NaN o infinitos."""
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return predeterminado
    return n if isfinite(n) else predeterminado


def texto(valor: Any) -> str:
    if valor is None:
        return ""
    salida = str(valor).strip()
    return "" if salida.lower() == "nan" else salida


def es_si(valor: Any) -> bool:
    return texto(valor).lower() in {"sí", "si", "s", "yes", "true", "1"}


def combinar_evidencia(*niveles: Any) -> str:
    """Devuelve el nivel más débil de la cadena probatoria."""
    limpios = [texto(n).upper() for n in niveles if texto(n)]
    if not limpios:
        return "E"
    return max(limpios, key=lambda n: RANGO_EVIDENCIA.get(n, 5))


def clasificar_linea(evidencia: Any, nexo_causal: Any, comparabilidad: Any = "") -> str:
    """Clasifica una línea como principal, exploratoria o excluida."""
    nivel = texto(evidencia).upper() or "E"
    comp = texto(comparabilidad).lower()
    if nivel == "X" or not es_si(nexo_causal):
        return "excluida"
    if nivel in {"D", "E"} or comp == "baja":
        return "exploratoria"
    return "principal"


def normalizar_valores_esvd(fila: dict[str, Any]) -> dict[str, Any]:
    """Recalcula los valores normalizados sin depender de fórmulas guardadas."""
    factores = (
        numero(fila.get("FACTOR_CONVERSION_MONEDA"), 0.0),
        numero(fila.get("FACTOR_ANIO_PRECIOS"), 0.0),
        numero(fila.get("FACTOR_TRANSFERENCIA_VALIDADO"), 0.0),
    )
    multiplicador = factores[0] * factores[1] * factores[2]
    salida = dict(fila)
    for escenario in ESCENARIOS:
        origen = numero(fila.get(f"VALOR_{escenario.upper()}_ORIGINAL"), 0.0)
        salida[f"VALOR_{escenario.upper()}_NORMALIZADO"] = origen * multiplicador

    obligatorios = [
        texto(fila.get("ID_PARAMETRO")),
        texto(fila.get("SERVICIO_ECOSISTEMICO")),
        texto(fila.get("UNIDAD_BASE")),
        numero(salida.get("VALOR_CENTRAL_NORMALIZADO"), 0.0),
        texto(fila.get("NIVEL_EVIDENCIA")),
        texto(fila.get("COMPARABILIDAD")),
        texto(fila.get("FUENTE_URL_CITA")),
    ]
    if not all(obligatorios):
        estado = "INCOMPLETO"
    elif any(f <= 0 for f in factores):
        estado = "REVISAR FACTORES"
    elif texto(fila.get("NIVEL_EVIDENCIA")).upper() == "X":
        estado = "EXCLUIDO"
    elif texto(fila.get("COMPARABILIDAD")).lower() == "baja" or texto(
        fila.get("NIVEL_EVIDENCIA")
    ).upper() in {"D", "E"}:
        estado = "EXPLORATORIO"
    else:
        estado = "LISTO"
    salida["ESTADO_PARAMETRO"] = estado
    return salida


def fracciones_perdida(
    perdida_inicial: Any,
    anios_recuperacion: Any,
    perfil: Any,
    horizonte_maximo: int,
) -> list[float]:
    """Genera la pérdida anual como proporción entre 0 y 1.

    El primer periodo es t=0. En un perfil lineal de N años, la pérdida cae en
    partes iguales y llega a cero al finalizar el año N.
    """
    perdida = min(1.0, max(0.0, numero(perdida_inicial)))
    nombre = texto(perfil).lower()
    if perdida == 0 or "inmediata" in nombre:
        return []
    n = min(max(1, ceil(numero(anios_recuperacion, 1.0))), max(1, horizonte_maximo))
    if "constante" in nombre:
        return [perdida] * n
    return [perdida * (1 - t / n) for t in range(n)]


def valor_presente_flujo(flujos: Iterable[float], tasa: Any) -> float:
    r = max(-0.99, numero(tasa))
    return sum(numero(flujo) / ((1 + r) ** periodo) for periodo, flujo in enumerate(flujos))


def calcular_servicio(fila: dict[str, Any], tasas: dict[str, float], horizonte: int) -> dict[str, Any]:
    evidencia = combinar_evidencia(fila.get("evidencia"), fila.get("evidencia_parametro"))
    categoria = clasificar_linea(evidencia, fila.get("nexo_causal"), fila.get("comparabilidad"))
    unidades = max(0.0, numero(fila.get("unidades_afectadas")))
    resultado = {
        "tipo": "Servicio ecosistémico",
        "cuenta": "B",
        "concepto": texto(fila.get("servicio")) or texto(fila.get("id_parametro")) or "Servicio sin nombre",
        "categoria": categoria,
        "evidencia": evidencia,
        "nexo_causal": texto(fila.get("nexo_causal")),
        "fuente": texto(fila.get("fuente")),
        "tipo_fuente": texto(fila.get("tipo_fuente")) or "Transferencia de valor",
        "estado_dato": texto(fila.get("estado_dato")) or "Estimado",
        "n_referencia": texto(fila.get("n_referencia")),
        "estadistico": texto(fila.get("estadistico")),
        "periodo_referencia": texto(fila.get("periodo_referencia")),
        "grupo_doble_conteo": texto(fila.get("grupo_doble_conteo")),
        "unidad": texto(fila.get("unidad_base")),
    }
    for escenario in ESCENARIOS:
        valor_unitario = max(0.0, numero(fila.get(f"valor_unitario_{escenario}")))
        fracciones = fracciones_perdida(
            fila.get(f"perdida_inicial_{escenario}"),
            fila.get(f"recuperacion_{escenario}"),
            fila.get("perfil_recuperacion"),
            horizonte,
        )
        flujos = [unidades * valor_unitario * fraccion for fraccion in fracciones]
        resultado[escenario] = valor_presente_flujo(flujos, tasas[escenario])
    return resultado


def calcular_costo(fila: dict[str, Any], tasas: dict[str, float]) -> dict[str, Any]:
    evidencia = combinar_evidencia(fila.get("evidencia"))
    categoria = clasificar_linea(evidencia, fila.get("nexo_causal"))
    anio = max(0, int(numero(fila.get("anio_desde_evento"))))
    cuenta = texto(fila.get("cuenta")).upper() or "E"
    resultado = {
        "tipo": "Costo monetario",
        "cuenta": cuenta,
        "concepto": texto(fila.get("concepto")) or "Costo sin nombre",
        "categoria": categoria,
        "evidencia": evidencia,
        "nexo_causal": texto(fila.get("nexo_causal")),
        "fuente": texto(fila.get("fuente")),
        "tipo_fuente": texto(fila.get("tipo_fuente")) or "Dato del expediente",
        "estado_dato": texto(fila.get("estado_dato")) or "Observado",
        "n_referencia": texto(fila.get("n_referencia")),
        "estadistico": texto(fila.get("estadistico")),
        "periodo_referencia": texto(fila.get("periodo_referencia")),
        "grupo_doble_conteo": texto(fila.get("grupo_doble_conteo")),
        "unidad": texto(fila.get("unidad")),
    }
    for escenario in ESCENARIOS:
        cantidad = max(0.0, numero(fila.get(f"cantidad_{escenario}")))
        costo = max(0.0, numero(fila.get(f"costo_unitario_{escenario}")))
        resultado[escenario] = cantidad * costo / ((1 + max(-0.99, tasas[escenario])) ** anio)
    return resultado


def _filas_no_vacias(filas: Iterable[dict[str, Any]], campos: tuple[str, ...]) -> list[dict[str, Any]]:
    return [fila for fila in filas if any(texto(fila.get(c)) for c in campos)]


def calcular_modelo(
    servicios: Iterable[dict[str, Any]],
    costos: Iterable[dict[str, Any]],
    configuracion: dict[str, Any],
) -> dict[str, Any]:
    tasas = {
        "bajo": numero(configuracion.get("tasa_descuento_baja"), 0.05),
        "central": numero(configuracion.get("tasa_descuento_central"), 0.03),
        "alto": numero(configuracion.get("tasa_descuento_alta"), 0.01),
    }
    horizonte = max(1, int(numero(configuracion.get("horizonte_maximo_anios"), 30)))
    filas_servicio = _filas_no_vacias(servicios, ("servicio", "id_parametro"))
    filas_costo = _filas_no_vacias(costos, ("concepto",))
    detalle = [calcular_servicio(f, tasas, horizonte) for f in filas_servicio]
    detalle.extend(calcular_costo(f, tasas) for f in filas_costo)

    principal = {cuenta: {e: 0.0 for e in ESCENARIOS} for cuenta in CUENTAS_VALIDAS}
    exploratorio = {cuenta: {e: 0.0 for e in ESCENARIOS} for cuenta in CUENTAS_VALIDAS}
    excluidas: list[dict[str, Any]] = []
    for fila in detalle:
        cuenta = fila["cuenta"] if fila["cuenta"] in principal else "E"
        if fila["categoria"] == "principal":
            destino = principal[cuenta]
        elif fila["categoria"] == "exploratoria":
            destino = exploratorio[cuenta]
        else:
            excluidas.append(fila)
            continue
        for escenario in ESCENARIOS:
            destino[escenario] += numero(fila[escenario])

    subtotal_danos = {
        escenario: sum(principal[c][escenario] for c in CUENTAS_DANOS)
        for escenario in ESCENARIOS
    }
    total_compatible = {
        escenario: subtotal_danos[escenario] + principal["R"][escenario]
        for escenario in ESCENARIOS
    }
    total_exploratorio = {
        escenario: sum(exploratorio[c][escenario] for c in CUENTAS_VALIDAS)
        for escenario in ESCENARIOS
    }

    por_estado_dato = {
        estado: {escenario: 0.0 for escenario in ESCENARIOS}
        for estado in ("Observado", "Estimado")
    }
    for fila in detalle:
        if fila["categoria"] == "excluida":
            continue
        estado = "Observado" if texto(fila.get("estado_dato")).lower().startswith("observ") else "Estimado"
        for escenario in ESCENARIOS:
            por_estado_dato[estado][escenario] += numero(fila[escenario])

    advertencias: list[str] = []
    for fila in detalle:
        if not fila["fuente"]:
            advertencias.append(f"Falta fuente o expediente: {fila['concepto']}.")
        if not texto(fila["estado_dato"]).lower().startswith("observ") and texto(
            fila["tipo_fuente"]
        ).lower().startswith("base histórica"):
            faltantes = []
            if not fila["n_referencia"]:
                faltantes.append("n")
            if not fila["estadistico"]:
                faltantes.append("estadístico")
            if not fila["periodo_referencia"]:
                faltantes.append("periodo")
            if faltantes:
                advertencias.append(
                    f"Complete el pedigrí histórico ({', '.join(faltantes)}): {fila['concepto']}."
                )
        if not (numero(fila["bajo"]) <= numero(fila["central"]) <= numero(fila["alto"])):
            advertencias.append(f"El rango bajo-central-alto no es creciente: {fila['concepto']}.")
    grupos = Counter(
        f["grupo_doble_conteo"]
        for f in detalle
        if f["categoria"] != "excluida" and f["grupo_doble_conteo"]
    )
    for grupo, cantidad in grupos.items():
        if cantidad > 1:
            advertencias.append(
                f"Revise posible doble conteo: el grupo '{grupo}' aparece en {cantidad} líneas activas."
            )
    if excluidas:
        advertencias.append(
            f"Se excluyeron {len(excluidas)} líneas por falta de nexo causal o evidencia no utilizable."
        )
    if not detalle:
        advertencias.append("No hay líneas monetizables. Registre al menos un servicio o costo.")

    return {
        "tasas": tasas,
        "horizonte": horizonte,
        "principal_por_cuenta": principal,
        "exploratorio_por_cuenta": exploratorio,
        "subtotal_danos": subtotal_danos,
        "total_compatible": total_compatible,
        "reparacion": principal["R"],
        "por_estado_dato": por_estado_dato,
        "total_exploratorio": total_exploratorio,
        "detalle": detalle,
        "excluidas": excluidas,
        "advertencias": sorted(set(advertencias)),
    }

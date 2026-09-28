from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from calculos import ESCENARIOS, calcular_modelo, calcular_multas_7317, numero, texto
from excel_io import (
    cargar_libro_referencia,
    crear_reporte_xlsx,
    fila_costo_desde_referencia,
    fila_multa_desde_referencia,
    fila_receptor_desde_caso,
    fila_servicio_desde_parametro,
    filas_especie_desde_referencia,
    seleccionar_filas_demo,
)


BASE_DIR = Path(__file__).resolve().parent
LIBRO_PREDETERMINADO = BASE_DIR / "data" / "Plantilla_Calculadora_ESVD_ES.xlsx"

st.set_page_config(
    page_title="Calculadora procesal VDEP",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.7rem; padding-bottom: 3rem;}
      .esvd-hero {background: linear-gradient(120deg,#143A52,#147D80); color:white;
                  padding:1.2rem 1.5rem; border-radius:14px; margin-bottom:1rem;}
      .esvd-hero h1 {margin:0; font-size:2rem;}
      .esvd-hero p {margin:.35rem 0 0; opacity:.92;}
      .small-note {color:#5F6B73; font-size:.9rem;}
    </style>
    <div class="esvd-hero">
      <h1>Calculadora VDEP</h1>
      <p>Estimación durante un expediente abierto con datos observados, referencias históricas y rangos visibles.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def leer_referencia(contenido: bytes):
    return cargar_libro_referencia(contenido)


def registros(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    limpio = df.where(pd.notna(df), None)
    return limpio.to_dict(orient="records")


def fila_servicio_vacia() -> dict:
    return {
        "id_parametro": "",
        "servicio": "",
        "unidad_base": "",
        "unidades_afectadas": 0.0,
        "valor_unitario_bajo": 0.0,
        "valor_unitario_central": 0.0,
        "valor_unitario_alto": 0.0,
        "perdida_inicial_bajo": 0.0,
        "perdida_inicial_central": 0.0,
        "perdida_inicial_alto": 0.0,
        "recuperacion_bajo": 1,
        "recuperacion_central": 1,
        "recuperacion_alto": 1,
        "perfil_recuperacion": "Lineal",
        "evidencia": "B",
        "evidencia_parametro": "",
        "comparabilidad": "Media",
        "nexo_causal": "Sí",
        "beneficiarios": "",
        "fuente": "",
        "tipo_fuente": "Transferencia de valor unitario",
        "estado_dato": "Estimado",
        "n_referencia": "",
        "estadistico": "",
        "periodo_referencia": "",
        "grupo_doble_conteo": "",
    }


def fila_costo_vacia() -> dict:
    return {
        "id_referencia": "",
        "cuenta": "A1",
        "concepto": "",
        "base_calculo": "",
        "unidad": "",
        "anio_desde_evento": 0,
        "cantidad_bajo": 1.0,
        "cantidad_central": 1.0,
        "cantidad_alto": 1.0,
        "costo_unitario_bajo": 0.0,
        "costo_unitario_central": 0.0,
        "costo_unitario_alto": 0.0,
        "evidencia": "B",
        "nexo_causal": "Sí",
        "fuente": "",
        "tipo_fuente": "Dato del expediente",
        "estado_dato": "Observado",
        "n_referencia": "",
        "estadistico": "",
        "periodo_referencia": "",
        "grupo_doble_conteo": "",
        "notas": "",
    }


def inicializar_estado():
    if "editor_version" not in st.session_state:
        st.session_state.editor_version = 0
    if "vida_df" not in st.session_state:
        st.session_state.vida_df = pd.DataFrame(
            columns=[
                "id_referencia", "especie_grupo", "cantidad", "tipo_afectacion", "funcion_ecologica",
                "nexo_causal", "evidencia", "fuente_expediente", "notas",
            ]
        )
    if "servicios_df" not in st.session_state:
        st.session_state.servicios_df = pd.DataFrame([fila_servicio_vacia()])
    if "costos_df" not in st.session_state:
        st.session_state.costos_df = pd.DataFrame([fila_costo_vacia()])
    if "variables_df" not in st.session_state:
        st.session_state.variables_df = pd.DataFrame()
    if "multas_df" not in st.session_state:
        st.session_state.multas_df = pd.DataFrame()
    st.session_state.setdefault("nombre_caso", "")
    st.session_state.setdefault("autoridad", "")
    st.session_state.setdefault("ubicacion", "")
    st.session_state.setdefault("conducta", "")
    st.session_state.setdefault("hecho_probado", "")
    st.session_state.setdefault("receptor_principal", "")
    st.session_state.setdefault("linea_base", "")
    st.session_state.setdefault("cambio_biofisico", "")
    st.session_state.setdefault("consecuencia", "")
    st.session_state.setdefault("version_valoracion", "VDEP-1")
    st.session_state.setdefault("responsable", "")
    st.session_state.setdefault("gravedad_factores", [])
    st.session_state.setdefault("gravedad_notas", "")
    st.session_state.setdefault("revision_causal", False)
    st.session_state.setdefault("revision_incertidumbre", False)
    st.session_state.setdefault("revision_doble", False)
    st.session_state.setdefault("permitir_agregacion_ui", False)
    st.session_state.setdefault("demostracion_activa", False)
    st.session_state.setdefault("caso_aplicado_id", "")
    st.session_state.setdefault("caso_aplicado_fuente", "")
    st.session_state.setdefault("control_doble_caso", "")
    st.session_state.setdefault("cambio_vdtc_caso", "")
    st.session_state.setdefault("totales_publicados", {})
    st.session_state.setdefault("moneda_modelo_ui", "")
    st.session_state.setdefault("anio_base_ui", 0)
    st.session_state.setdefault("salario_base_7317", 0.0)
    st.session_state.setdefault("tipo_cambio_multas", 1.0)
    st.session_state.setdefault("revision_multas", False)


def agregar_fila(clave: str, fila: dict, campos_contenido: tuple[str, ...]) -> None:
    df = st.session_state[clave]
    primera_vacia = df.empty or (
        len(df) == 1 and not any(texto(df.iloc[0].get(c)) for c in campos_contenido)
    )


def reiniciar_multas() -> None:
    """Conserva el catálogo cargado y limpia las decisiones del caso anterior."""
    if not st.session_state.multas_df.empty:
        multas = st.session_state.multas_df.copy()
        multas["aplica"] = False
        multas["monto_firme_crc"] = 0.0
        multas["observaciones"] = ""
        st.session_state.multas_df = multas
    st.session_state.revision_multas = False
    st.session_state[clave] = (
        pd.DataFrame([fila]) if primera_vacia else pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
    )


def cargar_caso_demostrativo(config_excel, parametros, especies, costos) -> None:
    parametros_demo, parametros_configurados = seleccionar_filas_demo(parametros)
    especies_demo, especies_configuradas = seleccionar_filas_demo(especies)
    costos_demo_ref, costos_configurados = seleccionar_filas_demo(costos)

    # Compatibilidad con libros de demostración anteriores a las columnas de control.
    if not especies_configuradas:
        especies_demo = especies[:3]
    if not parametros_configurados:
        parametros_demo = parametros[:3]
    if not costos_configurados:
        costos_demo_ref = []
        for cuenta in ("C", "D", "E", "R"):
            referencia = next((c for c in costos if texto(c.get("CUENTA")) == cuenta), None)
            if referencia:
                costos_demo_ref.append(referencia)

    vida, costos_especies = [], []
    for referencia in especies_demo:
        cantidad = numero(referencia.get("CANTIDAD_CASO_DEMO"), 2)
        registro, costo = filas_especie_desde_referencia(referencia, cantidad)
        vida.append(registro)
        costos_especies.append(costo)
    servicios_demo = [fila_servicio_desde_parametro(p) for p in parametros_demo]
    costos_demo = [fila_costo_desde_referencia(c) for c in costos_demo_ref]
    st.session_state.vida_df = pd.DataFrame(vida)
    st.session_state.servicios_df = (
        pd.DataFrame(servicios_demo) if servicios_demo else pd.DataFrame([fila_servicio_vacia()])
    )
    st.session_state.costos_df = pd.DataFrame(costos_especies + costos_demo)
    st.session_state.nombre_caso = texto(config_excel.get("demo_id_caso")) or "DEMO-VDEP-001"
    st.session_state.autoridad = texto(config_excel.get("demo_autoridad")) or "Autoridad ficticia"
    st.session_state.ubicacion = texto(config_excel.get("demo_ubicacion")) or "Sitio ficticio"
    st.session_state.conducta = texto(config_excel.get("demo_conducta")) or "Transporte y decomiso"
    st.session_state.hecho_probado = texto(config_excel.get("demo_hecho_probado"))
    st.session_state.receptor_principal = texto(config_excel.get("demo_receptor_principal"))
    st.session_state.linea_base = texto(config_excel.get("demo_linea_base"))
    st.session_state.cambio_biofisico = texto(config_excel.get("demo_cambio_biofisico"))
    st.session_state.consecuencia = texto(config_excel.get("demo_consecuencia"))
    st.session_state.version_valoracion = texto(config_excel.get("demo_version_valoracion")) or "VDEP-1"
    st.session_state.responsable = texto(config_excel.get("demo_responsable")) or "Equipo de demostración"
    factores = texto(config_excel.get("demo_gravedad_factores"))
    st.session_state.gravedad_factores = [f.strip() for f in factores.split("|") if f.strip()]
    st.session_state.gravedad_notas = texto(config_excel.get("demo_gravedad_notas"))
    st.session_state.revision_causal = True
    st.session_state.revision_incertidumbre = True
    st.session_state.revision_doble = True
    st.session_state.permitir_agregacion_ui = texto(
        config_excel.get("demo_permitir_agregacion")
    ).lower() in {"sí", "si", "s", "true", "1", "yes"}
    reiniciar_multas()
    st.session_state.demostracion_activa = True
    st.session_state.editor_version += 1


def cargar_caso_aplicado(
    id_caso: str,
    casos: list[dict],
    receptores: list[dict],
    costos: list[dict],
    variables: list[dict],
) -> None:
    caso = next(c for c in casos if texto(c.get("ID_CASO")) == id_caso)
    receptores_caso = sorted(
        [r for r in receptores if texto(r.get("ID_CASO")) == id_caso],
        key=lambda r: numero(r.get("ORDEN"), 9999),
    )
    costos_caso = sorted(
        [c for c in costos if texto(c.get("ID_CASO")) == id_caso],
        key=lambda c: numero(c.get("ORDEN_EN_CASO"), 9999),
    )
    variables_caso = sorted(
        [v for v in variables if texto(v.get("ID_CASO")) == id_caso],
        key=lambda v: numero(v.get("ORDEN"), 9999),
    )
    st.session_state.vida_df = pd.DataFrame(
        [fila_receptor_desde_caso(r) for r in receptores_caso]
    )
    st.session_state.servicios_df = pd.DataFrame([fila_servicio_vacia()])
    st.session_state.costos_df = pd.DataFrame(
        [fila_costo_desde_referencia(c) for c in costos_caso]
    )
    st.session_state.variables_df = pd.DataFrame(variables_caso)
    st.session_state.nombre_caso = texto(caso.get("ID_CASO"))
    st.session_state.autoridad = texto(caso.get("AUTORIDAD"))
    st.session_state.ubicacion = texto(caso.get("UBICACION"))
    st.session_state.conducta = texto(caso.get("CONDUCTA_EVENTO"))
    st.session_state.hecho_probado = texto(caso.get("HECHO_PROBADO"))
    st.session_state.receptor_principal = texto(caso.get("RECEPTOR_PRINCIPAL"))
    st.session_state.linea_base = texto(caso.get("LINEA_BASE"))
    st.session_state.cambio_biofisico = texto(caso.get("CAMBIO_BIOFISICO"))
    st.session_state.consecuencia = texto(caso.get("CONSECUENCIA"))
    st.session_state.version_valoracion = "VDEP-1"
    st.session_state.responsable = "Equipo de prueba VDEP"
    factores = texto(caso.get("GRAVEDAD_FACTORES"))
    st.session_state.gravedad_factores = [f.strip() for f in factores.split("|") if f.strip()]
    st.session_state.gravedad_notas = texto(caso.get("GRAVEDAD_NOTAS"))
    st.session_state.revision_causal = True
    st.session_state.revision_incertidumbre = True
    st.session_state.revision_doble = True
    st.session_state.permitir_agregacion_ui = texto(caso.get("PERMITIR_AGREGACION")).lower() in {
        "sí", "si", "s", "true", "1", "yes"
    }
    st.session_state.demostracion_activa = True
    st.session_state.caso_aplicado_id = id_caso
    st.session_state.caso_aplicado_fuente = texto(caso.get("FUENTE_CITA"))
    st.session_state.control_doble_caso = texto(caso.get("CONTROL_DOBLE_CONTEO"))
    st.session_state.cambio_vdtc_caso = texto(caso.get("QUE_CAMBIA_VDTC"))
    st.session_state.totales_publicados = {
        "bajo": numero(caso.get("TOTAL_BAJO")),
        "central": numero(caso.get("TOTAL_CENTRAL")),
        "alto": numero(caso.get("TOTAL_ALTO")),
    }
    reiniciar_multas()
    st.session_state.moneda_modelo_ui = texto(caso.get("MONEDA")) or "CRC"
    st.session_state.anio_base_ui = int(numero(caso.get("ANIO_BASE"), 2026))
    st.session_state.editor_version += 1


def limpiar_caso() -> None:
    st.session_state.vida_df = pd.DataFrame(
        columns=[
            "id_referencia", "especie_grupo", "cantidad", "tipo_afectacion", "funcion_ecologica",
            "nexo_causal", "evidencia", "fuente_expediente", "notas",
        ]
    )
    st.session_state.servicios_df = pd.DataFrame([fila_servicio_vacia()])
    st.session_state.costos_df = pd.DataFrame([fila_costo_vacia()])
    st.session_state.variables_df = pd.DataFrame()
    st.session_state.nombre_caso = ""
    st.session_state.autoridad = ""
    st.session_state.ubicacion = ""
    st.session_state.conducta = ""
    st.session_state.hecho_probado = ""
    st.session_state.receptor_principal = ""
    st.session_state.linea_base = ""
    st.session_state.cambio_biofisico = ""
    st.session_state.consecuencia = ""
    st.session_state.version_valoracion = "VDEP-1"
    st.session_state.responsable = ""
    st.session_state.gravedad_factores = []
    st.session_state.gravedad_notas = ""
    st.session_state.revision_causal = False
    st.session_state.revision_incertidumbre = False
    st.session_state.revision_doble = False
    st.session_state.permitir_agregacion_ui = False
    st.session_state.demostracion_activa = False
    st.session_state.caso_aplicado_id = ""
    st.session_state.caso_aplicado_fuente = ""
    st.session_state.control_doble_caso = ""
    st.session_state.cambio_vdtc_caso = ""
    st.session_state.totales_publicados = {}
    reiniciar_multas()
    st.session_state.editor_version += 1


def moneda(valor: float, codigo: str) -> str:
    return f"{codigo} {valor:,.2f}"


inicializar_estado()

with st.sidebar:
    st.header("Base de referencia")
    archivo = st.file_uploader(
        "Libro Excel ESVD (opcional)",
        type=["xlsx"],
        help="Si no carga otro archivo, se usa la plantilla incluida en el proyecto.",
    )
    try:
        contenido_libro = archivo.getvalue() if archivo else LIBRO_PREDETERMINADO.read_bytes()
        (
            config_excel,
            parametros,
            especies_referencia,
            costos_referencia,
            casos_vdep,
            receptores_vdep,
            variables_vdep,
            multas_referencia,
        ) = leer_referencia(contenido_libro)
        st.success(
            "Libro válido: "
            f"{len(especies_referencia)} especie(s), {len(parametros)} servicio(s) y "
            f"{len(costos_referencia)} componente(s); {len(casos_vdep)} caso(s) aplicado(s) y "
            f"{len(multas_referencia)} multa(s) catalogada(s)."
        )
    except Exception as exc:
        st.error(f"No se pudo leer el libro: {exc}")
        config_excel, parametros, especies_referencia, costos_referencia = {}, [], [], []
        casos_vdep, receptores_vdep, variables_vdep = [], [], []
        multas_referencia = []
    modo_demostracion = bool(casos_vdep) or bool(texto(config_excel.get("demo_id_caso"))) or any(
        "INCLUIR_CASO_DEMO" in fila
        for fila in [*parametros, *especies_referencia, *costos_referencia]
    )
    with st.expander("¿Qué hace este archivo?"):
        st.write(
            "Conserva la moneda, tasas, catálogos, fuentes y valores unitarios. "
            "La aplicación recalcula los valores normalizados y no depende de fórmulas guardadas por Excel."
        )
    st.divider()
    st.subheader("Ejemplos aplicados")
    if casos_vdep:
        opciones_caso = {
            f"Ejemplo {int(numero(c.get('NUMERO_EJEMPLO')))} — {texto(c.get('NOMBRE_CASO'))}": texto(c.get("ID_CASO"))
            for c in casos_vdep
        }
        seleccion_caso = st.selectbox(
            "Caso del Producto 2.1.2",
            list(opciones_caso),
            index=0,
        )
        st.caption("Carga receptores, variables biofísicas, componentes monetarios y notas del caso seleccionado.")
        if st.button("Cargar ejemplo aplicado", use_container_width=True):
            cargar_caso_aplicado(
                opciones_caso[seleccion_caso],
                casos_vdep,
                receptores_vdep,
                costos_referencia,
                variables_vdep,
            )
            st.rerun()
    else:
        st.caption("Este libro no contiene la tabla CASOS_VDEP.")
        if st.button(
            "Cargar caso demostrativo anterior",
            use_container_width=True,
            disabled=not (modo_demostracion and (parametros or especies_referencia or costos_referencia)),
        ):
            cargar_caso_demostrativo(config_excel, parametros, especies_referencia, costos_referencia)
            st.rerun()
    if st.button("Limpiar caso", use_container_width=True):
        limpiar_caso()
        st.rerun()

if modo_demostracion:
    st.warning(
        "DATOS DIDÁCTICOS. El Producto 2.1.2 indica que todos los hechos, montos, tamaños de muestra y parámetros de sus ejemplos son ficticios. "
        "Sirven para probar el instrumento y no son tarifas oficiales."
    )

if not texto(st.session_state.moneda_modelo_ui):
    st.session_state.moneda_modelo_ui = texto(config_excel.get("moneda_modelo")) or "CRC"
if not st.session_state.anio_base_ui:
    st.session_state.anio_base_ui = int(numero(config_excel.get("anio_base"), 2026))
if not st.session_state.salario_base_7317:
    st.session_state.salario_base_7317 = numero(config_excel.get("salario_base_ley_7337"), 462200)
ids_multas_referencia = {texto(fila.get("ID_MULTA")) for fila in multas_referencia}
ids_multas_estado = (
    set(st.session_state.multas_df.get("id_multa", pd.Series(dtype=str)).astype(str))
    if not st.session_state.multas_df.empty
    else set()
)
if ids_multas_referencia and ids_multas_referencia != ids_multas_estado:
    st.session_state.multas_df = pd.DataFrame(
        [fila_multa_desde_referencia(fila) for fila in multas_referencia]
    )
elif not ids_multas_referencia and ids_multas_estado:
    st.session_state.multas_df = pd.DataFrame()


tab_caso, tab_vida, tab_servicios, tab_costos, tab_gravedad, tab_multas, tab_resultados = st.tabs(
    [
        "1. Expediente",
        "2. Hecho y receptor",
        "3. Servicios",
        "4. Costos y reparación",
        "5. Gravedad y revisión",
        "6. Multas Ley 7317",
        "7. Resultado VDEP",
    ]
)

with tab_caso:
    st.subheader("Identifique el expediente")
    st.info(
        "Esta aplicación produce una valoración del daño para efectos procesales (VDEP). Puede usar datos del expediente "
        "y referencias históricas mientras el caso, el rescate o la restauración siguen abiertos."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        nombre_caso = st.text_input("Nombre o código del caso", placeholder="Ej.: Expediente TVS-2026-001", key="nombre_caso")
        autoridad = st.text_input("Autoridad o institución", placeholder="Ej.: SINAC, TAA, Fiscalía", key="autoridad")
        ubicacion = st.text_input("Ubicación", placeholder="Cantón, área protegida o coordenadas", key="ubicacion")
    with c2:
        fecha_evento = st.date_input("Fecha del evento o fecha de referencia")
        conducta = st.text_input(
            "Conducta o evento",
            placeholder="Extracción, transporte, tenencia, comercio u otro",
            key="conducta",
        )
        moneda_modelo = st.text_input("Moneda del resultado", key="moneda_modelo_ui")
    with c3:
        version_valoracion = st.text_input("Versión de la valoración", key="version_valoracion")
        responsable = st.text_input("Persona o equipo responsable", key="responsable")
        anio_base = st.number_input("Año base de precios", min_value=1990, max_value=2100, key="anio_base_ui")
        permitir_agregacion = st.checkbox(
            "Autorizar subtotal A1+A2+B+C+D+E",
            key="permitir_agregacion_ui",
            help="Active solo después de revisar solapamientos y doble conteo.",
        )
    with st.expander("Supuestos económicos avanzados"):
        a1, a2, a3, a4 = st.columns(4)
        tasa_baja = a1.number_input("Tasa escenario bajo", 0.0, 0.50, numero(config_excel.get("tasa_descuento_baja"), 0.05), 0.005, format="%.3f")
        tasa_central = a2.number_input("Tasa escenario central", 0.0, 0.50, numero(config_excel.get("tasa_descuento_central"), 0.03), 0.005, format="%.3f")
        tasa_alta = a3.number_input("Tasa escenario alto", 0.0, 0.50, numero(config_excel.get("tasa_descuento_alta"), 0.01), 0.005, format="%.3f")
        horizonte = a4.number_input("Horizonte máximo (años)", 1, 200, int(numero(config_excel.get("horizonte_maximo_anios"), 30)))
        st.caption("Valores predeterminados operativos; deben justificarse en el informe técnico.")

with tab_vida:
    st.subheader("Describa el hecho, el receptor y el cambio")
    st.caption("Complete la cadena causal antes de agregar valores monetarios.")
    cc1, cc2 = st.columns(2)
    with cc1:
        hecho_probado = st.text_area(
            "Qué ocurrió y qué está probado",
            placeholder="Resuma actas, peritajes, fotografías u otros hechos verificados.",
            key="hecho_probado",
        )
        receptor_principal = st.text_area(
            "Receptor afectado",
            placeholder="Individuo, lote, población, hábitat, servicio, persona o institución.",
            key="receptor_principal",
        )
        linea_base = st.text_area(
            "Línea base o situación sin el hecho",
            placeholder="Explique qué habría ocurrido razonablemente sin el evento.",
            key="linea_base",
        )
    with cc2:
        cambio_biofisico = st.text_area(
            "Cambio causado",
            placeholder="Muerte, lesión, ausencia, pérdida reproductiva, cambio funcional o costo adicional.",
            key="cambio_biofisico",
        )
        consecuencia = st.text_area(
            "Consecuencia y respuesta necesaria",
            placeholder="Pérdida ecológica, cuidado, actuación pública, restauración u otro efecto.",
            key="consecuencia",
        )
        st.markdown(
            "**Cadena mínima:** evento → receptor → cambio → consecuencia → cuenta y método."
        )

    st.divider()
    st.subheader("Inventario de vida silvestre")
    st.write(
        "Seleccione una referencia para autocompletar el inventario y una línea monetaria A1 o A2. "
        "También puede agregar o editar filas manualmente."
    )
    if especies_referencia:
        grupos = sorted({texto(e.get("GRUPO_TAXONOMICO")) for e in especies_referencia if texto(e.get("GRUPO_TAXONOMICO"))})
        v1, v2 = st.columns([2, 1])
        filtro_grupo = v1.selectbox("Grupo taxonómico", ["Todos", *grupos], key="filtro_grupo_especie")
        cantidad_especie = v2.number_input("Cantidad afectada", min_value=0.0, value=1.0, step=1.0)
        filtradas = [
            e for e in especies_referencia
            if filtro_grupo == "Todos" or texto(e.get("GRUPO_TAXONOMICO")) == filtro_grupo
        ]
        opciones_especie = {
            f"{e['ID_REFERENCIA']} — {e['ESPECIE_GRUPO']} — {e['TIPO_AFECTACION']}": e
            for e in filtradas
        }
        seleccion_especie = st.selectbox(
            "Especie y tipo de afectación",
            list(opciones_especie),
            index=None,
            placeholder="Seleccione una especie o receptor de referencia",
        )
        if seleccion_especie:
            e = opciones_especie[seleccion_especie]
            st.caption(
                f"Autocompletará Cuenta {texto(e.get('CUENTA')) or 'A1'}: "
                f"{moneda_modelo} {numero(e.get('VALOR_BAJO_USD')):,.2f} / "
                f"{numero(e.get('VALOR_CENTRAL_USD')):,.2f} / "
                f"{numero(e.get('VALOR_ALTO_USD')):,.2f} por {texto(e.get('UNIDAD'))}."
            )
        if st.button("Añadir especie y valoración", disabled=seleccion_especie is None):
            registro, costo = filas_especie_desde_referencia(
                opciones_especie[seleccion_especie], cantidad_especie
            )
            agregar_fila("vida_df", registro, ("especie_grupo",))
            agregar_fila("costos_df", costo, ("concepto",))
            st.session_state.demostracion_activa = st.session_state.demostracion_activa or texto(
                opciones_especie[seleccion_especie].get("ID_REFERENCIA")
            ).startswith(("ESP-DEMO-", "ESP-VDEP-"))
            st.session_state.editor_version += 1
            st.rerun()
    else:
        st.info("No hay referencias de especies en el libro. Puede completar el inventario manualmente.")
    st.session_state.vida_df = st.data_editor(
        st.session_state.vida_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "id_referencia": st.column_config.TextColumn("ID referencia", disabled=True),
            "especie_grupo": st.column_config.TextColumn("Especie o grupo", required=True),
            "cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0),
            "tipo_afectacion": st.column_config.SelectboxColumn("Afectación", options=["Mortalidad", "Extracción", "Lesión", "Desplazamiento", "Pérdida reproductiva", "Hábitat", "Otra"]),
            "funcion_ecologica": st.column_config.TextColumn("Función ecológica afectada"),
            "nexo_causal": st.column_config.SelectboxColumn("Nexo causal", options=["Sí", "No"]),
            "evidencia": st.column_config.SelectboxColumn("Evidencia", options=["A", "B", "C", "D", "E", "X"]),
            "fuente_expediente": st.column_config.TextColumn("Fuente / expediente"),
            "notas": st.column_config.TextColumn("Notas"),
        },
        key=f"editor_vida_{st.session_state.editor_version}",
    )
    if not st.session_state.variables_df.empty:
        with st.expander("Variables biofísicas y no monetarias del ejemplo cargado", expanded=True):
            st.dataframe(st.session_state.variables_df, use_container_width=True, hide_index=True)

with tab_servicios:
    st.subheader("Pérdida de servicios ecosistémicos (Cuenta B)")
    st.write(
        "Seleccione un parámetro del Excel. La aplicación autocompleta el rango unitario y, en esta versión de demostración, "
        "también carga cantidades, pérdida y recuperación didácticas que puede modificar."
    )
    if parametros:
        ecosistemas = sorted({texto(p.get("ECOSISTEMA")) for p in parametros if texto(p.get("ECOSISTEMA"))})
        filtro_ecosistema = st.selectbox("Ecosistema", ["Todos", *ecosistemas], key="filtro_ecosistema")
        parametros_filtrados = [
            p for p in parametros
            if filtro_ecosistema == "Todos" or texto(p.get("ECOSISTEMA")) == filtro_ecosistema
        ]
        opciones = {
            f"{p['ID_PARAMETRO']} — {p['SERVICIO_ECOSISTEMICO']} ({p['UNIDAD_BASE']}) [{p['ESTADO_PARAMETRO']}]": p
            for p in parametros_filtrados
        }
        seleccion = st.selectbox("Parámetro del libro", list(opciones), index=None, placeholder="Seleccione un valor ESVD/comparable")
        if seleccion:
            p = opciones[seleccion]
            st.caption(
                "Autocompletará: "
                f"{moneda_modelo} {numero(p.get('VALOR_BAJO_NORMALIZADO')):,.2f} / "
                f"{numero(p.get('VALOR_CENTRAL_NORMALIZADO')):,.2f} / "
                f"{numero(p.get('VALOR_ALTO_NORMALIZADO')):,.2f} por {texto(p.get('UNIDAD_BASE'))}."
            )
        if st.button("Añadir parámetro a la evaluación", disabled=seleccion is None):
            agregar_fila(
                "servicios_df",
                fila_servicio_desde_parametro(opciones[seleccion]),
                ("servicio", "id_parametro"),
            )
            st.session_state.demostracion_activa = st.session_state.demostracion_activa or texto(
                opciones[seleccion].get("ID_PARAMETRO")
            ).startswith(("ESVD-DEMO-", "VDEP-"))
            st.session_state.editor_version += 1
            st.rerun()
    else:
        st.info("El libro no contiene parámetros completos. Puede llenar manualmente los valores unitarios y citar su fuente en la tabla.")

    columnas_servicio = {
        "id_parametro": st.column_config.TextColumn("ID parámetro", help="Opcional si el valor es manual."),
        "servicio": st.column_config.TextColumn("Servicio ecosistémico", required=True),
        "unidad_base": st.column_config.TextColumn("Unidad del valor", help="Debe corresponder con las unidades afectadas."),
        "unidades_afectadas": st.column_config.NumberColumn("Unidades afectadas", min_value=0.0, format="%.2f"),
        "valor_unitario_bajo": st.column_config.NumberColumn("Valor unitario bajo", min_value=0.0, format="%.2f"),
        "valor_unitario_central": st.column_config.NumberColumn("Valor unitario central", min_value=0.0, format="%.2f"),
        "valor_unitario_alto": st.column_config.NumberColumn("Valor unitario alto", min_value=0.0, format="%.2f"),
        "perdida_inicial_bajo": st.column_config.NumberColumn("Pérdida inicial baja", min_value=0.0, max_value=1.0, format="%.0f%%"),
        "perdida_inicial_central": st.column_config.NumberColumn("Pérdida inicial central", min_value=0.0, max_value=1.0, format="%.0f%%"),
        "perdida_inicial_alto": st.column_config.NumberColumn("Pérdida inicial alta", min_value=0.0, max_value=1.0, format="%.0f%%"),
        "recuperacion_bajo": st.column_config.NumberColumn("Recuperación baja (años)", min_value=0, step=1),
        "recuperacion_central": st.column_config.NumberColumn("Recuperación central (años)", min_value=0, step=1),
        "recuperacion_alto": st.column_config.NumberColumn("Recuperación alta (años)", min_value=0, step=1),
        "perfil_recuperacion": st.column_config.SelectboxColumn("Perfil", options=["Lineal", "Constante", "Inmediata"]),
        "evidencia": st.column_config.SelectboxColumn("Evidencia del caso", options=["A", "B", "C", "D", "E", "X"]),
        "evidencia_parametro": st.column_config.TextColumn("Evidencia del parámetro", disabled=True),
        "comparabilidad": st.column_config.SelectboxColumn("Comparabilidad", options=["Alta", "Media", "Baja"]),
        "nexo_causal": st.column_config.SelectboxColumn("Nexo causal", options=["Sí", "No"]),
        "beneficiarios": st.column_config.TextColumn("Beneficiarios"),
        "fuente": st.column_config.TextColumn("Fuente / URL"),
        "tipo_fuente": st.column_config.SelectboxColumn(
            "Tipo de fuente",
            options=["Dato del expediente", "Estudio local", "Base histórica comparable", "Transferencia de valor unitario", "Proxy / supuesto"],
        ),
        "estado_dato": st.column_config.SelectboxColumn("Estado del dato", options=["Observado", "Estimado"]),
        "n_referencia": st.column_config.TextColumn("Número de casos u observaciones"),
        "estadistico": st.column_config.TextColumn("Estadístico", help="Mediana, media, rango u otro."),
        "periodo_referencia": st.column_config.TextColumn("Periodo de la referencia"),
        "grupo_doble_conteo": st.column_config.TextColumn("Grupo de doble conteo", help="Use el mismo código cuando dos líneas podrían medir la misma pérdida."),
    }
    st.session_state.servicios_df = st.data_editor(
        st.session_state.servicios_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=columnas_servicio,
        key=f"editor_servicios_{st.session_state.editor_version}",
    )
    with st.expander("Cómo se calcula la Cuenta B"):
        st.latex(r"VP = \sum_t \frac{unidades\ afectadas \times pérdida_t \times valor\ unitario}{(1+tasa)^t}")
        st.write("El perfil lineal reduce la pérdida en partes iguales hasta completar la recuperación; el constante mantiene la pérdida durante el periodo indicado.")

with tab_costos:
    st.subheader("Costos directos, efectos conexos y reparación")
    st.write(
        "Seleccione una acción o costo para autocompletar cuenta, unidad, cantidades y rango unitario. "
        "La cuenta R se informa separada del subtotal de daños."
    )
    if costos_referencia:
        cuentas_disponibles = [c for c in ["A1", "A2", "B", "C", "D", "E", "R"] if any(texto(x.get("CUENTA")) == c for x in costos_referencia)]
        filtro_cuenta = st.selectbox("Cuenta del costo", ["Todas", *cuentas_disponibles], key="filtro_cuenta_costo")
        costos_filtrados = [
            c for c in costos_referencia
            if filtro_cuenta == "Todas" or texto(c.get("CUENTA")) == filtro_cuenta
        ]
        opciones_costo = {
            f"{c['ID_REFERENCIA']} — Cuenta {c['CUENTA']} — {c['CONCEPTO']}": c
            for c in costos_filtrados
        }
        seleccion_costo = st.selectbox(
            "Acción, costo o efecto",
            list(opciones_costo),
            index=None,
            placeholder="Seleccione un componente de referencia",
        )
        if seleccion_costo:
            c = opciones_costo[seleccion_costo]
            st.caption(
                "Autocompletará: "
                f"{moneda_modelo} {numero(c.get('COSTO_UNITARIO_BAJO_USD')):,.2f} / "
                f"{numero(c.get('COSTO_UNITARIO_CENTRAL_USD')):,.2f} / "
                f"{numero(c.get('COSTO_UNITARIO_ALTO_USD')):,.2f} por {texto(c.get('UNIDAD'))}."
            )
        if st.button("Añadir costo o acción", disabled=seleccion_costo is None):
            agregar_fila(
                "costos_df",
                fila_costo_desde_referencia(opciones_costo[seleccion_costo]),
                ("concepto",),
            )
            st.session_state.demostracion_activa = st.session_state.demostracion_activa or texto(
                opciones_costo[seleccion_costo].get("ID_REFERENCIA")
            ).startswith(("CST-DEMO-", "VDEP-"))
            st.session_state.editor_version += 1
            st.rerun()
    else:
        st.info("No hay costos de referencia en el libro. Puede completar las líneas manualmente.")
    st.session_state.costos_df = st.data_editor(
        st.session_state.costos_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "id_referencia": st.column_config.TextColumn("ID referencia", disabled=True),
            "cuenta": st.column_config.SelectboxColumn("Cuenta", options=["A1", "A2", "B", "C", "D", "E", "R"], required=True),
            "concepto": st.column_config.TextColumn("Concepto", required=True),
            "base_calculo": st.column_config.TextColumn("Base de cálculo"),
            "unidad": st.column_config.TextColumn("Unidad"),
            "anio_desde_evento": st.column_config.NumberColumn("Año desde el evento", min_value=0, step=1),
            "cantidad_bajo": st.column_config.NumberColumn("Cantidad baja", min_value=0.0),
            "cantidad_central": st.column_config.NumberColumn("Cantidad central", min_value=0.0),
            "cantidad_alto": st.column_config.NumberColumn("Cantidad alta", min_value=0.0),
            "costo_unitario_bajo": st.column_config.NumberColumn("Costo unitario bajo", min_value=0.0, format="%.2f"),
            "costo_unitario_central": st.column_config.NumberColumn("Costo unitario central", min_value=0.0, format="%.2f"),
            "costo_unitario_alto": st.column_config.NumberColumn("Costo unitario alto", min_value=0.0, format="%.2f"),
            "evidencia": st.column_config.SelectboxColumn("Evidencia", options=["A", "B", "C", "D", "E", "X"]),
            "nexo_causal": st.column_config.SelectboxColumn("Nexo causal", options=["Sí", "No"]),
            "fuente": st.column_config.TextColumn("Factura / fuente / expediente"),
            "tipo_fuente": st.column_config.SelectboxColumn(
                "Tipo de fuente",
                options=["Dato del expediente", "Estudio local", "Base histórica comparable", "Estudio comparable", "Proxy / supuesto"],
            ),
            "estado_dato": st.column_config.SelectboxColumn("Estado del dato", options=["Observado", "Estimado"]),
            "n_referencia": st.column_config.TextColumn("Número de casos u observaciones"),
            "estadistico": st.column_config.TextColumn("Estadístico"),
            "periodo_referencia": st.column_config.TextColumn("Periodo de la referencia"),
            "grupo_doble_conteo": st.column_config.TextColumn("Grupo de doble conteo"),
            "notas": st.column_config.TextColumn("Notas"),
        },
        key=f"editor_costos_{st.session_state.editor_version}",
    )
    st.caption("Valor presente por línea = cantidad × costo unitario ÷ (1 + tasa) ^ año.")

with tab_gravedad:
    st.subheader("Registre la gravedad y complete la revisión")
    st.write(
        "La capa G conserva circunstancias éticas y jurídicas relevantes. No añade dinero ni aplica multiplicadores automáticos."
    )
    gravedad_factores = st.multiselect(
        "Factores presentes",
        [
            "Muerte o pérdida irreversible",
            "Sufrimiento grave",
            "Intencionalidad",
            "Daño de lenta recuperación",
            "Especial protección",
            "Afectación reproductiva o poblacional",
            "Otro factor jurídicamente relevante",
        ],
        key="gravedad_factores",
    )
    gravedad_notas = st.text_area(
        "Fundamento y evidencia de la capa G",
        placeholder="Explique el factor, la evidencia y su posible relevancia jurídica. No ingrese un porcentaje ni un multiplicador.",
        key="gravedad_notas",
    )
    st.divider()
    st.subheader("Tres confirmaciones antes de usar el subtotal")
    revision_causal = st.checkbox(
        "Revisé la cadena causal y la línea base.", key="revision_causal"
    )
    revision_incertidumbre = st.checkbox(
        "Diferencié datos observados de estimaciones y dejé visibles los rangos.",
        key="revision_incertidumbre",
    )
    revision_doble = st.checkbox(
        "Revisé los grupos de doble conteo, especialmente A2, B y R.", key="revision_doble"
    )
    if permitir_agregacion and not (revision_causal and revision_incertidumbre and revision_doble):
        st.warning("El subtotal está autorizado, pero todavía falta una o más confirmaciones de revisión.")

with tab_multas:
    st.subheader("Multas aplicables de la Ley N.° 7317")
    st.info(
        "Marque únicamente las conductas cuya aplicación haya sido confirmada jurídicamente. "
        "La multa se calcula con el salario base, se mantiene separada del daño ambiental y se suma solo al total final."
    )
    moneda_normalizada = texto(moneda_modelo).strip().upper()
    moneda_es_crc = moneda_normalizada in {"CRC", "COLÓN", "COLONES", "COLONES COSTARRICENSES", "₡"}
    moneda_anterior = st.session_state.get("moneda_multas_anterior")
    if moneda_anterior != moneda_normalizada:
        st.session_state.tipo_cambio_multas = 1.0 if moneda_es_crc else 0.0
        st.session_state.moneda_multas_anterior = moneda_normalizada
    p1, p2, p3 = st.columns(3)
    salario_base_multas = p1.number_input(
        "Salario base Ley 7337 (CRC)",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="salario_base_7317",
        help="Revise este dato cuando el Poder Judicial publique el salario base de un nuevo año.",
    )
    p2.metric("Año del salario base", int(numero(config_excel.get("anio_salario_base"), 2026)))
    if moneda_es_crc:
        tipo_cambio_multas = 1.0
        p3.metric("Conversión", "1 CRC = 1 CRC")
    else:
        tipo_cambio_multas = p3.number_input(
            f"CRC por 1 {moneda_modelo}",
            min_value=0.0,
            step=1.0,
            format="%.4f",
            key="tipo_cambio_multas",
            help=f"Ejemplo: si 1 {moneda_modelo} equivale a 500 CRC, escriba 500.",
        )

    if st.session_state.multas_df.empty:
        st.warning(
            "El Excel de referencia no contiene la hoja MULTAS_7317. Reemplace el archivo por la versión actualizada."
        )
    else:
        st.caption(
            "Casilla marcada = posible multa aplicable. “SB aplicados” define el escenario central; "
            "si ya existe un monto firme, escríbalo en CRC y ese monto sustituirá el central."
        )
        st.session_state.multas_df = st.data_editor(
            st.session_state.multas_df,
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
            column_config={
                "aplica": st.column_config.CheckboxColumn("Aplicar", default=False),
                "id_multa": st.column_config.TextColumn("ID", disabled=True),
                "articulo": st.column_config.TextColumn("Artículo", disabled=True),
                "tipo": st.column_config.TextColumn("Tipo", disabled=True),
                "conducta": st.column_config.TextColumn("Conducta", disabled=True, width="large"),
                "min_sb": st.column_config.NumberColumn("Mín. SB", disabled=True, format="%.2f"),
                "sb_aplicados": st.column_config.NumberColumn("SB aplicados", min_value=0.0, format="%.3f"),
                "max_sb": st.column_config.NumberColumn("Máx. SB", disabled=True, format="%.2f"),
                "monto_firme_crc": st.column_config.NumberColumn("Monto firme CRC", min_value=0.0, format="%.2f"),
                "otras_consecuencias": st.column_config.TextColumn("Otras consecuencias", disabled=True, width="large"),
                "fuente": st.column_config.TextColumn("Fuente oficial", disabled=True, width="large"),
                "observaciones": st.column_config.TextColumn("Observaciones del caso", width="large"),
            },
            key=f"editor_multas_{st.session_state.editor_version}",
        )

    multas_resultado = calcular_multas_7317(
        registros(st.session_state.multas_df),
        salario_base_multas,
        tipo_cambio_multas,
    )
    seleccionadas = len(multas_resultado["detalle"])
    st.write(f"Multas seleccionadas: **{seleccionadas}**")
    r1, r2, r3 = st.columns(3)
    r1.metric("Rango bajo en CRC", moneda(multas_resultado["total_crc"]["bajo"], "CRC"))
    r2.metric("Central o firme en CRC", moneda(multas_resultado["total_crc"]["central"], "CRC"))
    r3.metric("Rango alto en CRC", moneda(multas_resultado["total_crc"]["alto"], "CRC"))
    if multas_resultado["total_moneda"] is not None and not moneda_es_crc:
        st.caption(
            "Convertido a la moneda del resultado: "
            f"{moneda(multas_resultado['total_moneda']['bajo'], moneda_modelo)} / "
            f"{moneda(multas_resultado['total_moneda']['central'], moneda_modelo)} / "
            f"{moneda(multas_resultado['total_moneda']['alto'], moneda_modelo)}."
        )
    if multas_resultado["advertencias"]:
        st.warning("\n".join(f"• {mensaje}" for mensaje in multas_resultado["advertencias"]))
    revision_multas = st.checkbox(
        "La selección y la cuantía de las multas fueron revisadas jurídicamente.",
        key="revision_multas",
        disabled=seleccionadas == 0,
    )
    st.caption(
        "Esta pestaña es una ayuda de registro y cálculo. Si marca varias filas, la aplicación las suma aritméticamente; "
        "la revisión jurídica debe confirmar si realmente son acumulables, si la multa es alternativa a prisión y qué consecuencias no monetarias proceden."
    )

config_calculo = {
    "tasa_descuento_baja": tasa_baja,
    "tasa_descuento_central": tasa_central,
    "tasa_descuento_alta": tasa_alta,
    "horizonte_maximo_anios": horizonte,
}
resultado = calcular_modelo(registros(st.session_state.servicios_df), registros(st.session_state.costos_df), config_calculo)
caso = {
    "nombre_caso": nombre_caso,
    "tipo_valoracion": "VDEP - valoración del daño para efectos procesales",
    "autoridad": autoridad,
    "ubicacion": ubicacion,
    "fecha_evento": fecha_evento.isoformat(),
    "conducta": conducta,
    "hecho_probado": hecho_probado,
    "receptor_principal": receptor_principal,
    "linea_base": linea_base,
    "cambio_biofisico": cambio_biofisico,
    "consecuencia": consecuencia,
    "version_valoracion": version_valoracion,
    "responsable": responsable,
    "gravedad_factores": ", ".join(gravedad_factores),
    "gravedad_notas": gravedad_notas,
    "revision_causal": revision_causal,
    "revision_incertidumbre": revision_incertidumbre,
    "revision_doble_conteo": revision_doble,
    "revision_multas_ley_7317": revision_multas,
    "moneda": moneda_modelo,
    "anio_base": anio_base,
    "salario_base_ley_7337_crc": salario_base_multas,
    "crc_por_unidad_moneda": tipo_cambio_multas,
    "permitir_agregacion": permitir_agregacion,
    "caso_aplicado_id": st.session_state.caso_aplicado_id,
    "fuente_caso_aplicado": st.session_state.caso_aplicado_fuente,
    "control_doble_conteo_caso": st.session_state.control_doble_caso,
    "sustituciones_vdtc": st.session_state.cambio_vdtc_caso,
    **config_calculo,
}

with tab_resultados:
    st.subheader("Resultado VDEP")
    if st.session_state.demostracion_activa:
        st.warning("Resultado didáctico del Producto 2.1.2. No constituye tarifa oficial ni sustituye la validación técnica del expediente.")
    st.caption(
        "El rango combina datos observados con estimaciones históricas o transferidas. Cada línea conserva su fuente, evidencia y estado."
    )
    campos_minimos = {
        "código del caso": nombre_caso,
        "autoridad": autoridad,
        "hecho probado": hecho_probado,
        "receptor": receptor_principal,
        "línea base": linea_base,
        "cambio": cambio_biofisico,
        "consecuencia": consecuencia,
        "responsable": responsable,
    }
    faltantes_minimos = [nombre for nombre, valor in campos_minimos.items() if not texto(valor)]
    revisiones_pendientes = not (revision_causal and revision_incertidumbre and revision_doble)
    multas_pendientes = bool(multas_resultado["detalle"]) and not revision_multas
    if faltantes_minimos or revisiones_pendientes or multas_pendientes:
        partes = []
        if faltantes_minimos:
            partes.append("Faltan: " + ", ".join(faltantes_minimos))
        if revisiones_pendientes:
            partes.append("Faltan confirmaciones de revisión en la pestaña 5")
        if multas_pendientes:
            partes.append("Falta la revisión jurídica de las multas en la pestaña 6")
        st.warning("Resultado incompleto para revisión procesal. " + ". ".join(partes) + ".")
    else:
        st.success("El registro mínimo VDEP está completo. Revise las advertencias antes de usar el resultado.")
    resumen = []
    nombres = {
        "A1": "Pérdida biofísica o poblacional",
        "A2": "Pérdida irreversible y equivalencia individual",
        "B": "Servicios ecosistémicos", "C": "Respuesta pública",
        "D": "Rescate y cuidado", "E": "Efectos conexos", "R": "Reparación / restauración",
    }
    for cuenta in ("A1", "A2", "B", "C", "D", "E", "R"):
        valores = resultado["principal_por_cuenta"][cuenta]
        resumen.append({"Cuenta": cuenta, "Componente": nombres[cuenta], "Bajo": valores["bajo"], "Central": valores["central"], "Alto": valores["alto"]})
    resumen_df = pd.DataFrame(resumen)

    m1, m2, m3 = st.columns(3)
    if permitir_agregacion:
        m1.metric("Total compatible VDEP - Bajo", moneda(resultado["total_compatible"]["bajo"], moneda_modelo))
        m2.metric("Total compatible VDEP - Central", moneda(resultado["total_compatible"]["central"], moneda_modelo))
        m3.metric("Total compatible VDEP - Alto", moneda(resultado["total_compatible"]["alto"], moneda_modelo))
        st.caption(
            "Total compatible = subtotal A1+A2+B+C+D+E + R, únicamente después de revisar compatibilidad y doble conteo. "
            f"Subtotal de daños sin R: {moneda(resultado['subtotal_danos']['bajo'], moneda_modelo)} / "
            f"{moneda(resultado['subtotal_danos']['central'], moneda_modelo)} / "
            f"{moneda(resultado['subtotal_danos']['alto'], moneda_modelo)}."
        )
    else:
        st.info("El subtotal combinado no se muestra porque la agregación no está autorizada. Revise primero los grupos de doble conteo.")

    st.markdown("**Multas y total final**")
    multas_moneda = multas_resultado.get("total_moneda")
    if multas_moneda is not None:
        f1, f2, f3 = st.columns(3)
        f1.metric("Multas Ley 7317 - Bajo", moneda(multas_moneda["bajo"], moneda_modelo))
        f2.metric("Multas Ley 7317 - Central", moneda(multas_moneda["central"], moneda_modelo))
        f3.metric("Multas Ley 7317 - Alto", moneda(multas_moneda["alto"], moneda_modelo))
        if permitir_agregacion:
            total_final = {
                escenario: resultado["total_compatible"][escenario] + multas_moneda[escenario]
                for escenario in ESCENARIOS
            }
            t1, t2, t3 = st.columns(3)
            t1.metric("TOTAL FINAL - Bajo", moneda(total_final["bajo"], moneda_modelo))
            t2.metric("TOTAL FINAL - Central", moneda(total_final["central"], moneda_modelo))
            t3.metric("TOTAL FINAL - Alto", moneda(total_final["alto"], moneda_modelo))
        else:
            st.caption("Las multas se muestran, pero el total final no puede calcularse hasta autorizar la agregación VDEP.")
    else:
        st.warning(
            "Las multas se muestran en CRC, pero no se suman al total final porque falta el tipo de cambio a la moneda del resultado."
        )
        f1, f2, f3 = st.columns(3)
        f1.metric("Multas - Bajo", moneda(multas_resultado["total_crc"]["bajo"], "CRC"))
        f2.metric("Multas - Central", moneda(multas_resultado["total_crc"]["central"], "CRC"))
        f3.metric("Multas - Alto", moneda(multas_resultado["total_crc"]["alto"], "CRC"))
    st.caption(
        "Las multas son una consecuencia jurídica separada. No modifican el valor del daño ambiental; se agregan únicamente en esta línea final."
    )
    st.dataframe(
        resumen_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Bajo": st.column_config.NumberColumn(format=f"{moneda_modelo} %.2f"),
            "Central": st.column_config.NumberColumn(format=f"{moneda_modelo} %.2f"),
            "Alto": st.column_config.NumberColumn(format=f"{moneda_modelo} %.2f"),
        },
    )
    grafica = resumen_df[resumen_df["Cuenta"] != "R"].set_index("Cuenta")[["Bajo", "Central", "Alto"]]
    if grafica.to_numpy().sum() > 0:
        st.bar_chart(grafica)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Reparación / restauración (central)", moneda(resultado["reparacion"]["central"], moneda_modelo))
    with c2:
        st.metric("Líneas exploratorias (central)", moneda(resultado["total_exploratorio"]["central"], moneda_modelo))
    with c3:
        st.metric("Componentes observados", moneda(resultado["por_estado_dato"]["Observado"]["central"], moneda_modelo))
    with c4:
        st.metric("Componentes estimados", moneda(resultado["por_estado_dato"]["Estimado"]["central"], moneda_modelo))
    st.caption(
        "R se muestra separada y solo entra al total compatible tras la revisión. Las líneas exploratorias no se suman. G permanece no monetaria."
    )

    if st.session_state.caso_aplicado_id:
        st.markdown("**Comprobación con el anexo**")
        publicados = st.session_state.totales_publicados
        coincide = all(
            abs(resultado["total_compatible"][e] - numero(publicados.get(e))) < 0.01
            for e in ESCENARIOS
        )
        st.write(
            f"Publicado: {moneda(numero(publicados.get('bajo')), moneda_modelo)} / "
            f"{moneda(numero(publicados.get('central')), moneda_modelo)} / "
            f"{moneda(numero(publicados.get('alto')), moneda_modelo)}."
        )
        if coincide:
            st.success("El cálculo reproduce exactamente el rango del ejemplo seleccionado.")
        else:
            st.warning("El caso fue editado y ya no coincide con el rango publicado en el anexo.")
        if st.session_state.control_doble_caso:
            st.info("Control de doble conteo: " + st.session_state.control_doble_caso)
        if st.session_state.cambio_vdtc_caso:
            st.info("Para una VDTC: " + st.session_state.cambio_vdtc_caso)
        if st.session_state.caso_aplicado_fuente:
            st.caption("Fuente: " + st.session_state.caso_aplicado_fuente)

    if gravedad_factores or gravedad_notas:
        st.markdown("**Capa G de gravedad y equidad**")
        if gravedad_factores:
            st.write(", ".join(gravedad_factores))
        if gravedad_notas:
            st.write(gravedad_notas)

    advertencias_resultado = [*resultado["advertencias"], *multas_resultado["advertencias"]]
    if advertencias_resultado:
        st.warning("\n".join(f"• {a}" for a in sorted(set(advertencias_resultado))))
    else:
        st.success("No se detectaron advertencias automáticas. Aun así, realice revisión técnica y jurídica.")

    with st.expander("Detalle calculado"):
        if resultado["detalle"]:
            st.dataframe(pd.DataFrame(resultado["detalle"]), use_container_width=True, hide_index=True)
        else:
            st.write("Sin líneas calculadas.")

    reporte = crear_reporte_xlsx(
        caso,
        resultado,
        registros(st.session_state.vida_df),
        registros(st.session_state.servicios_df),
        registros(st.session_state.costos_df),
        registros(st.session_state.variables_df),
        multas_resultado,
    )
    paquete_json = json.dumps(
        {
            "caso": caso,
            "vida_silvestre": registros(st.session_state.vida_df),
            "variables_biofisicas": registros(st.session_state.variables_df),
            "servicios": registros(st.session_state.servicios_df),
            "costos": registros(st.session_state.costos_df),
            "multas_ley_7317": multas_resultado,
            "resultado": resultado,
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode("utf-8")
    d1, d2 = st.columns(2)
    d1.download_button("Descargar informe Excel", reporte, "resultado_calculadora_vdep.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    d2.download_button("Descargar datos JSON", paquete_json, "resultado_calculadora_vdep.json", "application/json", use_container_width=True)

st.divider()
st.markdown(
    '<p class="small-note">Herramienta VDEP de apoyo durante un expediente abierto. No sustituye peritaje ecológico o económico, revisión jurídica ni validación de las fuentes.</p>',
    unsafe_allow_html=True,
)

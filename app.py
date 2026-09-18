from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from calculos import ESCENARIOS, calcular_modelo, numero, texto
from excel_io import (
    cargar_libro_referencia,
    crear_reporte_xlsx,
    fila_costo_desde_referencia,
    fila_servicio_desde_parametro,
    filas_especie_desde_referencia,
    seleccionar_filas_demo,
)


BASE_DIR = Path(__file__).resolve().parent
LIBRO_PREDETERMINADO = BASE_DIR / "data" / "Plantilla_Calculadora_ESVD_ES.xlsx"

st.set_page_config(
    page_title="Calculadora procesal VEP",
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
      <h1>Calculadora para efectos procesales</h1>
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
    st.session_state.setdefault("nombre_caso", "")
    st.session_state.setdefault("autoridad", "")
    st.session_state.setdefault("ubicacion", "")
    st.session_state.setdefault("conducta", "")
    st.session_state.setdefault("hecho_probado", "")
    st.session_state.setdefault("receptor_principal", "")
    st.session_state.setdefault("linea_base", "")
    st.session_state.setdefault("cambio_biofisico", "")
    st.session_state.setdefault("consecuencia", "")
    st.session_state.setdefault("version_valoracion", "VEP-1")
    st.session_state.setdefault("responsable", "")
    st.session_state.setdefault("gravedad_factores", [])
    st.session_state.setdefault("gravedad_notas", "")
    st.session_state.setdefault("revision_causal", False)
    st.session_state.setdefault("revision_incertidumbre", False)
    st.session_state.setdefault("revision_doble", False)
    st.session_state.setdefault("permitir_agregacion_ui", False)
    st.session_state.setdefault("demostracion_activa", False)


def agregar_fila(clave: str, fila: dict, campos_contenido: tuple[str, ...]) -> None:
    df = st.session_state[clave]
    primera_vacia = df.empty or (
        len(df) == 1 and not any(texto(df.iloc[0].get(c)) for c in campos_contenido)
    )
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
    st.session_state.nombre_caso = texto(config_excel.get("demo_id_caso")) or "DEMO-VEP-001"
    st.session_state.autoridad = texto(config_excel.get("demo_autoridad")) or "Autoridad ficticia"
    st.session_state.ubicacion = texto(config_excel.get("demo_ubicacion")) or "Sitio ficticio"
    st.session_state.conducta = texto(config_excel.get("demo_conducta")) or "Transporte y decomiso"
    st.session_state.hecho_probado = texto(config_excel.get("demo_hecho_probado"))
    st.session_state.receptor_principal = texto(config_excel.get("demo_receptor_principal"))
    st.session_state.linea_base = texto(config_excel.get("demo_linea_base"))
    st.session_state.cambio_biofisico = texto(config_excel.get("demo_cambio_biofisico"))
    st.session_state.consecuencia = texto(config_excel.get("demo_consecuencia"))
    st.session_state.version_valoracion = texto(config_excel.get("demo_version_valoracion")) or "VEP-1"
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
    st.session_state.demostracion_activa = True
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
    st.session_state.nombre_caso = ""
    st.session_state.autoridad = ""
    st.session_state.ubicacion = ""
    st.session_state.conducta = ""
    st.session_state.hecho_probado = ""
    st.session_state.receptor_principal = ""
    st.session_state.linea_base = ""
    st.session_state.cambio_biofisico = ""
    st.session_state.consecuencia = ""
    st.session_state.version_valoracion = "VEP-1"
    st.session_state.responsable = ""
    st.session_state.gravedad_factores = []
    st.session_state.gravedad_notas = ""
    st.session_state.revision_causal = False
    st.session_state.revision_incertidumbre = False
    st.session_state.revision_doble = False
    st.session_state.permitir_agregacion_ui = False
    st.session_state.demostracion_activa = False
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
        config_excel, parametros, especies_referencia, costos_referencia = leer_referencia(contenido_libro)
        st.success(
            "Libro válido: "
            f"{len(especies_referencia)} especie(s), {len(parametros)} servicio(s) y "
            f"{len(costos_referencia)} costo(s) de referencia."
        )
    except Exception as exc:
        st.error(f"No se pudo leer el libro: {exc}")
        config_excel, parametros, especies_referencia, costos_referencia = {}, [], [], []
    modo_demostracion = bool(texto(config_excel.get("demo_id_caso"))) or any(
        "INCLUIR_CASO_DEMO" in fila
        for fila in [*parametros, *especies_referencia, *costos_referencia]
    )
    with st.expander("¿Qué hace este archivo?"):
        st.write(
            "Conserva la moneda, tasas, catálogos, fuentes y valores unitarios. "
            "La aplicación recalcula los valores normalizados y no depende de fórmulas guardadas por Excel."
        )
    st.divider()
    st.subheader("Demostración")
    st.caption(
        "Carga el caso ficticio de dos pericos en rehabilitación, adaptado del ejemplo metodológico VEP."
    )
    if st.button(
        "Cargar caso demostrativo de pericos",
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
        "VERSIÓN DE DEMOSTRACIÓN. Las especies, montos, ecosistemas, servicios, costos y fuentes del libro son ficticios. "
        "Úselos únicamente para probar el funcionamiento."
    )


tab_caso, tab_vida, tab_servicios, tab_costos, tab_gravedad, tab_resultados = st.tabs(
    [
        "1. Expediente",
        "2. Hecho y receptor",
        "3. Servicios",
        "4. Costos y reparación",
        "5. Gravedad y revisión",
        "6. Resultado VEP",
    ]
)

with tab_caso:
    st.subheader("Identifique el expediente")
    st.info(
        "Esta aplicación produce una valoración para efectos procesales (VEP). Puede usar datos del expediente "
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
        moneda_modelo = st.text_input("Moneda del resultado", value=texto(config_excel.get("moneda_modelo")) or "USD")
    with c3:
        version_valoracion = st.text_input("Versión de la valoración", key="version_valoracion")
        responsable = st.text_input("Persona o equipo responsable", key="responsable")
        anio_base = st.number_input("Año base de precios", min_value=1990, max_value=2100, value=int(numero(config_excel.get("anio_base"), 2026)))
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
            placeholder="Seleccione una especie ficticia",
        )
        if seleccion_especie:
            e = opciones_especie[seleccion_especie]
            st.caption(
                f"Autocompletará Cuenta {texto(e.get('CUENTA')) or 'A1'}: "
                f"USD {numero(e.get('VALOR_BAJO_USD')):,.2f} / "
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
            ).startswith("ESP-DEMO-")
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

with tab_servicios:
    st.subheader("Pérdida de servicios ecosistémicos (Cuenta B)")
    st.write(
        "Seleccione un parámetro del Excel. La aplicación autocompleta el rango unitario y, en esta versión de demostración, "
        "también carga cantidades, pérdida y recuperación ficticias que puede modificar."
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
                f"USD {numero(p.get('VALOR_BAJO_NORMALIZADO')):,.2f} / "
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
            ).startswith("ESVD-DEMO-")
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
        cuentas_disponibles = [c for c in ["A1", "A2", "C", "D", "E", "R"] if any(texto(x.get("CUENTA")) == c for x in costos_referencia)]
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
            placeholder="Seleccione un costo ficticio",
        )
        if seleccion_costo:
            c = opciones_costo[seleccion_costo]
            st.caption(
                "Autocompletará: "
                f"USD {numero(c.get('COSTO_UNITARIO_BAJO_USD')):,.2f} / "
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
            ).startswith("CST-DEMO-")
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
            "cuenta": st.column_config.SelectboxColumn("Cuenta", options=["A1", "A2", "C", "D", "E", "R"], required=True),
            "concepto": st.column_config.TextColumn("Concepto", required=True),
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

config_calculo = {
    "tasa_descuento_baja": tasa_baja,
    "tasa_descuento_central": tasa_central,
    "tasa_descuento_alta": tasa_alta,
    "horizonte_maximo_anios": horizonte,
}
resultado = calcular_modelo(registros(st.session_state.servicios_df), registros(st.session_state.costos_df), config_calculo)
caso = {
    "nombre_caso": nombre_caso,
    "tipo_valoracion": "VEP - valoración para efectos procesales",
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
    "moneda": moneda_modelo,
    "anio_base": anio_base,
    "permitir_agregacion": permitir_agregacion,
    **config_calculo,
}

with tab_resultados:
    st.subheader("Resultado para efectos procesales")
    if st.session_state.demostracion_activa:
        st.warning("Resultado de demostración calculado con datos ficticios. No tiene validez técnica, económica ni jurídica.")
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
    if faltantes_minimos or revisiones_pendientes:
        partes = []
        if faltantes_minimos:
            partes.append("Faltan: " + ", ".join(faltantes_minimos))
        if revisiones_pendientes:
            partes.append("Faltan confirmaciones de revisión en la pestaña 5")
        st.warning("Resultado incompleto para revisión procesal. " + ". ".join(partes) + ".")
    else:
        st.success("El registro mínimo VEP está completo. Revise las advertencias antes de usar el resultado.")
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
        m1.metric("Subtotal de daños - Bajo", moneda(resultado["subtotal_danos"]["bajo"], moneda_modelo))
        m2.metric("Subtotal de daños - Central", moneda(resultado["subtotal_danos"]["central"], moneda_modelo))
        m3.metric("Subtotal de daños - Alto", moneda(resultado["subtotal_danos"]["alto"], moneda_modelo))
    else:
        st.info("El subtotal combinado no se muestra porque la agregación no está autorizada. Revise primero los grupos de doble conteo.")
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
        "R se presenta separada. Las líneas exploratorias no entran al subtotal principal. G se conserva como información no monetaria."
    )

    if gravedad_factores or gravedad_notas:
        st.markdown("**Capa G de gravedad y equidad**")
        if gravedad_factores:
            st.write(", ".join(gravedad_factores))
        if gravedad_notas:
            st.write(gravedad_notas)

    if resultado["advertencias"]:
        st.warning("\n".join(f"• {a}" for a in resultado["advertencias"]))
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
    )
    paquete_json = json.dumps(
        {"caso": caso, "resultado": resultado}, ensure_ascii=False, indent=2, default=str
    ).encode("utf-8")
    d1, d2 = st.columns(2)
    d1.download_button("Descargar informe Excel", reporte, "resultado_calculadora_esvd.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    d2.download_button("Descargar datos JSON", paquete_json, "resultado_calculadora_esvd.json", "application/json", use_container_width=True)

st.divider()
st.markdown(
    '<p class="small-note">Herramienta VEP de apoyo durante un expediente abierto. No sustituye peritaje ecológico o económico, revisión jurídica ni validación de las fuentes.</p>',
    unsafe_allow_html=True,
)

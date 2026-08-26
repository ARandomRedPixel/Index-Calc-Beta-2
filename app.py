from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from calculos import ESCENARIOS, calcular_modelo, numero, texto
from excel_io import cargar_libro_referencia, crear_reporte_xlsx


BASE_DIR = Path(__file__).resolve().parent
LIBRO_PREDETERMINADO = BASE_DIR / "data" / "Plantilla_Calculadora_ESVD_ES.xlsx"

st.set_page_config(
    page_title="Calculadora preliminar ESVD",
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
      <h1>Calculadora preliminar ESVD</h1>
      <p>Daños a la vida silvestre, pérdida de servicios ecosistémicos y costos de reparación.</p>
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
        "grupo_doble_conteo": "",
    }


def fila_costo_vacia() -> dict:
    return {
        "cuenta": "A",
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
        "grupo_doble_conteo": "",
    }


def inicializar_estado():
    if "vida_df" not in st.session_state:
        st.session_state.vida_df = pd.DataFrame(
            columns=[
                "especie_grupo", "cantidad", "tipo_afectacion", "funcion_ecologica",
                "nexo_causal", "evidencia", "fuente_expediente", "notas",
            ]
        )
    if "servicios_df" not in st.session_state:
        st.session_state.servicios_df = pd.DataFrame([fila_servicio_vacia()])
    if "costos_df" not in st.session_state:
        st.session_state.costos_df = pd.DataFrame([fila_costo_vacia()])


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
        config_excel, parametros = leer_referencia(contenido_libro)
        st.success(f"Libro válido: {len(parametros)} parámetro(s) ESVD disponible(s).")
    except Exception as exc:
        st.error(f"No se pudo leer el libro: {exc}")
        config_excel, parametros = {}, []
    with st.expander("¿Qué hace este archivo?"):
        st.write(
            "Conserva la moneda, tasas, catálogos, fuentes y valores unitarios. "
            "La aplicación recalcula los valores normalizados y no depende de fórmulas guardadas por Excel."
        )


tab_caso, tab_vida, tab_servicios, tab_costos, tab_resultados = st.tabs(
    ["1. Caso", "2. Vida silvestre", "3. Servicios", "4. Costos y reparación", "5. Resultados"]
)

with tab_caso:
    st.subheader("Identifique el caso y confirme los supuestos")
    c1, c2, c3 = st.columns(3)
    with c1:
        nombre_caso = st.text_input("Nombre o código del caso", placeholder="Ej.: Expediente TVS-2026-001")
        ubicacion = st.text_input("Ubicación", placeholder="Cantón, área protegida o coordenadas")
    with c2:
        fecha_evento = st.date_input("Fecha del evento o fecha de referencia")
        moneda_modelo = st.text_input("Moneda del resultado", value=texto(config_excel.get("moneda_modelo")) or "USD")
    with c3:
        anio_base = st.number_input("Año base de precios", min_value=1990, max_value=2100, value=int(numero(config_excel.get("anio_base"), 2026)))
        permitir_agregacion = st.checkbox(
            "Autorizar subtotal combinado A+B+C+D+E",
            value=texto(config_excel.get("permitir_agregacion")).lower() in {"sí", "si"},
            help="Active solo después de revisar solapamientos y doble conteo.",
        )
    objetivo = st.text_area("Descripción breve del evento y del daño", placeholder="Qué ocurrió, qué receptores fueron afectados y durante qué periodo.")
    with st.expander("Supuestos económicos avanzados"):
        a1, a2, a3, a4 = st.columns(4)
        tasa_baja = a1.number_input("Tasa escenario bajo", 0.0, 0.50, numero(config_excel.get("tasa_descuento_baja"), 0.05), 0.005, format="%.3f")
        tasa_central = a2.number_input("Tasa escenario central", 0.0, 0.50, numero(config_excel.get("tasa_descuento_central"), 0.03), 0.005, format="%.3f")
        tasa_alta = a3.number_input("Tasa escenario alto", 0.0, 0.50, numero(config_excel.get("tasa_descuento_alta"), 0.01), 0.005, format="%.3f")
        horizonte = a4.number_input("Horizonte máximo (años)", 1, 200, int(numero(config_excel.get("horizonte_maximo_anios"), 30)))
        st.caption("Valores predeterminados operativos; deben justificarse en el informe técnico.")

with tab_vida:
    st.subheader("Inventario del daño a la vida silvestre")
    st.write("Registre los receptores ecológicos y el vínculo causal. Esta tabla documenta el caso; la monetización se hace en las pestañas 3 y 4.")
    st.session_state.vida_df = st.data_editor(
        st.session_state.vida_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "especie_grupo": st.column_config.TextColumn("Especie o grupo", required=True),
            "cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0),
            "tipo_afectacion": st.column_config.SelectboxColumn("Afectación", options=["Mortalidad", "Extracción", "Lesión", "Desplazamiento", "Pérdida reproductiva", "Hábitat", "Otra"]),
            "funcion_ecologica": st.column_config.TextColumn("Función ecológica afectada"),
            "nexo_causal": st.column_config.SelectboxColumn("Nexo causal", options=["Sí", "No"]),
            "evidencia": st.column_config.SelectboxColumn("Evidencia", options=["A", "B", "C", "D", "X"]),
            "fuente_expediente": st.column_config.TextColumn("Fuente / expediente"),
            "notas": st.column_config.TextColumn("Notas"),
        },
        key="editor_vida",
    )

with tab_servicios:
    st.subheader("Pérdida de servicios ecosistémicos (Cuenta B)")
    st.write("Seleccione un parámetro del Excel o escriba una fila manual. La aplicación proyecta la recuperación y descuenta los flujos año por año.")
    if parametros:
        opciones = {
            f"{p['ID_PARAMETRO']} — {p['SERVICIO_ECOSISTEMICO']} ({p['UNIDAD_BASE']}) [{p['ESTADO_PARAMETRO']}]": p
            for p in parametros
        }
        seleccion = st.selectbox("Parámetro del libro", list(opciones), index=None, placeholder="Seleccione un valor ESVD/comparable")
        if st.button("Añadir parámetro a la evaluación", disabled=seleccion is None):
            p = opciones[seleccion]
            nueva = fila_servicio_vacia()
            nueva.update({
                "id_parametro": texto(p.get("ID_PARAMETRO")),
                "servicio": texto(p.get("SERVICIO_ECOSISTEMICO")),
                "unidad_base": texto(p.get("UNIDAD_BASE")),
                "valor_unitario_bajo": numero(p.get("VALOR_BAJO_NORMALIZADO")),
                "valor_unitario_central": numero(p.get("VALOR_CENTRAL_NORMALIZADO")),
                "valor_unitario_alto": numero(p.get("VALOR_ALTO_NORMALIZADO")),
                "evidencia_parametro": texto(p.get("NIVEL_EVIDENCIA")),
                "comparabilidad": texto(p.get("COMPARABILIDAD")) or "Media",
                "beneficiarios": texto(p.get("BENEFICIARIOS")),
                "fuente": texto(p.get("FUENTE_URL_CITA")),
            })
            df = st.session_state.servicios_df
            if len(df) == 1 and not texto(df.iloc[0].get("servicio")):
                st.session_state.servicios_df = pd.DataFrame([nueva])
            else:
                st.session_state.servicios_df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
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
        "evidencia": st.column_config.SelectboxColumn("Evidencia del caso", options=["A", "B", "C", "D", "X"]),
        "evidencia_parametro": st.column_config.TextColumn("Evidencia del parámetro", disabled=True),
        "comparabilidad": st.column_config.SelectboxColumn("Comparabilidad", options=["Alta", "Media", "Baja"]),
        "nexo_causal": st.column_config.SelectboxColumn("Nexo causal", options=["Sí", "No"]),
        "beneficiarios": st.column_config.TextColumn("Beneficiarios"),
        "fuente": st.column_config.TextColumn("Fuente / URL"),
        "grupo_doble_conteo": st.column_config.TextColumn("Grupo de doble conteo", help="Use el mismo código cuando dos líneas podrían medir la misma pérdida."),
    }
    st.session_state.servicios_df = st.data_editor(
        st.session_state.servicios_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=columnas_servicio,
        key="editor_servicios",
    )
    with st.expander("Cómo se calcula la Cuenta B"):
        st.latex(r"VP = \sum_t \frac{unidades\ afectadas \times pérdida_t \times valor\ unitario}{(1+tasa)^t}")
        st.write("El perfil lineal reduce la pérdida en partes iguales hasta completar la recuperación; el constante mantiene la pérdida durante el periodo indicado.")

with tab_costos:
    st.subheader("Costos directos, efectos conexos y reparación")
    st.write("Use una fila por concepto. La cuenta R se informa separada del subtotal de daños.")
    st.session_state.costos_df = st.data_editor(
        st.session_state.costos_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "cuenta": st.column_config.SelectboxColumn("Cuenta", options=["A", "C", "D", "E", "R"], required=True),
            "concepto": st.column_config.TextColumn("Concepto", required=True),
            "unidad": st.column_config.TextColumn("Unidad"),
            "anio_desde_evento": st.column_config.NumberColumn("Año desde el evento", min_value=0, step=1),
            "cantidad_bajo": st.column_config.NumberColumn("Cantidad baja", min_value=0.0),
            "cantidad_central": st.column_config.NumberColumn("Cantidad central", min_value=0.0),
            "cantidad_alto": st.column_config.NumberColumn("Cantidad alta", min_value=0.0),
            "costo_unitario_bajo": st.column_config.NumberColumn("Costo unitario bajo", min_value=0.0, format="%.2f"),
            "costo_unitario_central": st.column_config.NumberColumn("Costo unitario central", min_value=0.0, format="%.2f"),
            "costo_unitario_alto": st.column_config.NumberColumn("Costo unitario alto", min_value=0.0, format="%.2f"),
            "evidencia": st.column_config.SelectboxColumn("Evidencia", options=["A", "B", "C", "D", "X"]),
            "nexo_causal": st.column_config.SelectboxColumn("Nexo causal", options=["Sí", "No"]),
            "fuente": st.column_config.TextColumn("Factura / fuente / expediente"),
            "grupo_doble_conteo": st.column_config.TextColumn("Grupo de doble conteo"),
        },
        key="editor_costos",
    )
    st.caption("Valor presente por línea = cantidad × costo unitario ÷ (1 + tasa) ^ año.")

config_calculo = {
    "tasa_descuento_baja": tasa_baja,
    "tasa_descuento_central": tasa_central,
    "tasa_descuento_alta": tasa_alta,
    "horizonte_maximo_anios": horizonte,
}
resultado = calcular_modelo(registros(st.session_state.servicios_df), registros(st.session_state.costos_df), config_calculo)
caso = {
    "nombre_caso": nombre_caso,
    "ubicacion": ubicacion,
    "fecha_evento": fecha_evento.isoformat(),
    "descripcion": objetivo,
    "moneda": moneda_modelo,
    "anio_base": anio_base,
    "permitir_agregacion": permitir_agregacion,
    **config_calculo,
}

with tab_resultados:
    st.subheader("Resultado preliminar")
    st.caption("Los resultados principales incluyen únicamente líneas con nexo causal y evidencia suficiente. Las líneas exploratorias se muestran por separado.")
    resumen = []
    nombres = {
        "A": "Daño biológico", "B": "Servicios ecosistémicos", "C": "Respuesta pública",
        "D": "Rescate y cuidado", "E": "Efectos conexos", "R": "Reparación / restauración",
    }
    for cuenta in ("A", "B", "C", "D", "E", "R"):
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

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Reparación / restauración (central)", moneda(resultado["reparacion"]["central"], moneda_modelo))
        st.caption("La cuenta R se presenta por separado y no se resta automáticamente del daño.")
    with c2:
        st.metric("Líneas exploratorias (central)", moneda(resultado["total_exploratorio"]["central"], moneda_modelo))
        st.caption("No deben incorporarse al escenario central sin fortalecer evidencia o comparabilidad.")

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
    '<p class="small-note">Herramienta preliminar de apoyo. No sustituye peritaje ecológico o económico, revisión jurídica ni validación de las fuentes.</p>',
    unsafe_allow_html=True,
)


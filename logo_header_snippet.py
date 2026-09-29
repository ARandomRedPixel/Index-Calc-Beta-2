import base64
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).parent / "assets"


def _png_data_uri(path: Path) -> str:
    """Convierte un PNG local en una imagen incrustada para controlar su diseño."""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_institutional_header():
    """Cabecera gráfica para la aplicación VDEP."""
    institutional_logos = _png_data_uri(ASSETS / "institutional_logos.png")

    st.markdown(
        f"""
        <style>
            .vdep-logo-header {{
                width: 100%;
                text-align: center;
                margin: 0 auto 1.1rem auto;
            }}
            .vdep-logo-title {{
                text-align: center;
                margin: 0.2rem auto 0.9rem auto;
                max-width: 980px;
                line-height: 1.22;
            }}
            .vdep-government-card {{
                display: inline-flex;
                justify-content: center;
                align-items: center;
                width: min(560px, calc(100% - 2rem));
                box-sizing: border-box;
                margin: 0 auto;
                padding: 10px 16px;
                background: #ffffff;
                border: 1px solid rgba(15, 45, 70, 0.14);
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(15, 45, 70, 0.08);
            }}
            .vdep-government-logos {{
                display: block;
                width: 100%;
                height: auto;
                margin: 0 auto;
            }}
        </style>
        <div class="vdep-logo-header">
            <h2 class="vdep-logo-title">
                Valoración del daño ambiental por pérdida de biodiversidad
                ocasionada por el tráfico de vida silvestre
            </h2>
            <div class="vdep-government-card">
                <img
                    class="vdep-government-logos"
                    src="{institutional_logos}"
                    alt="Logos de las instituciones participantes"
                />
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_eco_eje_footer():
    """Pie de página centrado con el logotipo de ECO-EJE."""
    eco_eje_logo = _png_data_uri(ASSETS / "eco_eje_logo.png")

    st.markdown(
        f"""
        <style>
            .vdep-eco-footer {{
                width: 100%;
                box-sizing: border-box;
                margin: 2.75rem auto 0 auto;
                padding: 1.15rem 0 0.4rem 0;
                text-align: center;
                border-top: 1px solid rgba(15, 45, 70, 0.14);
            }}
            .vdep-eco-footer img {{
                display: block;
                width: 160px;
                max-width: 46vw;
                height: auto;
                margin: 0 auto;
            }}
        </style>
        <div class="vdep-eco-footer">
            <img src="{eco_eje_logo}" alt="ECO-EJE" />
        </div>
        """,
        unsafe_allow_html=True,
    )


# Llame a render_institutional_header() después de st.set_page_config(...).
# Llame a render_eco_eje_footer() al final de app.py, después de todo el contenido.

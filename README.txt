Parche gráfico para la aplicación Streamlit VDEP

1. Copie la carpeta assets y logo_header_snippet.py al mismo directorio de app.py.
2. Importe las dos funciones:

   from logo_header_snippet import render_institutional_header, render_eco_eje_footer

3. Ejecute render_institutional_header() inmediatamente después de st.set_page_config(...).
4. Ejecute render_eco_eje_footer() como la última instrucción visual de app.py,
   después de todas las secciones, pestañas y resultados del calculador.
5. Confirme visualmente en Streamlit y haga commit/push al repositorio que alimenta Community Cloud.

La cabecera presenta los logotipos institucionales en una tarjeta blanca
centrada, de menor tamaño y adaptable a pantallas pequeñas. El logotipo de
ECO-EJE se presenta centrado al final de la página, separado del contenido por
una línea discreta.

Este parche modifica únicamente la presentación visual; no altera cálculos,
datos ni metodología.

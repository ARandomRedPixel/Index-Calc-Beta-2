# Calculadora preliminar ESVD - versión de demostración

Aplicación Streamlit en español para estimar, con rangos bajo/central/alto:

- daño biológico monetizable (A);
- pérdida de servicios ecosistémicos (B);
- respuesta pública incremental (C);
- rescate, rehabilitación y cuidado (D);
- efectos conexos demostrados (E); y
- reparación, restauración o equivalencia (R), presentada por separado.

La aplicación usa `data/Plantilla_Calculadora_ESVD_ES.xlsx` como base de parámetros. La versión incluida contiene datos completamente ficticios para probar la funcionalidad. También permite cargar una versión actualizada desde la interfaz.

## Prueba rápida

1. Pulse **Cargar caso completo de demostración** en el panel lateral.
2. Revise las especies, servicios y costos que se agregaron automáticamente.
3. Abra **5. Resultados** para ver los rangos en USD de todas las cuentas.
4. Pulse **Limpiar caso** para comenzar otra prueba.

También puede construir un ejemplo paso a paso mediante los desplegables de las pestañas 2, 3 y 4. La selección autocompleta valores unitarios, evidencia, unidades, cantidades demostrativas y fuentes ficticias. Todos esos campos siguen siendo editables para probar escenarios.

El manual completo, con explicación de cada campo y del flujo de cálculo, se incluye en `docs/Manual_de_uso_Calculadora_ESVD.docx`.

## Ejecución local

Requiere Python 3.11 o 3.12.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Publicación desde GitHub

1. Cree un repositorio nuevo en GitHub.
2. Suba **todo el contenido de esta carpeta**, incluida `.streamlit/config.toml` y `data/Plantilla_Calculadora_ESVD_ES.xlsx`.
3. En Streamlit Community Cloud, seleccione **Create app**.
4. Elija el repositorio, la rama y `app.py` como archivo de entrada.
5. En configuración avanzada, seleccione una versión de Python compatible (se recomienda 3.12) y despliegue.

Documentación oficial:

- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies

## Tablas de referencia

El Excel contiene tres tablas leídas por la aplicación:

- `ESPECIES_REFERENCIA`: autocompleta el inventario y una línea monetaria ficticia de Cuenta A.
- `VALORES_ESVD`: autocompleta la pérdida de servicios de Cuenta B.
- `COSTOS_REFERENCIA`: autocompleta costos y acciones de las cuentas A, C, D, E y R.

Mantenga los encabezados y nombres de hoja. En `VALORES_ESVD`, la aplicación recalcula:

`valor normalizado = valor original × factor de moneda × factor de año de precios × factor de transferencia validado`

Si una fila no tiene fuente, unidad, valor central, evidencia o comparabilidad, queda marcada como incompleta. Evidencia C/D o comparabilidad baja se presenta como exploratoria; evidencia X se excluye.

Los registros `DEMO` no constituyen estudios, tarifas, precios de especies ni costos reales. Deben sustituirse por datos validados antes de usar la herramienta fuera de una demostración.

## Pruebas

Desde la raíz del proyecto:

```bash
python -m unittest discover -s tests -v
```

## Alcance

Es una herramienta preliminar de apoyo técnico. No sustituye peritaje ecológico o económico, revisión jurídica, validación de la transferencia de beneficios ni verificación de doble conteo.

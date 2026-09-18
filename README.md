# Calculadora VEP para tráfico de vida silvestre

Aplicación Streamlit en español para preparar una **valoración para efectos procesales (VEP)** mientras un expediente sigue abierto. Organiza hechos del caso, referencias históricas, transferencia de valores, incertidumbre y controles de doble conteo.

La aplicación calcula rangos bajo, central y alto para:

- A1: pérdida biofísica o poblacional;
- A2: pérdida irreversible y equivalencia individual;
- B: servicios ecosistémicos;
- C: respuesta pública incremental;
- D: rescate, rehabilitación y cuidado;
- E: efectos conexos demostrados; y
- R: restauración o equivalencia, mostrada por separado.

La capa G registra gravedad ética y jurídica. No aplica un multiplicador monetario.

## Prueba rápida

1. Pulse **Cargar caso demostrativo de pericos**.
2. Revise las seis pestañas en orden.
3. Abra **6. Resultado VEP** para ver el rango y las advertencias.
4. Pulse **Limpiar caso** para comenzar otra prueba.

El caso reproduce el Ejemplo 1 de la metodología VEP: dos pericos vivos todavía en rehabilitación, 8 animal-días observados, 2 exámenes clínicos y una estancia estimada con 42 casos comparables. Los precios añadidos para operar la interfaz son ficticios; no constituyen tarifas, valores oficiales ni evidencia.

## Archivo de referencia

La aplicación lee `data/Plantilla_Calculadora_ESVD_ES.xlsx`:

- `ESPECIES_REFERENCIA` autocompleta A1 o A2;
- `VALORES_ESVD` autocompleta B;
- `COSTOS_REFERENCIA` autocompleta A1, A2, C, D, E o R.

Cada parámetro puede conservar tipo de fuente, estado observado o estimado, número de casos, estadístico, periodo, evidencia y fuente. Los datos específicos del expediente deben sustituir las referencias cuando estén disponibles.

Las columnas `INCLUIR_CASO_DEMO`, `CANTIDAD_CASO_DEMO` y `ORDEN_CASO_DEMO`, junto con las claves `demo_*` de `CONFIGURACION`, controlan el botón de prueba. Después de instalar esta versión, el caso demostrativo puede cambiarse sustituyendo únicamente el Excel y conservando el mismo nombre y ubicación.

## Reglas del resultado

- Evidencia A, B o C puede entrar al resultado principal si existe nexo causal y comparabilidad suficiente.
- Evidencia D o E, o comparabilidad baja, queda como exploratoria.
- Evidencia X o nexo causal negativo queda excluida.
- R se muestra separada del subtotal de daños.
- A2, B y R requieren una revisión expresa de posibles solapamientos.
- UICN y CITES informan riesgo, recuperación y prioridad. No funcionan como multiplicadores.

## Ejecución

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Los manuales están separados por herramienta:

- `docs/Manual_VEP_Aplicacion_Durante_el_Proceso.docx`: uso de la aplicación mientras el expediente sigue abierto.
- `docs/Manual_VTC_Excel_Despues_del_Hecho.docx`: uso de la plantilla Excel después del hecho.

La valoración técnicamente completa posterior se trabaja en `docs/Plantilla_VTC_Valoracion_Despues_del_Hecho.xlsx`.

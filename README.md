# Calculadora VDEP para tráfico de vida silvestre

Aplicación Streamlit en español para preparar una **Valoración del Daño para Efectos Procesales (VDEP)** mientras un expediente sigue abierto. Organiza hechos del caso, referencias históricas, transferencia de valores, incertidumbre y controles de doble conteo.

La aplicación calcula rangos bajo, central y alto para:

- A1: pérdida biofísica o poblacional;
- A2: pérdida irreversible y equivalencia individual;
- B: servicios ecosistémicos;
- C: respuesta pública incremental;
- D: rescate, rehabilitación y cuidado;
- E: efectos conexos demostrados; y
- R: restauración o equivalencia, mostrada por separado.

La capa G registra gravedad ética y jurídica. No aplica un multiplicador monetario.

La pestaña **Multas Ley 7317** permite marcar las disposiciones aplicables, calcular su rango con el salario base vigente y sumarlo, como línea jurídica separada, al total final.

## Prueba rápida

1. Seleccione uno de los nueve casos del Producto 2.1.2.
2. Pulse **Cargar ejemplo aplicado**.
3. Revise las siete pestañas en orden.
4. Abra **6. Multas Ley 7317** y marque solo las conductas confirmadas por la revisión jurídica.
5. Abra **7. Resultado VDEP** para ver el daño, las multas y el total final.
6. Pulse **Limpiar caso** para comenzar otra prueba.

Los nueve casos reproducen los datos del anexo aplicado: pericos, primate no liberable, lapa reproductora, huevos de tortuga, coral, orquídeas, árbol-nido y polluelos, paquete postal y manglar. El propio documento indica que todos los hechos, montos y parámetros son ficticios; no constituyen tarifas ni valores oficiales.

## Archivo de referencia

La aplicación lee `data/Plantilla_Calculadora_ESVD_ES.xlsx`:

- `ESPECIES_REFERENCIA` autocompleta A1 o A2;
- `VALORES_ESVD` autocompleta B;
- `COSTOS_REFERENCIA` autocompleta A1, A2, B, C, D, E o R;
- `CASOS_VDEP` define el expediente y el rango publicado de cada ejemplo;
- `RECEPTORES_VDEP` carga el inventario físico; y
- `VARIABLES_VDEP` conserva indicadores biofísicos y no monetarios.
- `MULTAS_7317` contiene el catálogo de rangos en salarios base que alimenta las casillas de selección.

Cada parámetro puede conservar tipo de fuente, estado observado o estimado, número de casos, estadístico, periodo, evidencia y fuente. Los datos específicos del expediente deben sustituir las referencias cuando estén disponibles.

Después de instalar esta versión, los ejemplos y catálogos pueden actualizarse sustituyendo únicamente el Excel, siempre que conserve el mismo nombre, hojas y encabezados.

## Reglas del resultado

- Evidencia A, B o C puede entrar al resultado principal si existe nexo causal y comparabilidad suficiente.
- Evidencia D o E, o comparabilidad baja, queda como exploratoria.
- Evidencia X o nexo causal negativo queda excluida.
- R se muestra separada del subtotal de daños y solo se incorpora al total compatible después de la revisión.
- A2, B y R requieren una revisión expresa de posibles solapamientos.
- UICN y CITES informan riesgo, recuperación y prioridad. No funcionan como multiplicadores.
- Las multas no multiplican el daño: se calculan por separado y solo se añaden al cierre monetario.

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

- `docs/Manual_VDEP_Aplicacion_Durante_el_Proceso.docx`: uso de la aplicación mientras el expediente sigue abierto.
- `docs/Manual_VTC_Excel_Despues_del_Hecho.docx`: uso de la plantilla Excel después del hecho.

La valoración técnicamente completa posterior se trabaja en `docs/Plantilla_VTC_Valoracion_Despues_del_Hecho.xlsx`.

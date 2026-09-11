import unittest

from calculos import (
    calcular_costo,
    calcular_modelo,
    calcular_servicio,
    clasificar_linea,
    fracciones_perdida,
    normalizar_valores_esvd,
)


class CalculosESVDTest(unittest.TestCase):
    def setUp(self):
        self.tasas = {"bajo": 0.0, "central": 0.0, "alto": 0.0}

    def test_normalizacion_esvd(self):
        fila = {
            "ID_PARAMETRO": "P1",
            "SERVICIO_ECOSISTEMICO": "Polinización",
            "UNIDAD_BASE": "USD/ha/año",
            "VALOR_BAJO_ORIGINAL": 100,
            "VALOR_CENTRAL_ORIGINAL": 200,
            "VALOR_ALTO_ORIGINAL": 300,
            "FACTOR_CONVERSION_MONEDA": 2,
            "FACTOR_ANIO_PRECIOS": 1.1,
            "FACTOR_TRANSFERENCIA_VALIDADO": 0.5,
            "NIVEL_EVIDENCIA": "B",
            "COMPARABILIDAD": "Media",
            "FUENTE_URL_CITA": "https://example.org",
        }
        salida = normalizar_valores_esvd(fila)
        self.assertAlmostEqual(salida["VALOR_CENTRAL_NORMALIZADO"], 220)
        self.assertEqual(salida["ESTADO_PARAMETRO"], "LISTO")
        fila["NIVEL_EVIDENCIA"] = "C"
        self.assertEqual(normalizar_valores_esvd(fila)["ESTADO_PARAMETRO"], "EXPLORATORIO")

    def test_recuperacion_lineal(self):
        self.assertEqual(fracciones_perdida(0.6, 3, "Lineal", 30), [0.6, 0.4, 0.2])

    def test_servicio_un_anio(self):
        fila = {
            "servicio": "Prueba",
            "unidades_afectadas": 10,
            "valor_unitario_bajo": 200,
            "valor_unitario_central": 200,
            "valor_unitario_alto": 200,
            "perdida_inicial_bajo": 0.2,
            "perdida_inicial_central": 0.5,
            "perdida_inicial_alto": 0.9,
            "recuperacion_bajo": 1,
            "recuperacion_central": 1,
            "recuperacion_alto": 1,
            "perfil_recuperacion": "Lineal",
            "evidencia": "A",
            "nexo_causal": "Sí",
        }
        salida = calcular_servicio(fila, self.tasas, 30)
        self.assertEqual((salida["bajo"], salida["central"], salida["alto"]), (400, 1000, 1800))

    def test_costo_valor_presente(self):
        fila = {
            "cuenta": "C",
            "concepto": "Peritaje",
            "anio_desde_evento": 2,
            "cantidad_bajo": 2,
            "cantidad_central": 2,
            "cantidad_alto": 2,
            "costo_unitario_bajo": 100,
            "costo_unitario_central": 100,
            "costo_unitario_alto": 100,
            "evidencia": "A",
            "nexo_causal": "Sí",
        }
        salida = calcular_costo(fila, {"bajo": 0.1, "central": 0.1, "alto": 0.1})
        self.assertAlmostEqual(salida["central"], 200 / 1.21)

    def test_regla_evidencia(self):
        self.assertEqual(clasificar_linea("A", "Sí"), "principal")
        self.assertEqual(clasificar_linea("C", "Sí"), "exploratoria")
        self.assertEqual(clasificar_linea("A", "No"), "excluida")
        self.assertEqual(clasificar_linea("X", "Sí"), "excluida")

    def test_reparacion_separada(self):
        costo = {
            "cuenta": "R", "concepto": "Restauración", "anio_desde_evento": 0,
            "cantidad_bajo": 1, "cantidad_central": 1, "cantidad_alto": 1,
            "costo_unitario_bajo": 100, "costo_unitario_central": 200, "costo_unitario_alto": 300,
            "evidencia": "A", "nexo_causal": "Sí",
        }
        resultado = calcular_modelo([], [costo], {
            "tasa_descuento_baja": 0, "tasa_descuento_central": 0,
            "tasa_descuento_alta": 0, "horizonte_maximo_anios": 30,
        })
        self.assertEqual(resultado["subtotal_danos"]["central"], 0)
        self.assertEqual(resultado["reparacion"]["central"], 200)


if __name__ == "__main__":
    unittest.main()

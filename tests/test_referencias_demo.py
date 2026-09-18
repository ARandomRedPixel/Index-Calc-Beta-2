import unittest
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from calculos import calcular_modelo
from excel_io import (
    cargar_libro_referencia,
    crear_reporte_xlsx,
    fila_costo_desde_referencia,
    fila_servicio_desde_parametro,
    filas_especie_desde_referencia,
    seleccionar_filas_demo,
)


class ReferenciasDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        libro = Path(__file__).resolve().parents[1] / "data" / "Plantilla_Calculadora_ESVD_ES.xlsx"
        cls.config, cls.parametros, cls.especies, cls.costos = cargar_libro_referencia(libro)

    def test_catalogos_ficticios_basados_en_ejemplos_metodologicos(self):
        self.assertEqual(len(self.parametros), 8)
        self.assertEqual(len(self.especies), 8)
        self.assertEqual(len(self.costos), 12)
        self.assertTrue(all(str(p["ID_PARAMETRO"]).startswith("ESVD-DEMO-") for p in self.parametros))
        self.assertEqual(self.config["demo_id_caso"], "DEMO-VEP-PERICOS-01")
        self.assertTrue(any("pericos" in str(e["ESPECIE_GRUPO"]).lower() for e in self.especies))

    def test_caso_demo_pericos_respeta_cuentas_y_rango_metodologico(self):
        parametros_demo, parametros_configurados = seleccionar_filas_demo(self.parametros)
        especies_demo, especies_configuradas = seleccionar_filas_demo(self.especies)
        costos_demo, costos_configurados = seleccionar_filas_demo(self.costos)
        self.assertTrue(parametros_configurados)
        self.assertTrue(especies_configuradas)
        self.assertTrue(costos_configurados)
        self.assertEqual(parametros_demo, [])  # El ejemplo 1 no activa la Cuenta B.
        self.assertEqual(len(especies_demo), 1)
        self.assertEqual(len(costos_demo), 5)

        vida, costo_a1 = filas_especie_desde_referencia(
            especies_demo[0], especies_demo[0]["CANTIDAD_CASO_DEMO"]
        )
        self.assertEqual(vida["cantidad"], 2)
        servicios = []
        costos = [costo_a1, *(fila_costo_desde_referencia(c) for c in costos_demo)]

        resultado = calcular_modelo(servicios, costos, self.config)
        self.assertEqual(resultado["principal_por_cuenta"]["A1"]["central"], 0)
        self.assertEqual(resultado["principal_por_cuenta"]["B"]["central"], 0)
        self.assertEqual(resultado["principal_por_cuenta"]["C"], {"bajo": 120, "central": 180, "alto": 260})
        self.assertEqual(resultado["principal_por_cuenta"]["D"], {"bajo": 250, "central": 350, "alto": 520})
        self.assertEqual(resultado["subtotal_danos"], {"bajo": 370, "central": 530, "alto": 780})
        self.assertAlmostEqual(resultado["reparacion"]["central"], 140 / 1.03)
        self.assertEqual(next(c for c in costos_demo if c["ID_REFERENCIA"] == "CST-DEMO-VEP01-D02")["N_CASOS"], 42)

        reporte = crear_reporte_xlsx(
            {"moneda": "USD", "permitir_agregacion": True, "tipo_valoracion": "VEP"},
            resultado,
            [vida],
            servicios,
            costos,
        )
        libro = load_workbook(BytesIO(reporte), read_only=True, data_only=False)
        self.assertIn("RESUMEN", libro.sheetnames)
        self.assertIn("METADATOS", libro.sheetnames)
        self.assertEqual(libro["RESUMEN"]["A2"].value, "A1")
        self.assertEqual(libro["RESUMEN"]["A3"].value, "A2")
        libro.close()


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from calculos import calcular_modelo
from excel_io import (
    cargar_libro_referencia,
    fila_costo_desde_referencia,
    fila_servicio_desde_parametro,
    filas_especie_desde_referencia,
)


class ReferenciasDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        libro = Path(__file__).resolve().parents[1] / "data" / "Plantilla_Calculadora_ESVD_ES.xlsx"
        cls.config, cls.parametros, cls.especies, cls.costos = cargar_libro_referencia(libro)

    def test_catalogos_ficticios_disponibles(self):
        self.assertEqual(len(self.parametros), 12)
        self.assertEqual(len(self.especies), 7)
        self.assertEqual(len(self.costos), 13)
        self.assertTrue(all(str(p["ID_PARAMETRO"]).startswith("ESVD-DEMO-") for p in self.parametros))

    def test_autocompletado_y_resultado_en_todas_las_cuentas(self):
        _, costo_especie = filas_especie_desde_referencia(self.especies[0], 2)
        servicios = [fila_servicio_desde_parametro(self.parametros[0])]
        costos = [costo_especie]
        for cuenta in ("C", "D", "E", "R"):
            referencia = next(c for c in self.costos if c["CUENTA"] == cuenta)
            costos.append(fila_costo_desde_referencia(referencia))

        resultado = calcular_modelo(servicios, costos, self.config)
        for cuenta in ("A", "B", "C", "D", "E", "R"):
            valores = resultado["principal_por_cuenta"][cuenta]
            self.assertGreater(valores["central"], 0, cuenta)
            self.assertLessEqual(valores["bajo"], valores["central"], cuenta)
            self.assertLessEqual(valores["central"], valores["alto"], cuenta)


if __name__ == "__main__":
    unittest.main()

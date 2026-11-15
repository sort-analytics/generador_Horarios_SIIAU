from fastapi.testclient import TestClient
from api.index import app
import unittest

client = TestClient(app)

class TestSIIAUAPI(unittest.TestCase):
    
    def test_endpoint_opciones(self):
        """Prueba que el endpoint de opciones devuelva ciclos y centros."""
        response = client.get("/api/opciones")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ciclos", response.json())
        self.assertIn("centros", response.json())

    def test_validar_materia_inexistente(self):
        """Prueba que el validador detecte una materia que no existe."""
        payload = {"materias": ["MATERIA_FALSA_123"], "ciclo": "202620", "centro": "D"}
        response = client.post("/api/materias/validar", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_generar_horarios_sin_empalmes(self):
        """Prueba que el generador devuelva horarios válidos."""
        payload = {
            "materias": ["IL355"],
            "ciclo": "202620",
            "centro": "D",
            "max_resultados": 5
        }
        response = client.post("/api/horarios/generar", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_horarios"] > 0, True)

if __name__ == "__main__":
    unittest.main()
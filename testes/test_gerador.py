"""Testes do gerador de casos local. Rodar com: python -m unittest discover testes"""
import random
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fabrica"))

import gerador_local  # noqa: E402
import validar  # noqa: E402


class TestGerador(unittest.TestCase):
    def test_300_casos_seguidos_sao_aprovados_e_nao_repetem(self):
        rng = random.Random(42)
        anterior = None
        solucoes = set()
        for _ in range(300):
            caso = gerador_local.gerar_caso(rng, evitar=anterior)
            erros, _ = validar.validar(caso)
            self.assertEqual(erros, [])
            s = caso["solucao"]
            if anterior:
                for k in ("culpado", "arma", "comodo"):
                    self.assertNotEqual(s[k], anterior[k])
                self.assertNotEqual(caso["titulo"], anterior["titulo"])
            anterior = {**s, "titulo": caso["titulo"]}
            solucoes.add((s["culpado"], s["arma"], s["comodo"]))
        self.assertGreater(len(solucoes), 150)   # muita variedade

    def test_abertura_nao_entrega_local_nem_arma(self):
        rng = random.Random(7)
        for _ in range(100):
            caso = gerador_local.gerar_caso(rng)
            texto = caso["enredo"].lower()
            for nome in ("biblioteca", "cozinha", "jardim", "sala de estar", "escritório", "adega",
                         "veneno", "faca", "corda", "revólver", "castiçal", "tesoura"):
                self.assertNotIn(nome, texto)

    def test_todos_os_suspeitos_e_armas_aparecem(self):
        rng = random.Random(3)
        culpados, armas, locais = set(), set(), set()
        for _ in range(200):
            s = gerador_local.gerar_caso(rng)["solucao"]
            culpados.add(s["culpado"]); armas.add(s["arma"]); locais.add(s["comodo"])
        self.assertEqual(len(culpados), 8)
        self.assertEqual(len(armas), 6)
        self.assertEqual(len(locais), 6)


if __name__ == "__main__":
    unittest.main()

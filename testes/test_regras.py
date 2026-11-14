"""Testes das regras do Quem Foi?. Rodar com: python -m unittest discover testes

Tabuleiro de 21 x 17 casas (dados/tabuleiro.json). Portas usadas nos testes:
Biblioteca (4, 5), Escritório (10, 5). Saídas do Saguão: (7, 8) e (13, 8).
"""
import json
import random
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "jogo"))
sys.path.insert(0, str(RAIZ / "fabrica"))

from regras import (SAGUAO, Jogador, Partida, Tabuleiro, casa, comodo)  # noqa: E402
import validar  # noqa: E402

CASO = json.loads((RAIZ / "dados/casos/caso_exemplo.json").read_text(encoding="utf-8"))
PORTA_BIB = casa(4, 5)
PORTA_ESC = casa(10, 5)


def jogadores(n=3):
    cores = [("Ana", "vermelho", "#D4404C"), ("Alisson", "azul", "#4A7FD4"), ("Levi", "verde", "#4FAE6A")]
    return [Jogador(nome, cor, hx) for nome, cor, hx in cores[:n]]


def partida(n=3, seed=1):
    return Partida(CASO, jogadores(n), rng=random.Random(seed))


def colocar(p, jogador, lugar):
    """Põe um jogador num lugar e recomeça a vez dele (para montar situações de teste)."""
    jogador.posicao = lugar
    p.vez = p.jogadores.index(jogador)
    p._inicio_vez()


class TestTabuleiro(unittest.TestCase):
    def setUp(self):
        self.t = Tabuleiro.padrao()

    def test_tamanho_21_por_17(self):
        self.assertEqual((self.t.largura, self.t.altura), (21, 17))
        corredor = [v for v in self.t.vizinhos if v[0] == "casa"]
        self.assertEqual(len(corredor), 154)

    def test_saida_do_saguao_pelos_dois_lados(self):
        d = self.t.destinos(SAGUAO, 1, set())
        self.assertEqual(set(d), {casa(7, 8), casa(13, 8)})

    def test_todos_os_comodos_ficam_a_8_do_saguao(self):
        d = self.t.destinos(SAGUAO, 30, set())
        self.assertEqual({lugar[1]: n for lugar, n in d.items() if lugar[0] == "comodo"},
                         {c: 8 for c in ("l01", "l02", "l03", "l04", "l05", "l06")})
        self.assertFalse([x for x in self.t.destinos(SAGUAO, 6, set()) if x[0] == "comodo"])

    def test_sem_diagonal(self):
        d = self.t.destinos(casa(7, 6), 1, set())
        self.assertEqual(set(d), {casa(6, 6), casa(8, 6), casa(7, 5), casa(7, 7)})

    def test_obstaculos_nao_sao_caminho(self):
        self.assertNotIn(casa(3, 8), self.t.vizinhos)    # Escadaria
        self.assertNotIn(casa(17, 8), self.t.vizinhos)   # Relógio de pêndulo

    def test_casa_ocupada_bloqueia_passagem(self):
        livre = self.t.destinos(casa(0, 5), 2, set())
        self.assertIn(casa(2, 5), livre)
        bloqueado = self.t.destinos(casa(0, 5), 2, {casa(1, 5)})
        self.assertNotIn(casa(2, 5), bloqueado)
        self.assertNotIn(casa(1, 5), bloqueado)

    def test_comodo_ocupado_fica_fechado(self):
        d = self.t.destinos(PORTA_BIB, 1, {comodo("l01")})
        self.assertNotIn(comodo("l01"), d)

    def test_entrar_no_comodo_e_opcional(self):
        d = self.t.destinos(PORTA_BIB, 3, set())
        self.assertIn(comodo("l01"), d)       # pode entrar
        self.assertIn(casa(7, 5), d)          # ou seguir andando

    def test_comodo_nao_e_atalho(self):
        d = self.t.destinos(PORTA_BIB, 6, set())
        self.assertEqual(d[comodo("l01")], 1)

    def test_caminho_casa_a_casa(self):
        c = self.t.caminho(SAGUAO, comodo("l05"), set())
        self.assertEqual(c[0], SAGUAO)
        self.assertEqual(c[-1], comodo("l05"))
        self.assertEqual(len(c) - 1, 8)


class TestVez(unittest.TestCase):
    def test_ordem_sorteada_tem_todos(self):
        ordem, rodadas = Partida.sortear_ordem(jogadores(3), random.Random(7))
        self.assertEqual(sorted(j.nome for j in ordem), ["Alisson", "Ana", "Levi"])
        self.assertTrue(rodadas)

    def test_vez_segue_1_2_3(self):
        p = partida()
        nomes = []
        for _ in range(4):
            nomes.append(p.jogador.nome)
            p.encerrar_vez()
        self.assertEqual(nomes, ["Ana", "Alisson", "Levi", "Ana"])

    def test_dado_e_destinos(self):
        p = partida()
        p.rolar_dado(6)
        self.assertEqual(p.estado, Partida.MOVER)
        self.assertFalse([d for d in p.destinos if d[0] == "comodo"])   # do Saguão, 6 não chega
        with self.assertRaises(ValueError):
            p.mover(comodo("l05"))

    def test_obrigado_a_sair_do_comodo(self):
        p = partida(1)
        colocar(p, p.jogadores[0], comodo("l05"))
        p.rolar_dado(6)
        self.assertNotIn(comodo("l05"), p.destinos)
        self.assertIn(PORTA_ESC, p.destinos)

    def test_porta_bloqueada_perde_a_vez(self):
        p = partida(2)
        ana, alisson = p.jogadores
        alisson.posicao = PORTA_ESC
        colocar(p, ana, comodo("l05"))
        p.rolar_dado(3)
        self.assertEqual(p.estado, Partida.AGIR)
        self.assertEqual(p.destinos, {})

    def test_so_um_detetive_por_comodo(self):
        p = partida(2)
        ana, alisson = p.jogadores
        ana.posicao = comodo("l05")
        colocar(p, alisson, casa(10, 6))
        p.rolar_dado(2)
        self.assertNotIn(comodo("l05"), p.destinos)

    def test_ve_as_pistas_ao_entrar(self):
        p = partida()
        colocar(p, p.jogadores[0], casa(10, 6))
        p.rolar_dado(2)
        p.mover(comodo("l05"))
        self.assertEqual(p.jogador.pistas_vistas, ["pi09", "pi10"])


class TestComodo(unittest.TestCase):
    def entrar(self, p, cid="l05"):
        porta = {"l05": casa(10, 6), "l02": casa(4, 10), "l01": casa(4, 6)}[cid]
        colocar(p, p.jogador, porta)
        p.rolar_dado(2)
        p.mover(comodo(cid))

    def test_interrogatorio_uma_vez(self):
        p = partida(); self.entrar(p)
        qs = p.sortear_perguntas()
        self.assertEqual(len(qs), 3)
        resp = p.interrogar("p03", "q02")
        self.assertIn("Otávio", resp)
        with self.assertRaises(RuntimeError):
            p.interrogar("p01", "q01")

    def test_nao_interroga_no_corredor(self):
        p = partida(); p.rolar_dado(2); p.mover(casa(7, 7))
        self.assertFalse(p.pode_interrogar)

    def test_palpite_mostra_item_por_item_e_tira_vida(self):
        p = partida(); self.entrar(p, "l05")
        r = p.palpite("p04", "a02")
        self.assertEqual((r.suspeito, r.arma, r.comodo), (True, False, False))
        self.assertEqual(r.vidas_restantes, 4)
        self.assertEqual(p.jogador.caderno, {"p04": "certo", "a02": "errado", "l05": "errado"})
        with self.assertRaises(RuntimeError):
            p.palpite("p01", "a01")   # só 1 palpite por vez

    def test_palpite_certo_resolve_o_caso(self):
        p = partida(); self.entrar(p, "l01")
        r = p.palpite("p04", "a01")
        self.assertTrue(r.resolveu)
        self.assertEqual(p.estado, Partida.FIM_CASO)
        self.assertEqual(p.vencedor.nome, "Ana")
        self.assertEqual(p.vencedor.pontos, 100 + 20 * 5)

    def test_cinco_erros_eliminam(self):
        p = partida(2)
        ana = p.jogador
        for _ in range(5):
            ana.posicao = comodo("l02"); p.estado = Partida.AGIR; p.ja_palpitou = False
            p.palpite("p01", "a02")
        self.assertTrue(ana.eliminado)
        p.encerrar_vez()
        self.assertEqual(p.jogador.nome, "Alisson")
        p.encerrar_vez()
        self.assertEqual(p.jogador.nome, "Alisson")   # Ana fica de fora


class TestCartadaFinal(unittest.TestCase):
    def test_cartada_certa_de_qualquer_lugar(self):
        p = partida()
        self.assertTrue(p.cartada_final("p04", "a01", "l01"))   # ainda no Saguão
        self.assertEqual(p.vencedor.pontos, 100 + 20 * 5 + 50)

    def test_cartada_errada_elimina(self):
        p = partida(2)
        self.assertFalse(p.cartada_final("p01", "a01", "l01"))
        self.assertTrue(p.jogadores[0].eliminado)
        self.assertNotEqual(p.estado, Partida.FIM_CASO)

    def test_todos_eliminados_encerra_o_caso(self):
        p = partida(1)
        p.cartada_final("p01", "a01", "l01")
        self.assertEqual(p.estado, Partida.FIM_CASO)
        self.assertIsNone(p.vencedor)


class TestCasoExemplo(unittest.TestCase):
    def test_caso_exemplo_aprovado(self):
        erros, _ = validar.validar(CASO)
        self.assertEqual(erros, [])


if __name__ == "__main__":
    unittest.main()

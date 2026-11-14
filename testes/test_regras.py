"""Testes das regras do Quem Foi?. Rodar com: python -m unittest discover testes"""
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


def jogadores(n=3):
    cores = [("Ana", "vermelho", "#D4404C"), ("Alisson", "azul", "#4A7FD4"), ("Levi", "verde", "#4FAE6A")]
    return [Jogador(nome, cor, hx) for nome, cor, hx in cores[:n]]


def partida(n=3, seed=1):
    return Partida(CASO, jogadores(n), rng=random.Random(seed))


class TestTabuleiro(unittest.TestCase):
    def setUp(self):
        self.t = Tabuleiro.padrao()

    def test_saida_do_saguao_pelos_dois_lados(self):
        d = self.t.destinos(SAGUAO, 1, set())
        self.assertEqual(set(d), {casa(3, 4), casa(7, 4)})

    def test_comodo_mais_perto_do_saguao_fica_a_5_passos(self):
        d = self.t.destinos(SAGUAO, 6, set())
        perto = min(n for lugar, n in d.items() if lugar[0] == "comodo")
        self.assertEqual(perto, 5)
        self.assertNotIn(comodo("l01"), self.t.destinos(SAGUAO, 4, set()))

    def test_sem_diagonal(self):
        d = self.t.destinos(casa(3, 4), 1, set())
        self.assertEqual(set(d), {casa(3, 3), casa(3, 5), casa(2, 4)})

    def test_casa_ocupada_bloqueia_passagem(self):
        livre = self.t.destinos(casa(3, 3), 2, set())
        self.assertIn(casa(5, 3), livre)
        bloqueado = self.t.destinos(casa(3, 3), 2, {casa(4, 3)})
        self.assertNotIn(casa(5, 3), bloqueado)
        self.assertNotIn(casa(4, 3), bloqueado)

    def test_comodo_ocupado_fica_fechado(self):
        d = self.t.destinos(casa(1, 3), 1, {comodo("l01")})
        self.assertNotIn(comodo("l01"), d)

    def test_entrar_no_comodo_e_opcional(self):
        d = self.t.destinos(casa(1, 3), 3, set())
        self.assertIn(comodo("l01"), d)           # pode entrar
        self.assertIn(casa(3, 3), d)              # ou seguir andando

    def test_comodo_nao_e_atalho(self):
        # quem está na porta da Biblioteca e entra, para ali; não sai do outro lado
        d = self.t.destinos(casa(1, 3), 6, set())
        self.assertEqual(d[comodo("l01")], 1)

    def test_caminho_casa_a_casa(self):
        c = self.t.caminho(SAGUAO, comodo("l05"), set())
        self.assertEqual(c[0], SAGUAO)
        self.assertEqual(c[-1], comodo("l05"))
        self.assertEqual(len(c) - 1, 5)


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
        p.rolar_dado(4)
        self.assertEqual(p.estado, Partida.MOVER)
        self.assertFalse([d for d in p.destinos if d[0] == "comodo"])   # com 4 nenhum cômodo
        with self.assertRaises(ValueError):
            p.mover(comodo("l05"))

    def test_todos_os_comodos_ficam_a_5_do_saguao(self):
        p = partida()
        p.rolar_dado(5)
        self.assertEqual({d[1] for d in p.destinos if d[0] == "comodo"},
                         {"l01", "l02", "l03", "l04", "l05", "l06"})

    def test_obrigado_a_sair_do_comodo(self):
        p = partida(1)
        p.rolar_dado(5); p.mover(comodo("l05"))
        p.encerrar_vez()                    # só 1 jogador: a vez volta para ele
        p.rolar_dado(6)
        self.assertNotIn(comodo("l05"), p.destinos)
        self.assertIn(casa(5, 3), p.destinos)

    def test_porta_bloqueada_perde_a_vez(self):
        p = partida(2)
        p.rolar_dado(5); p.mover(comodo("l05")); p.encerrar_vez()      # Ana no Escritório
        p.rolar_dado(4); p.mover(casa(5, 3)); p.encerrar_vez()         # Alisson para na porta
        p.rolar_dado(3)                                                # Ana não consegue sair
        self.assertEqual(p.estado, Partida.AGIR)
        self.assertEqual(p.destinos, {})

    def test_so_um_detetive_por_comodo(self):
        p = partida(2)
        p.rolar_dado(5); p.mover(comodo("l05")); p.encerrar_vez()
        p.rolar_dado(5)
        self.assertNotIn(comodo("l05"), p.destinos)

    def test_ve_as_pistas_ao_entrar(self):
        p = partida()
        p.rolar_dado(5); p.mover(comodo("l05"))
        self.assertEqual(p.jogador.pistas_vistas, ["pi09", "pi10"])


class TestComodo(unittest.TestCase):
    def entrar(self, p, cid="l05"):
        p.rolar_dado(5); p.mover(comodo(cid))

    def test_interrogatorio_uma_vez(self):
        p = partida(); self.entrar(p)
        qs = p.sortear_perguntas()
        self.assertEqual(len(qs), 3)
        resp = p.interrogar("p03", "q02")
        self.assertIn("Otávio", resp)
        with self.assertRaises(RuntimeError):
            p.interrogar("p01", "q01")

    def test_nao_interroga_no_corredor(self):
        p = partida(); p.rolar_dado(2); p.mover(casa(3, 3))
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
        p = partida()
        p.jogador.posicao = comodo("l01")
        p.estado = Partida.AGIR
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

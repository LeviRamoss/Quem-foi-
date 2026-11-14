"""Regras do Quem Foi?, sem nenhuma parte gráfica.

Tudo o que decide o jogo fica aqui: tabuleiro, movimento, vez dos jogadores,
cômodos, interrogatório, palpite, Cartada Final e pontuação. A interface
(main.py) só chama estas funções e desenha o resultado.
"""
from __future__ import annotations

import json
import random
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"

VIDAS_INICIAIS = 5
PONTOS_CASO = 100
PONTOS_POR_VIDA = 20
PONTOS_CARTADA = 50
PERGUNTAS_SORTEADAS = 3

SAGUAO = ("saguao",)


def carregar_json(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def casa(col, lin):
    return ("casa", col, lin)


def comodo(cid):
    return ("comodo", cid)


# --------------------------------------------------------------------------- tabuleiro
class Tabuleiro:
    """Grafo do tabuleiro: casas de corredor, cômodos e o Saguão."""

    def __init__(self, dados_tabuleiro: dict, comodos: list[dict]):
        self.largura = dados_tabuleiro["largura"]
        self.altura = dados_tabuleiro["altura"]
        self.mapa = dados_tabuleiro["mapa"]
        self.comodos = {c["id"]: c for c in comodos}
        self.vizinhos: dict[tuple, list[tuple]] = {}

        for lin, linha in enumerate(self.mapa):
            for col, ch in enumerate(linha):
                if ch == ".":
                    self.vizinhos[casa(col, lin)] = []
        for (_, col, lin) in list(self.vizinhos):
            for dc, dl in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = casa(col + dc, lin + dl)
                if v in self.vizinhos:
                    self.vizinhos[casa(col, lin)].append(v)
        # porta: a casa de corredor colada ao cômodo
        for cid, c in self.comodos.items():
            porta = casa(c["porta"]["col"], c["porta"]["lin"])
            self.vizinhos[comodo(cid)] = [porta]
            self.vizinhos[porta].append(comodo(cid))
        saidas = [casa(s["col"], s["lin"]) for s in dados_tabuleiro["saguao"]["saidas"]]
        self.vizinhos[SAGUAO] = saidas
        self.saguao_area = dados_tabuleiro["saguao"]["area"]
        self.saidas_saguao = saidas
        self.obstaculos = dados_tabuleiro.get("obstaculos", [])

    @classmethod
    def padrao(cls):
        return cls(carregar_json(DADOS / "tabuleiro.json"), carregar_json(DADOS / "comodos.json"))

    def destinos(self, origem, passos: int, ocupados: set, proibidos: set = frozenset()) -> dict:
        """Lugares aonde dá para chegar andando de 1 até `passos` casas.

        - Não passa nem para em casa ocupada por outro detetive.
        - Cômodo ocupado fica fechado; entrar num cômodo encerra o movimento.
        - O Saguão só serve de ponto de partida.
        Devolve {destino: menor número de passos}.
        """
        dist = {origem: 0}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            if dist[atual] == passos:
                continue
            if atual != origem and atual[0] == "comodo":
                continue  # quem entra no cômodo para ali
            for v in self.vizinhos[atual]:
                if v in dist or v == SAGUAO or v in ocupados:
                    continue
                dist[v] = dist[atual] + 1
                fila.append(v)
        return {d: n for d, n in dist.items() if d != origem and d not in proibidos}

    def caminho(self, origem, destino, ocupados: set) -> list:
        """Menor caminho casa a casa (para animar o peão andando)."""
        anterior = {origem: None}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            if atual == destino:
                break
            if atual != origem and atual[0] == "comodo":
                continue
            for v in self.vizinhos[atual]:
                if v not in anterior and v != SAGUAO and (v not in ocupados or v == destino):
                    anterior[v] = atual
                    fila.append(v)
        if destino not in anterior:
            return []
        trajeto = [destino]
        while trajeto[-1] != origem:
            trajeto.append(anterior[trajeto[-1]])
        return trajeto[::-1]


# --------------------------------------------------------------------------- jogadores e caderno
@dataclass
class Jogador:
    nome: str
    cor: str           # vermelho, azul ou verde
    hex: str
    posicao: tuple = SAGUAO
    vidas: int = VIDAS_INICIAIS
    eliminado: bool = False
    pontos: int = 0
    caderno: dict = field(default_factory=dict)   # id do item -> "certo" | "errado"
    pistas_vistas: list = field(default_factory=list)
    respostas_ouvidas: list = field(default_factory=list)   # (suspeito, pergunta)

    @property
    def no_comodo(self):
        return self.posicao[1] if self.posicao[0] == "comodo" else None


@dataclass
class ResultadoPalpite:
    suspeito: bool
    arma: bool
    comodo: bool
    vidas_restantes: int
    resolveu: bool
    eliminado: bool


# --------------------------------------------------------------------------- partida
class Partida:
    """Uma partida = um caso, jogado por 1 a 3 detetives no mesmo computador."""

    # estados da vez
    ROLAR, MOVER, AGIR, FIM_CASO = "rolar", "mover", "agir", "fim_caso"

    def __init__(self, caso: dict, jogadores: list[Jogador], tabuleiro: Tabuleiro | None = None,
                 perguntas: list[dict] | None = None, rng: random.Random | None = None):
        if not 1 <= len(jogadores) <= 3:
            raise ValueError("o jogo é de 1 a 3 jogadores")
        self.caso = caso
        self.jogadores = jogadores
        self.tabuleiro = tabuleiro or Tabuleiro.padrao()
        self.perguntas = perguntas or carregar_json(DADOS / "perguntas.json")
        self.rng = rng or random.Random()
        self.solucao = caso["solucao"]
        self.vez = 0
        self.estado = self.ROLAR
        self.dado = None
        self.destinos: dict = {}
        self.vencedor: Jogador | None = None
        self.mensagens: list[str] = []
        self._inicio_vez()

    # ---------------------------------------------------------------- ordem inicial
    @staticmethod
    def sortear_ordem(jogadores: list[Jogador], rng: random.Random) -> tuple[list[Jogador], list[dict]]:
        """Todos jogam o dado; quem tirar mais começa. Empate: os empatados jogam de novo."""
        rodadas = []
        grupo = list(jogadores)
        ordem: list[Jogador] = []
        pendentes = [grupo]
        while pendentes:
            grupo = pendentes.pop(0)
            if len(grupo) == 1:
                ordem.append(grupo[0])
                continue
            jogadas = {j.nome: rng.randint(1, 6) for j in grupo}
            rodadas.append(jogadas)
            valores = sorted(set(jogadas.values()), reverse=True)
            novos = [[j for j in grupo if jogadas[j.nome] == v] for v in valores]
            pendentes = novos + pendentes
        return ordem, rodadas

    # ---------------------------------------------------------------- vez
    @property
    def jogador(self) -> Jogador:
        return self.jogadores[self.vez]

    def _ocupados(self, exceto: Jogador) -> set:
        return {j.posicao for j in self.jogadores
                if j is not exceto and not j.eliminado and j.posicao != SAGUAO}

    def _inicio_vez(self):
        self.estado = self.ROLAR
        self.dado = None
        self.destinos = {}
        self.ja_interrogou = False
        self.ja_palpitou = False
        self.comodo_de_saida = self.jogador.no_comodo   # obrigado a sair dele nesta vez

    def rolar_dado(self, valor: int | None = None) -> int:
        if self.estado != self.ROLAR:
            raise RuntimeError("agora não é hora de jogar o dado")
        self.dado = valor or self.rng.randint(1, 6)
        proibidos = {comodo(self.comodo_de_saida)} if self.comodo_de_saida else set()
        self.destinos = self.tabuleiro.destinos(self.jogador.posicao, self.dado,
                                                self._ocupados(self.jogador), proibidos)
        if not self.destinos:
            self.mensagens.append(f"{self.jogador.nome} está com a passagem bloqueada e perde a vez.")
            self.estado = self.AGIR
        else:
            self.estado = self.MOVER
        return self.dado

    def mover(self, destino) -> list:
        if self.estado != self.MOVER or destino not in self.destinos:
            raise ValueError("destino fora do alcance")
        trajeto = self.tabuleiro.caminho(self.jogador.posicao, destino, self._ocupados(self.jogador))
        self.jogador.posicao = destino
        self.destinos = {}
        self.estado = self.AGIR
        if destino[0] == "comodo":
            for p in self.caso["pistas"]:
                if p["comodo"] == destino[1] and p["id"] not in self.jogador.pistas_vistas:
                    self.jogador.pistas_vistas.append(p["id"])
        return trajeto

    def pistas_do_comodo(self, cid: str) -> list[dict]:
        return [p for p in self.caso["pistas"] if p["comodo"] == cid]

    def encerrar_vez(self):
        if self.estado == self.FIM_CASO:
            return
        ativos = [j for j in self.jogadores if not j.eliminado]
        if not ativos:
            self._fim_caso(None)
            return
        for _ in range(len(self.jogadores)):
            self.vez = (self.vez + 1) % len(self.jogadores)
            if not self.jogador.eliminado:
                break
        self._inicio_vez()

    # ---------------------------------------------------------------- interrogatório
    @property
    def pode_interrogar(self) -> bool:
        return self.estado == self.AGIR and self.jogador.no_comodo is not None and not self.ja_interrogou

    def sortear_perguntas(self) -> list[dict]:
        return self.rng.sample(self.perguntas, PERGUNTAS_SORTEADAS)

    def interrogar(self, suspeito: str, pergunta: str) -> str:
        if not self.pode_interrogar:
            raise RuntimeError("só dá para interrogar uma vez, dentro de um cômodo")
        if suspeito not in self.caso["suspeitos"]:
            raise ValueError("suspeito fora do caso")
        self.ja_interrogou = True
        self.jogador.respostas_ouvidas.append((suspeito, pergunta))
        return self.caso["respostas"][suspeito][pergunta]["texto"]

    # ---------------------------------------------------------------- palpite e Cartada Final
    @property
    def pode_palpitar(self) -> bool:
        return self.estado == self.AGIR and self.jogador.no_comodo is not None and not self.ja_palpitou

    def _marcar(self, j: Jogador, item: str, certo: bool):
        j.caderno[item] = "certo" if certo else "errado"

    def palpite(self, suspeito: str, arma: str) -> ResultadoPalpite:
        """O cômodo do palpite é sempre aquele onde o jogador está."""
        if not self.pode_palpitar:
            raise RuntimeError("palpite só dentro de um cômodo, uma vez por vez de jogar")
        j = self.jogador
        local = j.no_comodo
        self.ja_palpitou = True
        r_s = suspeito == self.solucao["culpado"]
        r_a = arma == self.solucao["arma"]
        r_c = local == self.solucao["comodo"]
        for item, ok in ((suspeito, r_s), (arma, r_a), (local, r_c)):
            self._marcar(j, item, ok)
        resolveu = r_s and r_a and r_c
        if resolveu:
            self._vitoria(j, cartada=False)
        else:
            j.vidas -= 1
            if j.vidas <= 0:
                self._eliminar(j)
        return ResultadoPalpite(r_s, r_a, r_c, j.vidas, resolveu, j.eliminado)

    def cartada_final(self, suspeito: str, arma: str, local: str) -> bool:
        """De qualquer lugar, na sua vez. Errou: eliminado."""
        if self.estado == self.FIM_CASO:
            raise RuntimeError("o caso já terminou")
        j = self.jogador
        acertou = (suspeito, arma, local) == (self.solucao["culpado"], self.solucao["arma"], self.solucao["comodo"])
        if acertou:
            self._vitoria(j, cartada=True)
        else:
            self._eliminar(j)
        return acertou

    def _eliminar(self, j: Jogador):
        j.eliminado = True
        self.mensagens.append(f"{j.nome} foi eliminado.")
        if all(x.eliminado for x in self.jogadores):
            self._fim_caso(None)
        else:
            self.estado = self.AGIR  # a interface chama encerrar_vez()

    def _vitoria(self, j: Jogador, cartada: bool):
        j.pontos += PONTOS_CASO + PONTOS_POR_VIDA * j.vidas + (PONTOS_CARTADA if cartada else 0)
        self._fim_caso(j)

    def _fim_caso(self, vencedor: Jogador | None):
        self.vencedor = vencedor
        self.estado = self.FIM_CASO

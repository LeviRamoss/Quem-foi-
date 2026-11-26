"""Quem Foi? — interface do jogo em Pygame-CE.

Rodar:  pip install pygame-ce
        python jogo/main.py

As regras ficam em regras.py; aqui só desenhamos e tratamos cliques.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pygame

from regras import (DADOS, SAGUAO, Jogador, Partida, Tabuleiro, carregar_json, casa)

RAIZ = Path(__file__).resolve().parent
ASSETS = RAIZ / "assets"
sys.path.insert(0, str(RAIZ.parent / "fabrica"))
import gerador_local  # noqa: E402  (casos novos sem internet)

LARGURA, ALTURA = 1600, 900   # a janela se ajusta ao monitor (F11 = tela cheia)
FPS = 60
TAB = carregar_json(DADOS / "tabuleiro.json")
CASA = TAB["tamanho_casa_px"]          # tamanho de cada casa do tabuleiro (46px)
TAB_L, TAB_A = TAB["largura"] * CASA, TAB["altura"] * CASA   # 21 x 17 casas
BX, BY = 316, 70              # canto do tabuleiro na tela
PX = BX + TAB_L + 16          # coluna da direita

PAL = {k: pygame.Color(v) for k, v in carregar_json(DADOS / "paleta.json").items()}
BRANCO_SUAVE = PAL["texto"]
CINZA = PAL["texto_suave"]


# =========================================================================== utilidades
def fonte(tipo: str, tamanho: int, negrito=False):
    nomes = {
        "titulo": "georgia,palatinolinotype,timesnewroman,serif",
        "texto": "segoeui,arial,helvetica,sans",
        "maquina": "couriernew,courier,monospace",
    }[tipo]
    return pygame.font.SysFont(nomes, tamanho, bold=negrito)


def quebrar(texto: str, f, largura: int) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = (atual + " " + palavra).strip()
        if f.size(teste)[0] <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def escrever(tela, texto, f, cor, pos, largura=None, entrelinha=4, centro=False):
    """Escreve texto (quebrando linhas se `largura`). Devolve o y final."""
    x, y = pos
    linhas = quebrar(texto, f, largura) if largura else [texto]
    for linha in linhas:
        img = f.render(linha, True, cor)
        r = img.get_rect(topleft=(x, y))
        if centro:
            r.centerx = x
        tela.blit(img, r)
        y += img.get_height() + entrelinha
    return y


def painel(tela, rect, cor=None, borda=None, raio=10, alfa=255):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    c = pygame.Color(cor or PAL["painel"])
    c.a = alfa
    pygame.draw.rect(s, c, s.get_rect(), border_radius=raio)
    if borda:
        pygame.draw.rect(s, borda, s.get_rect(), 2, border_radius=raio)
    tela.blit(s, rect.topleft)


class Botao:
    def __init__(self, rect, texto, acao, cor=None, ativo=True):
        self.rect = pygame.Rect(rect)
        self.texto, self.acao, self.cor, self.ativo = texto, acao, cor, ativo

    def desenhar(self, tela, f, mouse):
        if not self.texto:
            return  # área clicável invisível (grades de escolha)
        cima = self.ativo and self.rect.collidepoint(mouse)
        if self.cor:
            fundo = pygame.Color(self.cor)
            if not self.ativo:
                fundo = pygame.Color(60, 60, 66)
            pygame.draw.rect(tela, fundo, self.rect, border_radius=8)
            if cima:
                pygame.draw.rect(tela, BRANCO_SUAVE, self.rect, 2, border_radius=8)
            cor_txt = BRANCO_SUAVE if self.ativo else CINZA
        else:
            pygame.draw.rect(tela, PAL["painel"], self.rect, border_radius=8)
            borda = PAL["dourado_claro"] if cima else (PAL["dourado"] if self.ativo else PAL["linha"])
            pygame.draw.rect(tela, borda, self.rect, 2, border_radius=8)
            cor_txt = PAL["dourado_claro"] if self.ativo else PAL["linha"]
        img = f.render(self.texto, True, cor_txt)
        tela.blit(img, img.get_rect(center=self.rect.center))

    def clicou(self, pos):
        return self.ativo and self.rect.collidepoint(pos)


# =========================================================================== imagens
class Imagens:
    def __init__(self):
        def carregar(rel, tam=None):
            img = pygame.image.load(str(ASSETS / rel)).convert_alpha()
            return pygame.transform.smoothscale(img, tam) if tam else img

        self.tabuleiro = carregar("tabuleiro.png")
        self.comodos = {p.stem: carregar(f"comodos/{p.name}") for p in (ASSETS / "comodos").glob("*.png")}
        self.suspeitos = {p.stem: carregar(f"suspeitos/{p.name}") for p in (ASSETS / "suspeitos").glob("*.png")}
        self.armas = {p.stem: carregar(f"armas/{p.name}") for p in (ASSETS / "armas").glob("*.png")}
        self.dado = {n: carregar(f"dado/{n}.png") for n in range(1, 7)}
        self.peoes = {d: carregar(f"detetives/{d}_peao.png") for d in ("d1", "d2", "d3")}
        self.retratos_det = {d: carregar(f"detetives/{d}_retrato.png") for d in ("d1", "d2", "d3")}
        self.vida_cheia = carregar("ui/vida_cheia.png", (26, 26))
        self.vida_vazia = carregar("ui/vida_vazia.png", (26, 26))
        self.lupa = carregar("ui/lupa.png", (36, 36))
        self._cache = {}

    def escala(self, img, tam):
        chave = (id(img), tam)
        if chave not in self._cache:
            self._cache[chave] = pygame.transform.smoothscale(img, tam)
        return self._cache[chave]


# =========================================================================== jogo
class Jogo:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Quem Foi?")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
        self.relogio = pygame.time.Clock()
        self.img = Imagens()
        self.f_titulo = fonte("titulo", 42, True)
        self.f_sub = fonte("titulo", 26, True)
        self.f_txt = fonte("texto", 21)
        self.f_peq = fonte("texto", 17)
        self.f_btn = fonte("texto", 19, True)
        self.f_maq = fonte("maquina", 18)

        self.personagens = {p["id"]: p for p in carregar_json(DADOS / "personagens.json")}
        self.armas = {a["id"]: a for a in carregar_json(DADOS / "armas.json")}
        self.comodos = {c["id"]: c for c in carregar_json(DADOS / "comodos.json")}
        self.perguntas = {q["id"]: q for q in carregar_json(DADOS / "perguntas.json")}
        self.detetives = carregar_json(DADOS / "detetives.json")
        self.tabuleiro = Tabuleiro.padrao()
        self.ultima_solucao = None
        self.casos_jogados = set()
        self.rng = random.Random()

        # tela de início
        self.n_jogadores = 3
        self.nomes = ["Jogador 1", "Jogador 2", "Jogador 3"]
        self.campo_ativo = None

        self.cena = "inicio"
        self.partida: Partida | None = None
        self.jogadores: list[Jogador] = []
        self.modal = None            # janela aberta por cima do tabuleiro
        self.anim = None             # animação em andamento
        self.aviso = ""
        self.botoes: list[Botao] = []
        self.tem_musica = self.tocar_musica()
        self.musica = self.tem_musica

    # ------------------------------------------------------------------ música de fundo
    def tocar_musica(self) -> bool:
        """Toca em loop a primeira música de jogo/assets/audio/. Sem arquivo ou sem som, o jogo segue mudo."""
        pasta = ASSETS / "audio"
        arquivos = sorted(a for a in pasta.glob("*") if a.suffix.lower() in (".ogg", ".mp3", ".wav")) if pasta.exists() else []
        if not arquivos:
            return False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(str(arquivos[0]))
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)          # -1 = repete para sempre
            return True
        except pygame.error as e:
            print("Sem música:", e)
            return False

    def alternar_musica(self):
        if not self.tem_musica:
            return
        if self.musica:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
        self.musica = not self.musica

    # ------------------------------------------------------------------ laço principal
    def rodar(self):
        while True:
            dt = self.relogio.tick(FPS) / 1000
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.evento(ev)
            self.atualizar(dt)
            self.desenhar()
            pygame.display.flip()

    # ------------------------------------------------------------------ início e partidas
    def comecar(self):
        self.jogadores = []
        for i in range(self.n_jogadores):
            d = self.detetives[i]
            nome = self.nomes[i].strip() or f"Jogador {i + 1}"
            j = Jogador(nome, d["cor"], d["hex"])
            j.peao = d["id"]
            self.jogadores.append(j)
        ordem, rodadas = Partida.sortear_ordem(self.jogadores, self.rng)
        self.jogadores = ordem
        self.rodadas_ordem = rodadas
        self.cena = "ordem"

    def novo_caso(self):
        # primeiro os casos escritos pela IA (dados/casos/ia); quando acabam, o gerador local
        caso = self.proximo_caso_ia() or gerador_local.gerar_caso(self.rng, evitar=self.ultima_solucao)
        self.ultima_solucao = {**caso["solucao"], "titulo": caso["titulo"]}
        for j in self.jogadores:
            j.posicao, j.vidas, j.eliminado = SAGUAO, 5, False
            j.caderno, j.pistas_vistas, j.respostas_ouvidas = {}, [], []
        self.partida = Partida(caso, self.jogadores, self.tabuleiro, rng=self.rng)
        self.modal = {"tipo": "abertura"}
        self.cena = "capa"

    def proximo_caso_ia(self):
        pasta = DADOS / "casos" / "ia"
        for arq in sorted(pasta.glob("*.json")) if pasta.exists() else []:
            if arq.stem in self.casos_jogados:
                continue
            self.casos_jogados.add(arq.stem)
            try:
                return carregar_json(arq)
            except (OSError, ValueError):
                continue
        return None

    # ------------------------------------------------------------------ coordenadas
    def rect_casa(self, col, lin):
        return pygame.Rect(BX + col * CASA, BY + lin * CASA, CASA, CASA)

    def rect_comodo(self, cid):
        a = self.comodos[cid]["area"]
        return pygame.Rect(BX + a["col"] * CASA, BY + a["lin"] * CASA, a["largura"] * CASA, a["altura"] * CASA)

    def rect_saguao(self):
        a = TAB["saguao"]["area"]
        return pygame.Rect(BX + a["col"] * CASA, BY + a["lin"] * CASA, a["largura"] * CASA, a["altura"] * CASA)

    def centro_lugar(self, lugar, indice=0):
        if lugar == SAGUAO:
            r = self.rect_saguao()
            return (r.centerx + (indice - 1) * CASA, r.centery - CASA // 3)
        if lugar[0] == "comodo":
            return self.rect_comodo(lugar[1]).center
        return self.rect_casa(lugar[1], lugar[2]).center

    def lugar_na_tela(self, pos):
        x, y = pos[0] - BX, pos[1] - BY
        if not (0 <= x < TAB_L and 0 <= y < TAB_A):
            return None
        col, lin = x // CASA, y // CASA
        for cid in self.comodos:
            if self.rect_comodo(cid).collidepoint(pos):
                return ("comodo", cid)
        if self.tabuleiro.mapa[lin][col] == ".":
            return casa(col, lin)
        return None

    # ------------------------------------------------------------------ eventos
    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m and self.campo_ativo is None:
            self.alternar_musica()      # M liga e desliga a música (menos quando está digitando um nome)
            return
        if self.cena == "inicio":
            self.evento_inicio(ev)
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.anim:
                return
            for b in list(self.botoes):
                if b.clicou(ev.pos):
                    b.acao()
                    return
            if self.cena == "jogo" and not self.modal and self.partida.estado == Partida.MOVER:
                lugar = self.lugar_na_tela(ev.pos)
                if lugar in self.partida.destinos:
                    self.mover(lugar)

    def evento_inicio(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.campo_ativo = None
            for i in range(self.n_jogadores):
                if self.rect_campo(i).collidepoint(ev.pos):
                    self.campo_ativo = i
                    if self.nomes[i].startswith("Jogador "):
                        self.nomes[i] = ""
            for b in list(self.botoes):
                if b.clicou(ev.pos):
                    b.acao()
                    return
        elif ev.type == pygame.TEXTINPUT and self.campo_ativo is not None:
            if len(self.nomes[self.campo_ativo]) < 14:
                self.nomes[self.campo_ativo] += ev.text
        elif ev.type == pygame.KEYDOWN and self.campo_ativo is not None:
            if ev.key == pygame.K_BACKSPACE:
                self.nomes[self.campo_ativo] = self.nomes[self.campo_ativo][:-1]
            elif ev.key in (pygame.K_RETURN, pygame.K_TAB):
                self.campo_ativo = (self.campo_ativo + 1) % self.n_jogadores

    # ------------------------------------------------------------------ ações da vez
    def jogar_dado(self):
        valor = self.rng.randint(1, 6)
        self.anim = {"tipo": "dado", "t": 0.0, "dur": 0.9, "valor": valor, "face": 1, "troca": 0.0}

    def mover(self, destino):
        p = self.partida
        origem = p.jogador.posicao
        trajeto = p.tabuleiro.caminho(origem, destino, p._ocupados(p.jogador))
        p.mover(destino)
        self.anim = {"tipo": "andar", "trajeto": trajeto, "passo": 0, "t": 0.0, "dur": 0.13}
        if destino[0] == "comodo":
            self.depois_anim = lambda: self.abrir_pistas(destino[1])
        else:
            self.depois_anim = None

    def no_na(self, cid):
        """'no Escritório', 'na Biblioteca'."""
        artigo = "no" if cid in ("l05", "l03") else "na"
        return f"{artigo} {self.comodos[cid]['nome']}"

    def abrir_pistas(self, cid):
        self.modal = {"tipo": "pistas", "comodo": cid}

    def encerrar_vez(self):
        self.modal = None
        self.partida.encerrar_vez()
        if self.partida.estado == Partida.FIM_CASO:
            self.modal = {"tipo": "fim"}
        else:
            self.cena = "capa"

    def abrir_interrogatorio(self):
        self.modal = {"tipo": "interrogar", "suspeito": None,
                      "perguntas": self.partida.sortear_perguntas(), "resposta": None}

    def abrir_palpite(self):
        self.modal = {"tipo": "palpite", "suspeito": None, "arma": None, "resultado": None}

    def abrir_cartada(self):
        self.modal = {"tipo": "cartada", "suspeito": None, "arma": None, "comodo": None, "resultado": None}

    # ------------------------------------------------------------------ atualização (animações)
    def atualizar(self, dt):
        a = self.anim
        if not a:
            return
        a["t"] += dt
        if a["tipo"] == "dado":
            a["troca"] += dt
            if a["troca"] > 0.07:
                a["troca"] = 0
                a["face"] = self.rng.randint(1, 6)
            if a["t"] >= a["dur"]:
                self.anim = None
                self.partida.rolar_dado(a["valor"])
                if self.partida.estado == Partida.AGIR:
                    self.aviso = self.partida.mensagens[-1]
                else:
                    self.aviso = f"Tirou {a['valor']}. Clique numa casa acesa para andar."
        elif a["tipo"] == "andar":
            if a["t"] >= a["dur"]:
                a["t"] = 0
                a["passo"] += 1
                if a["passo"] >= len(a["trajeto"]) - 1:
                    self.anim = None
                    self.aviso = "Encerre a vez ou use a Cartada Final."
                    if self.depois_anim:
                        self.depois_anim()

    # ================================================================== desenho
    def desenhar(self):
        self.tela.fill(PAL["fundo"])
        self.botoes = []
        mouse = pygame.mouse.get_pos()
        {"inicio": self.desenhar_inicio, "ordem": self.desenhar_ordem,
         "capa": self.desenhar_capa, "jogo": self.desenhar_jogo}[self.cena]()
        for b in self.botoes:
            b.desenhar(self.tela, self.f_btn, mouse)

    # ------------------------------------------------------------------ início
    def rect_campo(self, i):
        return pygame.Rect(LARGURA // 2 - 110, 400 + i * 72, 320, 50)

    def desenhar_inicio(self):
        cx = LARGURA // 2
        t = self.f_titulo.render("QUEM", True, BRANCO_SUAVE)
        t2 = self.f_titulo.render("FOI?", True, PAL["vermelho"])
        larg = t.get_width() + 14 + t2.get_width()
        self.tela.blit(t, (cx - larg // 2, 140))
        self.tela.blit(t2, (cx - larg // 2 + t.get_width() + 14, 140))
        escrever(self.tela, "Um jogo de dedução para até 3 detetives", self.f_txt, CINZA, (cx, 205), centro=True)
        escrever(self.tela, "Quantos jogadores?", self.f_sub, PAL["dourado"], (cx, 270), centro=True)
        for n in (1, 2, 3):
            sel = n == self.n_jogadores
            self.botoes.append(Botao((cx - 126 + (n - 1) * 90, 314, 72, 48), str(n),
                                     lambda n=n: setattr(self, "n_jogadores", n),
                                     cor=PAL["sangue"] if sel else None))
        for i in range(self.n_jogadores):
            d = self.detetives[i]
            r = self.rect_campo(i)
            self.tela.blit(self.img.escala(self.img.peoes[d["id"]], (46, 46)), (r.left - 60, r.top + 2))
            pygame.draw.rect(self.tela, PAL["painel"], r, border_radius=8)
            borda = PAL["dourado_claro"] if self.campo_ativo == i else PAL["linha"]
            pygame.draw.rect(self.tela, borda, r, 2, border_radius=8)
            txt = self.nomes[i] + ("|" if self.campo_ativo == i and pygame.time.get_ticks() // 500 % 2 else "")
            escrever(self.tela, txt or " ", self.f_txt, BRANCO_SUAVE, (r.left + 12, r.top + 10))
        self.botoes.append(Botao((cx - 120, 650, 240, 56), "Começar", self.comecar, cor=PAL["sangue"]))
        escrever(self.tela, "Clique num nome para trocar. Todos jogam no mesmo computador. F11: tela cheia.",
                 self.f_peq, CINZA, (cx, 730), centro=True)

    # ------------------------------------------------------------------ ordem inicial
    def desenhar_ordem(self):
        cx = LARGURA // 2
        escrever(self.tela, "Quem começa?", self.f_titulo, BRANCO_SUAVE, (cx, 140), centro=True)
        y = 230
        for i, rodada in enumerate(self.rodadas_ordem):
            txt = "  ·  ".join(f"{nome}: {v}" for nome, v in rodada.items())
            escrever(self.tela, ("Desempate — " if i else "Dados — ") + txt, self.f_txt, CINZA, (cx, y), centro=True)
            y += 34
        y += 20
        for i, j in enumerate(self.jogadores):
            self.tela.blit(self.img.escala(self.img.retratos_det[j.peao], (130, 130)), (cx - 335 + i * 240, y))
            escrever(self.tela, f"{i + 1}º  {j.nome}", self.f_sub, pygame.Color(j.hex), (cx - 270 + i * 240, y + 140), centro=True)
        self.botoes.append(Botao((cx - 120, 680, 240, 56), "Abrir o caso", self.novo_caso, cor=PAL["sangue"]))

    # ------------------------------------------------------------------ capa da vez (privacidade)
    def desenhar_capa(self):
        cx = LARGURA // 2
        if self.modal and self.modal.get("tipo") == "abertura":
            c = self.partida.caso
            origem = "UM NOVO CASO · ESCRITO PELA IA" if c["id"].startswith("caso_ia") else "UM NOVO CASO"
            escrever(self.tela, origem, self.f_maq, PAL["dourado"], (cx, 170), centro=True)
            escrever(self.tela, c["titulo"], self.f_titulo, BRANCO_SUAVE, (cx, 205), centro=True)
            escrever(self.tela, c["enredo"], self.f_txt, CINZA, (cx - 420, 300), largura=840, entrelinha=8)
            escrever(self.tela, f"Vítima: {c['vitima']['nome']}  ·  Horário: {c['horario_do_crime']}",
                     self.f_peq, PAL["dourado_claro"], (cx, 520), centro=True)

            def fechar():
                self.modal = None
            self.botoes.append(Botao((cx - 120, 660, 240, 56), "Investigar", fechar, cor=PAL["sangue"]))
            return
        j = self.partida.jogador
        self.tela.blit(self.img.escala(self.img.retratos_det[j.peao], (192, 192)), (cx - 96, 190))
        escrever(self.tela, f"Vez de {j.nome}", self.f_titulo, pygame.Color(j.hex), (cx, 420), centro=True)
        escrever(self.tela, "Os outros detetives, olhem para o lado.", self.f_txt, CINZA, (cx, 480), centro=True)

        def entrar():
            self.cena = "jogo"
            self.aviso = "Jogue o dado ou use a Cartada Final."
        self.botoes.append(Botao((cx - 150, 560, 300, 56), "Clique para começar", entrar, cor=PAL["sangue"]))

    # ------------------------------------------------------------------ tela principal
    def desenhar_jogo(self):
        p = self.partida
        j = p.jogador
        self.desenhar_topo(j)
        self.desenhar_tabuleiro()
        self.desenhar_caderno(j)
        self.desenhar_acoes()
        if self.anim and self.anim["tipo"] == "dado":
            face = self.img.dado[self.anim["face"]]
            ang = (self.anim["t"] * 720) % 360
            img = pygame.transform.rotozoom(face, ang, 1.0 + 0.25 * abs((self.anim["t"] % 0.3) - 0.15) / 0.15)
            self.tela.blit(img, img.get_rect(center=(BX + TAB_L // 2, BY + TAB_A // 2)))
        elif p.dado and p.estado in (Partida.MOVER, Partida.AGIR):
            self.tela.blit(self.img.escala(self.img.dado[p.dado], (58, 58)), (BX + TAB_L - 62, 6))
        if self.modal:
            self.desenhar_modal()

    def desenhar_topo(self, j):
        escrever(self.tela, self.partida.caso["titulo"], self.f_sub, BRANCO_SUAVE, (BX, 6))
        escrever(self.tela, self.aviso, self.f_peq, PAL["dourado_claro"], (BX, 40), largura=TAB_L - 90, entrelinha=0)
        self.tela.blit(self.img.escala(self.img.peoes[j.peao], (42, 42)), (20, 14))
        escrever(self.tela, j.nome, self.f_sub, pygame.Color(j.hex), (70, 18))
        for i in range(5):
            self.tela.blit(self.img.vida_cheia if i < j.vidas else self.img.vida_vazia, (PX + i * 32, 10))
        escrever(self.tela, f"{j.pontos} pontos", self.f_peq, PAL["dourado_claro"], (PX, 42))
        if self.tem_musica:
            escrever(self.tela, "Música: M", self.f_peq, PAL["dourado_claro"] if self.musica else CINZA, (LARGURA - 104, 14))

    def desenhar_tabuleiro(self):
        p = self.partida
        self.tela.blit(self.img.tabuleiro, (BX, BY))
        # casas aonde dá para ir
        if p.estado == Partida.MOVER and not self.anim:
            brilho = 90 + int(50 * abs((pygame.time.get_ticks() % 1200) / 600 - 1))
            for lugar in p.destinos:
                r = self.rect_comodo(lugar[1]) if lugar[0] == "comodo" else self.rect_casa(lugar[1], lugar[2])
                s = pygame.Surface(r.size, pygame.SRCALPHA)
                s.fill((230, 200, 140, brilho // 2))
                pygame.draw.rect(s, (230, 200, 140, 255), s.get_rect(), 3)
                self.tela.blit(s, r.topleft)
        # nomes dos cômodos
        for cid, c in self.comodos.items():
            r = self.rect_comodo(cid)
            img = self.f_peq.render(c["nome"], True, BRANCO_SUAVE)
            fundo = pygame.Rect(0, 0, img.get_width() + 12, img.get_height() + 4)
            fundo.midbottom = (r.centerx, r.bottom - 6)
            painel(self.tela, fundo, PAL["fundo"], raio=6, alfa=200)
            self.tela.blit(img, img.get_rect(center=fundo.center))
        # peões
        no_saguao = 0
        for jog in self.jogadores:
            if jog.eliminado:
                continue
            if self.anim and self.anim["tipo"] == "andar" and jog is p.jogador:
                a = self.anim
                ini = self.centro_lugar(a["trajeto"][a["passo"]])
                fim = self.centro_lugar(a["trajeto"][min(a["passo"] + 1, len(a["trajeto"]) - 1)])
                k = min(1.0, a["t"] / a["dur"])
                centro = (ini[0] + (fim[0] - ini[0]) * k, ini[1] + (fim[1] - ini[1]) * k)
            else:
                centro = self.centro_lugar(jog.posicao, no_saguao)
                if jog.posicao == SAGUAO:
                    no_saguao += 1
            peao = self.img.escala(self.img.peoes[jog.peao], (CASA - 4, CASA - 4))
            self.tela.blit(peao, peao.get_rect(center=centro))
            if jog is p.jogador:
                pygame.draw.circle(self.tela, BRANCO_SUAVE, (int(centro[0]), int(centro[1])), CASA // 2 + 3, 3)

    def desenhar_caderno(self, j):
        caso = self.partida.caso
        # esquerda: suspeitos
        r = pygame.Rect(16, BY, BX - 32, TAB_A)
        painel(self.tela, r, borda=PAL["linha"])
        escrever(self.tela, "SUSPEITOS", self.f_maq, PAL["dourado"], (r.left + 14, r.top + 12))
        for i, sid in enumerate(caso["suspeitos"]):
            y = r.top + 48 + i * 148
            self.tela.blit(self.img.escala(self.img.suspeitos[sid], (110, 110)), (r.left + 10, y))
            per = self.personagens[sid]
            cor = CINZA if j.caderno.get(sid) == "errado" else BRANCO_SUAVE
            y2 = escrever(self.tela, per["nome"], self.f_txt, cor, (r.left + 130, y + 18), largura=r.width - 140, entrelinha=0)
            escrever(self.tela, per["papel"], self.f_peq, CINZA, (r.left + 130, y2 + 4), largura=r.width - 140, entrelinha=0)
            self.marca(j.caderno.get(sid), (r.left + 10, y), 110)
        # direita: armas e cômodos
        r = pygame.Rect(PX, BY, LARGURA - PX - 16, TAB_A)
        painel(self.tela, r, borda=PAL["linha"])
        escrever(self.tela, "ARMAS", self.f_maq, PAL["dourado"], (r.left + 14, r.top + 12))
        for i, aid in enumerate(caso["armas"]):
            y = r.top + 42 + i * 50
            self.tela.blit(self.img.escala(self.img.armas[aid], (46, 46)), (r.left + 12, y))
            cor = CINZA if j.caderno.get(aid) == "errado" else BRANCO_SUAVE
            escrever(self.tela, self.armas[aid]["nome"], self.f_txt, cor, (r.left + 66, y + 10))
            self.marca(j.caderno.get(aid), (r.left + 12, y), 44)
        y0 = r.top + 300
        escrever(self.tela, "CÔMODOS", self.f_maq, PAL["dourado"], (r.left + 14, y0))
        for i, cid in enumerate(caso["comodos"]):
            y = y0 + 30 + i * 31
            cor = CINZA if j.caderno.get(cid) == "errado" else BRANCO_SUAVE
            escrever(self.tela, self.comodos[cid]["nome"], self.f_txt, cor, (r.left + 40, y + 4))
            self.marca(j.caderno.get(cid), (r.left + 10, y + 2), 24)

    def marca(self, estado, pos, tam):
        if estado == "errado":
            x, y = pos
            pygame.draw.line(self.tela, PAL["vermelho"], (x + 4, y + 4), (x + tam - 4, y + tam - 4), 4)
            pygame.draw.line(self.tela, PAL["vermelho"], (x + tam - 4, y + 4), (x + 4, y + tam - 4), 4)
        elif estado == "certo":
            pygame.draw.rect(self.tela, PAL["dourado_claro"], (pos[0] - 2, pos[1] - 2, tam + 4, tam + 4), 4, border_radius=max(6, tam // 10))

    def desenhar_acoes(self):
        """Botões empilhados no pé da coluna da direita."""
        if self.modal or self.anim:
            return
        p = self.partida
        botoes = []
        if p.estado == Partida.ROLAR:
            botoes.append(("Jogar o dado", self.jogar_dado, PAL["sangue"], True))
        if p.estado == Partida.AGIR and p.jogador.no_comodo:
            cid = p.jogador.no_comodo
            botoes.append(("Ver as pistas", lambda: self.abrir_pistas(cid), None, True))
            botoes.append(("Interrogar", self.abrir_interrogatorio, None, p.pode_interrogar))
            botoes.append(("Palpite", self.abrir_palpite, None, p.pode_palpitar))
        botoes.append(("Cartada Final", self.abrir_cartada, PAL["sangue"], p.estado in (Partida.ROLAR, Partida.AGIR)))
        if p.estado != Partida.ROLAR:
            botoes.append(("Encerrar a vez", self.encerrar_vez, PAL["linha"], p.estado == Partida.AGIR))
        largura = LARGURA - PX - 32
        y = BY + TAB_A - 12 - len(botoes) * 48
        for texto, acao, cor, ativo in botoes:
            self.botoes.append(Botao((PX + 8, y, largura, 42), texto, acao, cor=cor, ativo=ativo))
            y += 48

    # ------------------------------------------------------------------ janelas (modais)
    def desenhar_modal(self):
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 170))
        self.tela.blit(veu, (0, 0))
        tipo = self.modal["tipo"]
        getattr(self, f"modal_{tipo}")()

    def caixa(self, largura, altura, titulo, borda=None):
        r = pygame.Rect(0, 0, largura, altura)
        r.center = (LARGURA // 2, ALTURA // 2)
        painel(self.tela, r, borda=borda or PAL["dourado"], raio=14)
        escrever(self.tela, titulo, self.f_sub, BRANCO_SUAVE, (r.left + 28, r.top + 22))
        return r

    def fechar_modal(self):
        self.modal = None

    def modal_pistas(self):
        cid = self.modal["comodo"]
        r = self.caixa(960, 480, f"Você está {self.no_na(cid)}")
        self.tela.blit(self.img.escala(self.img.comodos[cid], (330, 330)), (r.left + 28, r.top + 72))
        y = r.top + 76
        escrever(self.tela, "PISTAS QUE VOCÊ ENCONTROU", self.f_maq, PAL["dourado"], (r.left + 384, y))
        y += 32
        for pista in self.partida.pistas_do_comodo(cid):
            self.tela.blit(self.img.lupa, (r.left + 380, y))
            y = escrever(self.tela, pista["texto"], self.f_txt, BRANCO_SUAVE, (r.left + 426, y + 4), largura=500) + 18
        self.botoes.append(Botao((r.right - 200, r.bottom - 64, 172, 44), "Continuar", self.fechar_modal, cor=PAL["sangue"]))

    def grade_escolha(self, r, y, ids, imagens, chave, tam=72, nomes=None):
        """Linha de opções clicáveis (suspeitos, armas ou cômodos)."""
        mouse = pygame.mouse.get_pos()
        for i, item in enumerate(ids):
            caixa = pygame.Rect(r.left + 28 + i * (tam + 26), y, tam + 16, tam + 40)
            sel = self.modal.get(chave) == item
            if sel or caixa.collidepoint(mouse):
                pygame.draw.rect(self.tela, PAL["dourado_claro"] if sel else PAL["linha"], caixa, 2, border_radius=8)
            if imagens is not None:
                self.tela.blit(self.img.escala(imagens[item], (tam, tam)), (caixa.left + 8, caixa.top + 4))
            nome = (nomes or {}).get(item, item)
            escrever(self.tela, nome.split()[0], self.f_peq, BRANCO_SUAVE, (caixa.centerx, caixa.top + tam + 10), centro=True)
            self.botoes.append(Botao(caixa, "", lambda item=item: self.modal.__setitem__(chave, item)))

    def nomes_suspeitos(self):
        return {s: self.personagens[s]["nome"] for s in self.partida.caso["suspeitos"]}

    def modal_interrogar(self):
        m = self.modal
        r = self.caixa(980, 580, "Interrogatório: escolha um suspeito e uma pergunta")
        if m["resposta"]:
            per = self.personagens[m["suspeito"]]
            self.tela.blit(self.img.escala(self.img.suspeitos[m["suspeito"]], (170, 170)), (r.left + 32, r.top + 90))
            escrever(self.tela, per["nome"], self.f_sub, BRANCO_SUAVE, (r.left + 230, r.top + 92))
            escrever(self.tela, self.perguntas[m["pergunta"]]["texto"], self.f_txt, CINZA, (r.left + 230, r.top + 134), largura=700)
            escrever(self.tela, f"“{m['resposta']}”", self.f_sub, PAL["dourado_claro"], (r.left + 230, r.top + 200), largura=700, entrelinha=8)
            self.botoes.append(Botao((r.right - 200, r.bottom - 64, 172, 44), "Continuar", self.fechar_modal, cor=PAL["sangue"]))
            return
        sus = self.partida.caso["suspeitos"]
        self.grade_escolha(r, r.top + 70, sus, self.img.suspeitos, "suspeito", 100, self.nomes_suspeitos())
        y = r.top + 250
        escrever(self.tela, "PERGUNTAS SORTEADAS", self.f_maq, PAL["dourado"], (r.left + 28, y))
        for i, q in enumerate(m["perguntas"]):
            def perguntar(q=q):
                if not m["suspeito"]:
                    self.aviso = "Escolha um suspeito primeiro."
                    return
                m["pergunta"] = q["id"]
                m["resposta"] = self.partida.interrogar(m["suspeito"], q["id"])
            self.botoes.append(Botao((r.left + 28, y + 32 + i * 60, r.width - 56, 50), q["texto"], perguntar,
                                     ativo=m["suspeito"] is not None))
        self.botoes.append(Botao((r.left + 28, r.bottom - 60, 140, 40), "Voltar", self.fechar_modal))

    def modal_palpite(self):
        m = self.modal
        p = self.partida
        cid = p.jogador.no_comodo
        if m["resultado"]:
            self.resultado_palpite(m["resultado"], m["suspeito"], m["arma"], cid)
            return
        r = self.caixa(940, 560, f"Palpite: quem foi, e com o quê, aqui {self.no_na(cid)}?")
        escrever(self.tela, "QUEM FOI", self.f_maq, PAL["dourado"], (r.left + 28, r.top + 66))
        self.grade_escolha(r, r.top + 90, p.caso["suspeitos"], self.img.suspeitos, "suspeito", 80, self.nomes_suspeitos())
        escrever(self.tela, "COM QUE ARMA", self.f_maq, PAL["dourado"], (r.left + 28, r.top + 232))
        self.grade_escolha(r, r.top + 256, p.caso["armas"], self.img.armas, "arma", 80,
                           {a: self.armas[a]["nome"] for a in p.caso["armas"]})
        escrever(self.tela, "Errou algum item: perde 1 vida. Acertou os três: caso resolvido.",
                 self.f_peq, CINZA, (r.left + 28, r.bottom - 92))

        def confirmar():
            m["resultado"] = p.palpite(m["suspeito"], m["arma"])
        self.botoes.append(Botao((r.left + 28, r.bottom - 60, 140, 40), "Voltar", self.fechar_modal))
        self.botoes.append(Botao((r.right - 220, r.bottom - 64, 192, 44), "Fazer o palpite", confirmar,
                                 cor=PAL["sangue"], ativo=bool(m["suspeito"] and m["arma"])))

    def resultado_palpite(self, res, sid, aid, cid):
        r = self.caixa(780, 440, "Resultado do palpite (só você está vendo)")
        linhas = [(self.comodos[cid]["nome"], res.comodo), (self.personagens[sid]["nome"], res.suspeito),
                  (self.armas[aid]["nome"], res.arma)]
        for i, (nome, ok) in enumerate(linhas):
            y = r.top + 90 + i * 56
            escrever(self.tela, nome, self.f_sub, BRANCO_SUAVE, (r.left + 60, y))
            escrever(self.tela, "certo" if ok else "errado", self.f_sub,
                     PAL["dourado_claro"] if ok else PAL["vermelho"], (r.left + 420, y))
        if res.resolveu:
            self.botoes.append(Botao((r.right - 220, r.bottom - 64, 192, 44), "Continuar",
                                     lambda: self.modal.update(tipo="fim"), cor=PAL["sangue"]))
            return
        msg = "Você foi eliminado." if res.eliminado else f"Você perdeu 1 vida. Restam {res.vidas_restantes}."
        escrever(self.tela, msg, self.f_txt, PAL["vermelho"], (r.left + 60, r.top + 270))
        acao = self.encerrar_vez if res.eliminado else self.fechar_modal
        self.botoes.append(Botao((r.right - 220, r.bottom - 64, 192, 44), "Continuar", acao, cor=PAL["sangue"]))

    def modal_cartada(self):
        m = self.modal
        p = self.partida
        if m["resultado"] is not None:
            if m["resultado"]:
                self.modal = {"tipo": "fim"}
                return
            r = self.caixa(640, 300, "Cartada Final errada", borda=PAL["vermelho"])
            escrever(self.tela, f"{p.jogador.nome} está eliminado deste caso.", self.f_sub, PAL["vermelho"],
                     (r.left + 28, r.top + 100))
            self.botoes.append(Botao((r.right - 220, r.bottom - 64, 192, 44), "Continuar", self.encerrar_vez, cor=PAL["sangue"]))
            return
        r = self.caixa(960, 700, "Cartada Final: quem, com o quê e onde", borda=PAL["vermelho"])
        self.grade_escolha(r, r.top + 64, p.caso["suspeitos"], self.img.suspeitos, "suspeito", 76, self.nomes_suspeitos())
        self.grade_escolha(r, r.top + 196, p.caso["armas"], self.img.armas, "arma", 76,
                           {a: self.armas[a]["nome"] for a in p.caso["armas"]})
        self.grade_escolha(r, r.top + 328, p.caso["comodos"], self.img.comodos, "comodo", 76,
                           {c: self.comodos[c]["nome"] for c in p.caso["comodos"]})
        escrever(self.tela, "Acertou: vence o caso com +50 pontos. Errou: está eliminado, mesmo com vidas.",
                 self.f_txt, PAL["vermelho"], (r.left + 28, r.bottom - 100))

        def confirmar():
            m["resultado"] = p.cartada_final(m["suspeito"], m["arma"], m["comodo"])
        self.botoes.append(Botao((r.left + 28, r.bottom - 60, 140, 40), "Voltar", self.fechar_modal))
        self.botoes.append(Botao((r.right - 240, r.bottom - 64, 212, 44), "Cartada Final", confirmar,
                                 cor=PAL["sangue"], ativo=bool(m["suspeito"] and m["arma"] and m["comodo"])))

    def modal_fim(self):
        p = self.partida
        s = p.solucao
        venc = p.vencedor
        titulo = "Parabéns! Caso resolvido" if venc else "Caso encerrado"
        r = self.caixa(900, 560, titulo, borda=PAL["dourado_claro"])
        if venc:
            escrever(self.tela, f"{venc.nome} desvendou o mistério e soma {venc.pontos} pontos.",
                     self.f_txt, pygame.Color(venc.hex), (r.left + 28, r.top + 62))
        else:
            escrever(self.tela, "Todos os detetives foram eliminados.", self.f_txt, PAL["vermelho"], (r.left + 28, r.top + 62))
        itens = [(self.img.suspeitos[s["culpado"]], self.personagens[s["culpado"]]["nome"]),
                 (self.img.armas[s["arma"]], self.armas[s["arma"]]["nome"]),
                 (self.img.comodos[s["comodo"]], self.comodos[s["comodo"]]["nome"])]
        for i, (im, nome) in enumerate(itens):
            x = r.left + 100 + i * 260
            self.tela.blit(self.img.escala(im, (160, 160)), (x, r.top + 110))
            escrever(self.tela, nome, self.f_sub, BRANCO_SUAVE, (x + 80, r.top + 282), centro=True)
        mentiras = [q for q, resp in p.caso["respostas"][s["culpado"]].items() if not resp["verdade"]]
        escrever(self.tela, f"{self.personagens[s['culpado']]['nome'].split()[0]} mentiu {len(mentiras)} vezes no interrogatório.",
                 self.f_txt, CINZA, (r.left + 28, r.top + 340))
        placar = "   ".join(f"{j.nome}: {j.pontos}" for j in self.jogadores)
        escrever(self.tela, "Placar — " + placar, self.f_txt, PAL["dourado_claro"], (r.left + 28, r.top + 378))

        def proximo():
            self.modal = None
            self.novo_caso()
        self.botoes.append(Botao((r.right - 220, r.bottom - 64, 192, 44), "Próximo caso", proximo, cor=PAL["sangue"]))


if __name__ == "__main__":
    Jogo().rodar()

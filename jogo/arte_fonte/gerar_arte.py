"""Gera a arte do Quem Foi? em SVG e exporta PNGs transparentes com o Chromium.

Uso: python arte.py <pasta_saida>
"""
import os, sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = sys.argv[1]

# Paleta (igual a dados/paleta.json)
BG = "#0B0D12"; PAINEL = "#141821"; LINHA = "#2C3240"
TXT = "#ECE3CF"; SUAVE = "#B9B09D"; OURO = "#D0AC6C"; OURO2 = "#E6C88C"
SANGUE = "#A8222E"; VERM = "#D4404C"; AZUL = "#4A7FD4"; VERDE = "#4FAE6A"
MADEIRA = "#2A2118"; MADEIRA2 = "#3A2D1F"; PEDRA = "#23262D"; SILH = "#05060A"

assets = {}  # caminho relativo -> (svg, largura, altura)


def add(path, w, h, body, defs="", render=None):
    """w, h = tamanho do desenho; render = tamanho do PNG final (o SVG escala sem borrar)."""
    rw, rh = render or (w, h)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{rw}" height="{rh}" viewBox="0 0 {w} {h}"><defs>{defs}</defs>{body}</svg>'
    assets[path] = (svg, rw, rh)


# ---------------------------------------------------------------- padrões de piso
PADROES = f"""
<pattern id="madeira" width="48" height="12" patternUnits="userSpaceOnUse">
  <rect width="48" height="12" fill="{MADEIRA}"/><path d="M0 12H48M16 0V12" stroke="#1E1811" stroke-width="1.5"/>
  <path d="M40 0V12" stroke="#1E1811" stroke-width="1" opacity=".5"/></pattern>
<pattern id="ladrilho" width="24" height="24" patternUnits="userSpaceOnUse">
  <rect width="24" height="24" fill="#1A1E27"/><rect width="12" height="12" fill="#232836"/><rect x="12" y="12" width="12" height="12" fill="#232836"/></pattern>
<pattern id="pedra" width="32" height="20" patternUnits="userSpaceOnUse">
  <rect width="32" height="20" fill="{PEDRA}"/><path d="M0 10H32M0 20H32M8 0V10M24 10V20" stroke="#15171C" stroke-width="2"/></pattern>
<pattern id="grama" width="16" height="16" patternUnits="userSpaceOnUse">
  <rect width="16" height="16" fill="#101A13"/><path d="M3 6l1-3 1 3M11 14l1-3 1 3" stroke="#1C2E21" stroke-width="1.2" fill="none"/></pattern>
<pattern id="tapete" width="20" height="20" patternUnits="userSpaceOnUse">
  <rect width="20" height="20" fill="#2A1519"/><path d="M10 2l8 8-8 8-8-8z" fill="none" stroke="#3A1E24" stroke-width="1.5"/></pattern>
<pattern id="carpete" width="12" height="12" patternUnits="userSpaceOnUse">
  <rect width="12" height="12" fill="#161C2A"/><circle cx="6" cy="6" r="1.2" fill="#1F2738"/></pattern>
<pattern id="corredor" width="64" height="16" patternUnits="userSpaceOnUse">
  <rect width="64" height="16" fill="#191510"/><path d="M0 16H64M24 0V16" stroke="#120F0B" stroke-width="1.5"/></pattern>
<pattern id="marmore" width="32" height="32" patternUnits="userSpaceOnUse">
  <rect width="32" height="32" fill="#2B2E36"/><path d="M0 32L32 0" stroke="#34383F" stroke-width="1"/><path d="M0 0H32V32" fill="none" stroke="#22252B" stroke-width="1.5"/></pattern>
<radialGradient id="luz" cx="50%" cy="45%" r="60%"><stop offset="0" stop-color="{OURO2}" stop-opacity=".20"/><stop offset="1" stop-color="{OURO2}" stop-opacity="0"/></radialGradient>
<radialGradient id="vinheta" cx="50%" cy="50%" r="72%"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
"""


# ---------------------------------------------------------------- cômodos (192x192, vistos de cima)
def comodo(piso, moveis, luz=True):
    return (f'<rect width="192" height="192" fill="url(#{piso})"/>{moveis}'
            + ('<rect width="192" height="192" fill="url(#luz)"/>' if luz else '')
            + '<rect width="192" height="192" fill="url(#vinheta)"/>'
            + f'<rect x="2" y="2" width="188" height="188" fill="none" stroke="#6A6658" stroke-width="4"/>')


def livros(x, y, w, h, vertical=False):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#1B140D" stroke="#4A3A26" stroke-width="1.5"/>'
    cores = ["#5A2A2E", "#2E3E5A", "#4A4026", "#2F4A36", "#5A4A30"]
    n = int((h if vertical else w) // 7)
    for i in range(n):
        c = cores[i % 5]
        if vertical:
            s += f'<rect x="{x+3}" y="{y+2+i*7}" width="{w-6}" height="5" fill="{c}"/>'
        else:
            s += f'<rect x="{x+2+i*7}" y="{y+3}" width="5" height="{h-6}" fill="{c}"/>'
    return s


MOVEIS = {
 "l01": ("madeira",  # Biblioteca
   livros(10, 8, 172, 18) + livros(8, 30, 18, 110, True)
   + '<rect x="70" y="150" width="54" height="30" fill="#2B1F14" stroke="#5A4630"/><path d="M78 150v-8h38v8" fill="#1A120B" stroke="#5A4630"/>'
   + f'<circle cx="97" cy="160" r="6" fill="{SANGUE}" opacity=".85"/>'
   + '<rect x="96" y="70" width="52" height="44" rx="10" fill="#3B1F22" stroke="#5E3236" stroke-width="2"/><rect x="104" y="78" width="36" height="28" rx="6" fill="#4A272B"/>'
   + '<circle cx="66" cy="94" r="12" fill="#2B1F14" stroke="#5A4630" stroke-width="2"/><rect x="62" y="84" width="4" height="10" fill="#5B3E1F"/><circle cx="70" cy="96" r="3" fill="#9FB3C8" opacity=".7"/>'),
 "l05": ("carpete",  # Escritório
   '<rect x="40" y="56" width="112" height="48" fill="#2B1F14" stroke="#5A4630" stroke-width="2"/><rect x="50" y="64" width="34" height="22" fill="#D9D0BC" opacity=".55"/><rect x="92" y="66" width="22" height="16" fill="#D9D0BC" opacity=".4"/>'
   + '<circle cx="96" cy="122" r="14" fill="#1C1C22" stroke="#3A3A44" stroke-width="2"/>'
   + '<rect x="150" y="10" width="34" height="34" rx="3" fill="#3A3D45" stroke="#5A5E68" stroke-width="2"/><circle cx="167" cy="27" r="7" fill="none" stroke="#8A8F9A" stroke-width="2"/>'
   + '<rect x="8" y="140" width="30" height="44" fill="#2A2D33" stroke="#4A4E58" stroke-width="2"/><path d="M12 154h22M12 168h22" stroke="#4A4E58" stroke-width="2"/>'
   + '<rect x="56" y="10" width="60" height="16" fill="#1B140D" stroke="#4A3A26"/>'),
 "l06": ("pedra",  # Adega
   ''.join(f'<rect x="{8+i*46}" y="8" width="40" height="70" fill="#1E140C" stroke="#4A3420" stroke-width="2"/>'
           + ''.join(f'<circle cx="{18+i*46+(k%2)*20}" cy="{20+(k//2)*16}" r="6" fill="#3A1418" stroke="#5E2228"/>' for k in range(8)) for i in range(4))
   + '<circle cx="40" cy="128" r="22" fill="#4A3420" stroke="#2B1D10" stroke-width="4"/><circle cx="40" cy="128" r="14" fill="none" stroke="#2B1D10" stroke-width="3"/>'
   + '<circle cx="88" cy="150" r="18" fill="#4A3420" stroke="#2B1D10" stroke-width="4"/>'
   + ''.join(f'<rect x="140" y="{100+i*14}" width="44" height="12" fill="#2E3138" stroke="#16181D"/>' for i in range(6))),
 "l02": ("ladrilho",  # Cozinha
   '<rect x="6" y="6" width="180" height="30" fill="#C8C2B4" opacity=".75"/><rect x="6" y="6" width="30" height="120" fill="#C8C2B4" opacity=".75"/>'
   + '<rect x="120" y="10" width="40" height="22" fill="#2A2D33"/>' + ''.join(f'<circle cx="{130+(k%2)*20}" cy="{16+(k//2)*10}" r="4" fill="none" stroke="{VERM}" stroke-width="1.5" opacity=".8"/>' for k in range(4))
   + '<rect x="50" y="12" width="18" height="16" fill="#3B2A18"/><path d="M54 12v-4M59 12v-6M64 12v-4" stroke="#B9B09D" stroke-width="2"/>'
   + '<rect x="70" y="96" width="76" height="52" rx="4" fill="#3B2A18" stroke="#5A4630" stroke-width="2"/>'
   + ''.join(f'<rect x="{x}" y="{y}" width="16" height="16" rx="3" fill="#2B1F14"/>' for x, y in [(76, 78), (124, 78), (76, 152), (124, 152)])),
 "l04": ("tapete",  # Sala de Estar
   '<rect x="20" y="20" width="70" height="30" rx="8" fill="#3B1F22" stroke="#5E3236" stroke-width="2"/><rect x="20" y="140" width="70" height="30" rx="8" fill="#3B1F22" stroke="#5E3236" stroke-width="2"/>'
   + '<rect x="40" y="76" width="44" height="40" rx="4" fill="#2B1F14" stroke="#5A4630"/>'
   + '<path d="M118 112h60v52c-20 0-40-10-60-22z" fill="#0F0F12" stroke="#3A3A44" stroke-width="2"/><rect x="120" y="112" width="58" height="10" fill="#E8E2D2"/>'
   + ''.join(f'<rect x="{122+i*6}" y="112" width="3" height="6" fill="#0F0F12"/>' for i in range(9))
   + '<rect x="150" y="14" width="30" height="76" fill="#2B1F14" stroke="#5A4630"/>'
   + f'<circle cx="165" cy="32" r="6" fill="none" stroke="{OURO2}" stroke-width="2"/><circle cx="165" cy="72" r="6" fill="none" stroke="{OURO2}" stroke-width="2"/>'),
 "l03": ("grama",  # Jardim
   '<path d="M96 192C96 150 70 120 60 70S70 20 96 0" stroke="#3A3A33" stroke-width="22" fill="none" stroke-linecap="round"/>'
   + ''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#0C150F" stroke="#1F3326" stroke-width="2"/>' for x, y, r in [(150, 40, 20), (170, 80, 16), (24, 150, 18), (150, 160, 22)])
   + '<rect x="120" y="110" width="50" height="34" fill="#1C2420" stroke="#9FB3A2" stroke-width="1.5" opacity=".7"/><path d="M120 127h50M145 110v34" stroke="#9FB3A2" stroke-width="1" opacity=".6"/>'
   + '<rect x="8" y="10" width="40" height="34" fill="#3B2A18" stroke="#5A4630" stroke-width="2"/><path d="M8 10l20-8 20 8" fill="#2B1F14" stroke="#5A4630"/>'
   + '<rect x="18" y="96" width="36" height="12" fill="#4A3420"/>'
   + ''.join(f'<ellipse cx="{x}" cy="{y}" rx="3" ry="5" fill="#6B5A3E" opacity=".9"/>' for x, y in [(78, 96), (86, 110), (80, 124)])),
}
for cid, (piso, moveis) in MOVEIS.items():
    add(f"comodos/{cid}.png", 192, 192, comodo(piso, moveis), PADROES, render=(384, 384))


# ---------------------------------------------------------------- tabuleiro completo, lido de dados/tabuleiro.json
DADOS = Path(__file__).resolve().parent.parent.parent / "dados"
TAB = json.loads((DADOS / "tabuleiro.json").read_text(encoding="utf-8"))
COMS = json.loads((DADOS / "comodos.json").read_text(encoding="utf-8"))
C = TAB["tamanho_casa_px"]
W, H = TAB["largura"] * C, TAB["altura"] * C
corpo = f'<rect width="{W}" height="{H}" fill="url(#corredor)"/>'
for lin, row in enumerate(TAB["mapa"]):
    for col, ch in enumerate(row):
        if ch == ".":
            corpo += f'<rect x="{col*C+1}" y="{lin*C+1}" width="{C-2}" height="{C-2}" fill="none" stroke="#2C251C" stroke-width="1.2"/>'


def area_px(a):
    return a["col"] * C, a["lin"] * C, a["largura"] * C, a["altura"] * C


# saguão: mármore com a mesa do caso no meio
x, y, w, h = area_px(TAB["saguao"]["area"])
corpo += (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#marmore)"/>'
          f'<rect x="{x+3}" y="{y+3}" width="{w-6}" height="{h-6}" fill="none" stroke="{OURO}" stroke-width="2"/>'
          f'<rect x="{x+w/2-50}" y="{y+h/2-24}" width="100" height="48" rx="4" fill="#2B1F14" stroke="{OURO}" stroke-width="1.5"/>'
          f'<rect x="{x+w/2-26}" y="{y+h/2-15}" width="40" height="30" fill="#D9D0BC" opacity=".6" transform="rotate(-8 {x+w/2-6} {y+h/2})"/>'
          f'<text x="{x+w/2}" y="{y+h-10}" text-anchor="middle" font-family="Caladea, Georgia, serif" font-size="15" fill="{OURO2}" letter-spacing="3">SAGUÃO</text>')
# obstáculos: escadaria e relógio de pêndulo
for ob in TAB.get("obstaculos", []):
    x, y, w, h = area_px(ob["area"])
    corpo += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#marmore)"/><rect x="{x+2}" y="{y+2}" width="{w-4}" height="{h-4}" fill="none" stroke="#6A6658" stroke-width="2"/>'
    if ob["sigla"] == "X":   # degraus
        for k in range(7):
            corpo += f'<rect x="{x+12}" y="{y+12+k*15}" width="{w-24}" height="12" fill="#3A3D45" stroke="#1B1D22" stroke-width="1.5"/>'
    else:                   # relógio visto de cima
        cx, cy = x + w / 2, y + h / 2 - 6
        corpo += (f'<rect x="{cx-30}" y="{cy-40}" width="60" height="80" rx="6" fill="#2B1F14" stroke="#5A4630" stroke-width="2"/>'
                  f'<circle cx="{cx}" cy="{cy-8}" r="22" fill="#E8E2D2" opacity=".85"/><path d="M{cx} {cy-8}V{cy-24}M{cx} {cy-8}L{cx+12} {cy-2}" stroke="#14110C" stroke-width="3"/>')
    corpo += f'<text x="{x+w/2}" y="{y+h-8}" text-anchor="middle" font-family="Carlito, Arial, sans-serif" font-size="13" fill="{SUAVE}">{ob["nome"]}</text>'
# cômodos: a mesma arte de 192x192, recortada para o tamanho do cômodo
for cm in COMS:
    piso, moveis = MOVEIS[cm["id"]]
    x, y, w, h = area_px(cm["area"])
    corpo += (f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 192 192" preserveAspectRatio="xMidYMid slice">'
              f'{comodo(piso, moveis)}</svg>'
              f'<rect x="{x+2}" y="{y+2}" width="{w-4}" height="{h-4}" fill="none" stroke="#6A6658" stroke-width="4"/>')
# portas: barra dourada na parede + seta na casa da porta
for cm in COMS:
    a, pt = cm["area"], cm["porta"]
    px, py = pt["col"] * C, pt["lin"] * C
    acima = pt["lin"] >= a["lin"] + a["altura"]   # porta embaixo do cômodo: seta para cima
    by = py - 6 if acima else py + C - 2
    corpo += f'<rect x="{px+8}" y="{by}" width="{C-16}" height="8" fill="{OURO}"/>'
    cx, cy = px + C / 2, py + C / 2
    d = f"M{cx-7} {cy+3}L{cx} {cy-5}L{cx+7} {cy+3}" if acima else f"M{cx-7} {cy-3}L{cx} {cy+5}L{cx+7} {cy-3}"
    corpo += f'<path d="{d}" fill="none" stroke="{OURO}" stroke-width="2.5" opacity=".75"/>'
corpo += f'<rect x="1" y="1" width="{W-2}" height="{H-2}" fill="none" stroke="#6A6658" stroke-width="2"/>'
add("tabuleiro.png", W, H, corpo, PADROES)  # 1 pixel por pixel: casas de 46px


# ---------------------------------------------------------------- retratos (160x160): silhueta noir + detalhe de cada um
def retrato(cabeca, extra, borda=OURO):
    fundo = (f'<circle cx="80" cy="80" r="78" fill="url(#fundoR)"/>'
             f'<clipPath id="clip"><circle cx="80" cy="80" r="76"/></clipPath>')
    corpo_ = '<path d="M22 170c0-34 26-58 58-58s58 24 58 58z" fill="#05060A"/>'
    return (fundo + f'<g clip-path="url(#clip)">{corpo_}{cabeca}{extra}</g>'
            + f'<circle cx="80" cy="80" r="77" fill="none" stroke="{borda}" stroke-width="3"/>')


DEF_R = (f'<radialGradient id="fundoR" cx="50%" cy="38%" r="65%"><stop offset="0" stop-color="#3A3F4D"/>'
         f'<stop offset="1" stop-color="{BG}"/></radialGradient>')
cab = '<ellipse cx="80" cy="74" rx="24" ry="28" fill="#05060A"/>'
RETRATOS = {
 "p01": cab + '<circle cx="80" cy="40" r="15" fill="#05060A"/>',  # Helena: coque
 "p02": cab + '<path d="M50 52h60l-6-18H56z" fill="#05060A"/><rect x="44" y="50" width="72" height="6" rx="3" fill="#05060A"/>',  # Marcos: chapéu
 "p03": '<path d="M54 76c0-22 12-36 26-36s26 14 26 36c0 10-4 18-8 22H62c-4-4-8-12-8-22z" fill="#05060A"/>',  # Rita: cabelo curto
 "p04": cab,  # Otávio
 "p05": cab + '<path d="M54 60l6-18 8 10 6-14 8 12 8-12 4 14 8-6 2 16z" fill="#05060A"/>',  # Bruno: cabelo bagunçado
 "p06": cab + '<ellipse cx="74" cy="48" rx="28" ry="10" fill="#05060A" transform="rotate(-10 74 48)"/><circle cx="62" cy="40" r="4" fill="#05060A"/>',  # Clara: boina
 "p07": cab + '<ellipse cx="80" cy="52" rx="44" ry="8" fill="#05060A"/><path d="M60 52c0-14 8-22 20-22s20 8 20 22z" fill="#05060A"/>',  # Jonas: chapéu de palha
 "p08": '<path d="M52 92V66c0-20 12-32 28-32s28 12 28 32v26H96V70H64v22z" fill="#05060A"/>' + cab,  # Lívia: chanel
}
EXTRAS = {
 "p01": ''.join(f'<circle cx="{60+i*5}" cy="{112+abs(4-i)*-1.2+5}" r="2.6" fill="#E8E2D2"/>' for i in range(9)),  # pérolas
 "p02": f'<rect x="96" y="92" width="26" height="5" rx="2" fill="#6B4A2A" transform="rotate(-12 96 92)"/><circle cx="121" cy="87" r="2.5" fill="{VERM}"/>'
        + '<path d="M124 82c4-6 0-10 4-16" stroke="#9AA0AA" stroke-width="2" fill="none" opacity=".7"/>',  # charuto
 "p03": f'<path d="M68 128h24v42H68z" fill="#E8E2D2" opacity=".85"/><circle cx="106" cy="128" r="7" fill="none" stroke="{OURO2}" stroke-width="2.5"/><path d="M110 132l6 6M104 134l2 8" stroke="{OURO2}" stroke-width="2"/>',  # avental e chaves
 "p04": f'<circle cx="71" cy="72" r="7" fill="none" stroke="{OURO2}" stroke-width="2"/><circle cx="89" cy="72" r="7" fill="none" stroke="{OURO2}" stroke-width="2"/><path d="M78 72h4" stroke="{OURO2}" stroke-width="2"/>'
        + '<rect x="98" y="134" width="34" height="24" rx="3" fill="#4A2E1A" stroke="#6B4A2A" stroke-width="2"/><path d="M108 134v-5h14v5" fill="none" stroke="#6B4A2A" stroke-width="2"/>',  # óculos e maleta
 "p05": '<path d="M44 140l20-26 16 18 16-18 20 26" fill="none" stroke="#3A3F4D" stroke-width="3"/>',  # gola da jaqueta
 "p06": f'<rect x="96" y="128" width="24" height="30" rx="2" fill="{SANGUE}" stroke="#D4404C" stroke-width="1.5"/>',  # caderno vermelho
 "p07": '<path d="M44 52h72" stroke="#C9A85A" stroke-width="2" opacity=".6"/>',  # palha
 "p08": f'<path d="M94 134c6-10 16-12 22-6l-4 14h-16z" fill="#2B1F14" stroke="{OURO}" stroke-width="1.5"/>',  # luvas
}
for pid in RETRATOS:
    add(f"suspeitos/{pid}.png", 160, 160, retrato(RETRATOS[pid], EXTRAS[pid]), DEF_R, render=(192, 192))

# detetives: retrato com chapéu fedora e gola de sobretudo, borda na cor do peão
DET = {"d1": VERM, "d2": AZUL, "d3": VERDE}
fedora = ('<path d="M54 54h52l-6-20c-8-4-32-4-40 0z" fill="#05060A"/><ellipse cx="80" cy="56" rx="40" ry="7" fill="#05060A"/>'
          '<path d="M30 170l20-56 30 26 30-26 20 56z" fill="#0A0C12" stroke="#2C3240" stroke-width="2"/>')
for did, cor in DET.items():
    add(f"detetives/{did}_retrato.png", 160, 160,
        retrato(cab + fedora, f'<rect x="54" y="48" width="52" height="5" fill="{cor}"/>', borda=cor), DEF_R, render=(192, 192))
    # peão visto de cima: ficha com chapéu
    add(f"detetives/{did}_peao.png", 48, 48,
        f'<circle cx="24" cy="26" r="20" fill="#000" opacity=".45"/>'
        f'<circle cx="24" cy="24" r="20" fill="{cor}" stroke="{TXT}" stroke-width="2"/>'
        f'<circle cx="24" cy="24" r="13" fill="#141821"/><circle cx="24" cy="24" r="7" fill="{cor}" opacity=".9"/>'
        f'<circle cx="24" cy="24" r="13" fill="none" stroke="#000" stroke-width="1.5" opacity=".6"/>', render=(64, 64))


# ---------------------------------------------------------------- armas (96x96, traço dourado)
def icone(body):
    return f'<g fill="none" stroke="{OURO2}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{body}</g>'


ARMAS = {
 "a01": f'<path d="M38 14h20M41 14v18L28 52a20 20 0 0 0 16 30h8a20 20 0 0 0 16-30L55 32V14"/><path d="M30 60h36" stroke="{VERM}"/>'
        f'<circle cx="44" cy="68" r="3" fill="{VERM}" stroke="none"/><circle cx="54" cy="73" r="2" fill="{VERM}" stroke="none"/>',
 "a02": '<path d="M18 78L62 34l14-14-4 18-44 44z"/><path d="M14 82l10-10"/><path d="M30 66l8 8" stroke-width="3"/>',
 "a03": '<ellipse cx="48" cy="50" rx="30" ry="22"/><ellipse cx="48" cy="50" rx="20" ry="13"/><ellipse cx="48" cy="50" rx="9" ry="5"/><path d="M76 58c10 10 6 22-4 24"/>',
 "a04": '<path d="M12 34h56v14H40l-6 30H20l6-30H12z"/><path d="M68 38h14"/><circle cx="46" cy="44" r="5"/><path d="M36 48l4 10h8"/>',
 "a05": f'<path d="M48 10c5 6 5 10 0 13-5-3-5-7 0-13z" fill="{OURO}" stroke="{OURO}"/><path d="M42 26h12v20H42z"/><path d="M24 46h48M48 46v28M32 86h32l-6-12H38z"/><path d="M24 46v-12M72 46v-12"/>',
 "a06": '<circle cx="28" cy="70" r="12"/><circle cx="68" cy="70" r="12"/><path d="M36 61L70 16M60 61L26 16"/>',
}
for aid, body in ARMAS.items():
    add(f"armas/{aid}.png", 96, 96, icone(body))


# ---------------------------------------------------------------- dado (96x96, 6 faces)
PIPS = {1: [(48, 48)], 2: [(30, 30), (66, 66)], 3: [(28, 28), (48, 48), (68, 68)],
        4: [(30, 30), (66, 30), (30, 66), (66, 66)], 5: [(28, 28), (68, 28), (48, 48), (28, 68), (68, 68)],
        6: [(30, 26), (66, 26), (30, 48), (66, 48), (30, 70), (66, 70)]}
DEF_DADO = '<linearGradient id="marfim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3ECDB"/><stop offset="1" stop-color="#CFC4AA"/></linearGradient>'
for n, pts in PIPS.items():
    pips = ''.join(f'<circle cx="{x}" cy="{y}" r="8" fill="{SANGUE if n == 1 else "#14110C"}"/>' for x, y in pts)
    add(f"dado/{n}.png", 96, 96,
        f'<rect x="6" y="9" width="84" height="84" rx="16" fill="#000" opacity=".45"/>'
        f'<rect x="6" y="6" width="84" height="84" rx="16" fill="url(#marfim)" stroke="#8C7F62" stroke-width="2"/>{pips}', DEF_DADO)


# ---------------------------------------------------------------- interface: vida, lupa
CORACAO = "M24 42s-15-9.2-19-18.8C2 16 6.4 9 13.4 9c4.2 0 7.6 2.4 10.6 6.2C27 11.4 30.4 9 34.6 9 41.6 9 46 16 43 23.2 39 32.8 24 42 24 42z"
add("ui/vida_cheia.png", 48, 48, f'<path d="{CORACAO}" fill="{VERM}" stroke="#F08A92" stroke-width="1.5"/>')
add("ui/vida_vazia.png", 48, 48, f'<path d="{CORACAO}" fill="none" stroke="#5A5560" stroke-width="2.5"/>')
add("ui/lupa.png", 48, 48, f'<circle cx="20" cy="20" r="13" fill="{SANGUE}" fill-opacity=".3" stroke="{OURO2}" stroke-width="4"/><path d="M30 30l13 13" stroke="{OURO2}" stroke-width="6" stroke-linecap="round"/>')


# ---------------------------------------------------------------- exportar
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(device_scale_factor=1)
    for path, (svg, w, h) in assets.items():
        dest = os.path.join(OUT, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        pg.set_viewport_size({"width": w, "height": h})
        pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
        pg.locator("body > svg").screenshot(path=dest, omit_background=True)
        with open(dest.replace(".png", ".svg"), "w", encoding="utf-8") as f:
            f.write(svg)
    b.close()
print(len(assets), "imagens")

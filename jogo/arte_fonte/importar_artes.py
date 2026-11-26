"""Transforma as imagens geradas pelo grupo no Gemini (pasta ia/) na arte do jogo (jogo/assets/).

- recorta bordas brancas que o Gemini às vezes deixa
- retratos (suspeitos e detetives) e armas: quadrado com cantos arredondados e moldura
- cômodos: quadrado para a janela de pistas
- tabuleiro.png: refeito com as salas, o saguão, a escadaria e o relógio novos,
  mantendo corredor, portas e setas no lugar certo (lido de dados/tabuleiro.json e comodos.json)

Os peões e o dado continuam com a arte desenhada em código (gerar_arte.py).

Uso: python jogo/arte_fonte/importar_artes.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

AQUI = Path(__file__).resolve().parent
FONTE = AQUI / "ia"
ASSETS = AQUI.parent / "assets"
DADOS = AQUI.parent.parent / "dados"

OURO = (208, 172, 108)
OURO2 = (230, 200, 140)
MOLDURA = (106, 102, 88)
FUNDO = (11, 13, 18)
COR_DET = {"d1": (212, 64, 76), "d2": (74, 127, 212), "d3": (79, 174, 106)}


def abrir(nome: str, zoom: float = 1.0) -> Image.Image:
    arq = next(FONTE.glob(nome + ".*"))
    img = Image.open(arq).convert("RGB")
    cinza = img.convert("L")
    # moldura branca (às vezes com sombra) em volta da arte: corta até a parte escura
    anel = [cinza.getpixel((x, y)) for x in range(0, img.width, 16) for y in (2, img.height - 3)]
    anel += [cinza.getpixel((x, y)) for y in range(0, img.height, 16) for x in (2, img.width - 3)]
    if sum(anel) / len(anel) > 170:
        caixa = cinza.point(lambda v: 255 if v < 110 else 0).getbbox()
        if caixa:
            m = 8
            img = img.crop((caixa[0] + m, caixa[1] + m, caixa[2] - m, caixa[3] - m))
    if zoom > 1:   # aproxima o centro (objetos pequenos nos ícones)
        w, h = img.size
        cw, ch = w / zoom, h / zoom
        img = img.crop(((w - cw) / 2, (h - ch) / 2, (w + cw) / 2, (h + ch) / 2))
    return img


def cartao(img: Image.Image, lado: int, cor=OURO, borda=4, raio=None) -> Image.Image:
    """Quadrado com cantos arredondados e moldura, fundo transparente."""
    raio = raio if raio is not None else lado // 12
    k = 3  # desenha maior e reduz: bordas suaves
    L = lado * k
    foto = ImageOps.fit(img, (L, L), Image.LANCZOS, centering=(0.5, 0.42))
    mascara = Image.new("L", (L, L), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, L - 1, L - 1), raio * k, fill=255)
    saida = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    saida.paste(foto, (0, 0), mascara)
    ImageDraw.Draw(saida).rounded_rectangle((0, 0, L - 1, L - 1), raio * k, outline=cor + (255,), width=borda * k)
    return saida.resize((lado, lado), Image.LANCZOS)


def salvar(img, rel):
    destino = ASSETS / rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino)
    print("ok", rel, img.size)


# ---------------------------------------------------------------- retratos, armas e cômodos
for i in range(1, 9):
    salvar(cartao(abrir(f"p0{i}"), 256), f"suspeitos/p0{i}.png")
for d, cor in COR_DET.items():
    salvar(cartao(abrir(d), 256, cor=cor, borda=5), f"detetives/{d}_retrato.png")
for i in range(1, 7):
    salvar(cartao(abrir(f"a0{i}", zoom=1.25), 160, borda=3), f"armas/a0{i}.png")
for i in range(1, 7):
    salvar(cartao(abrir(f"l0{i}"), 384, cor=MOLDURA, borda=4, raio=14), f"comodos/l0{i}.png")

# ---------------------------------------------------------------- tabuleiro
TAB = json.loads((DADOS / "tabuleiro.json").read_text(encoding="utf-8"))
COMS = json.loads((DADOS / "comodos.json").read_text(encoding="utf-8"))
COMS = COMS["comodos"] if isinstance(COMS, dict) else COMS
C = TAB["tamanho_casa_px"]
W, H = TAB["largura"] * C, TAB["altura"] * C


def area_px(a):
    return a["col"] * C, a["lin"] * C, a["largura"] * C, a["altura"] * C


def fonte(nome, tam):
    for arq in (nome, "DejaVuSerif.ttf"):
        try:
            return ImageFont.truetype(arq, tam)
        except OSError:
            continue
    return ImageFont.load_default()


# corredor: o piso de tacos escuros do tabuleiro antigo continua igual
base = Image.open(AQUI / "tabuleiro_corredor.png").convert("RGB") if (AQUI / "tabuleiro_corredor.png").exists() \
    else Image.open(ASSETS / "tabuleiro.png").convert("RGB")
if not (AQUI / "tabuleiro_corredor.png").exists():
    base.save(AQUI / "tabuleiro_corredor.png")   # guarda o original para poder rodar de novo
tab = base.copy()
d = ImageDraw.Draw(tab)


def pintar(img, x, y, w, h, cor=MOLDURA, borda=4, centro=(0.5, 0.5)):
    tab.paste(ImageOps.fit(img, (w, h), Image.LANCZOS, centering=centro), (x, y))
    d.rectangle((x + 1, y + 1, x + w - 2, y + h - 2), outline=cor, width=borda)


def plaquinha(texto, cx, base_y, tam=13, cor=OURO2, espaco=0):
    f = fonte("Caladea-Bold.ttf", tam)
    texto = " ".join(texto) if espaco else texto
    l, t, r, b = d.textbbox((0, 0), texto, font=f)
    w, h = r - l + 14, b - t + 8
    caixa = Image.new("RGBA", (w, h), FUNDO + (200,))
    tab.paste(caixa, (int(cx - w / 2), int(base_y - h)), caixa)
    d.text((cx, base_y - h / 2), texto, font=f, fill=cor, anchor="mm")


x, y, w, h = area_px(TAB["saguao"]["area"])
pintar(abrir("saguao"), x, y, w, h, cor=OURO, borda=3)
plaquinha("SAGUÃO", x + w / 2, y + h - 6, 14, espaco=1)

for ob in TAB.get("obstaculos", []):
    x, y, w, h = area_px(ob["area"])
    pintar(abrir("escadaria" if ob["sigla"] == "X" else "relogio"), x, y, w, h)
    plaquinha(ob["nome"], x + w / 2, y + h - 6, 12, cor=(205, 196, 178))

for cm in COMS:
    x, y, w, h = area_px(cm["area"])
    pintar(abrir(cm["id"]), x, y, w, h)

# portas: barra dourada na parede (a seta no corredor já está no piso)
for cm in COMS:
    a, pt = cm["area"], cm["porta"]
    px, py = pt["col"] * C, pt["lin"] * C
    acima = pt["lin"] >= a["lin"] + a["altura"]
    by = py - 6 if acima else py + C - 2
    d.rectangle((px + 8, by, px + C - 8, by + 8), fill=OURO)

d.rectangle((1, 1, W - 2, H - 2), outline=MOLDURA, width=2)
salvar(tab, "tabuleiro.png")

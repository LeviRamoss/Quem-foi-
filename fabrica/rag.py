"""RAG do Quem Foi?: busca trechos das 24 fichas para dar contexto à IA.

Funciona sem internet e sem instalar nada (só a biblioteca padrão do Python):

- Fontes: base_conhecimento/ (8 personagens, 6 locais, 6 armas, 4 guias).
- Chunking: cada ficha vira 1 trecho; os guias são divididos por seção ou parágrafo.
- Vetores: TF-IDF com acentos removidos (palavra -> peso).
- Banco vetorial: fabrica/indice_vetorial.json (criado por `python fabrica/rag.py --indexar`).
- Busca: filtro pelos itens sorteados no caso + similaridade de cosseno com a pergunta.

Uso:
    python fabrica/rag.py --indexar
    python fabrica/rag.py "álibi da governanta na cozinha"
"""
from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BASE = AQUI.parent / "base_conhecimento"
INDICE = AQUI / "indice_vetorial.json"

PARADAS = set("""a o as os um uma de da do das dos e em no na nos nas para por com sem que se ao aos
à às é ser foi era são ou mas como mais muito ele ela eles elas seu sua seus suas lhe isso esta este
essa esse aqui ali lá quando onde já não sim tem ter há""".split())


def normalizar(texto: str) -> list[str]:
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in PARADAS and len(w) > 1]


def _ler_ficha(caminho: Path) -> tuple[dict, str]:
    texto = caminho.read_text(encoding="utf-8")
    meta = {}
    if texto.startswith("---"):
        _, cab, corpo = texto.split("---", 2)
        for linha in cab.strip().splitlines():
            k, _, v = linha.partition(":")
            meta[k.strip()] = v.strip()
        texto = corpo
    return meta, texto.strip()


def fatiar() -> list[dict]:
    """Chunking: 1 trecho por ficha; guias divididos por parágrafo/lista."""
    trechos = []
    for arq in sorted(BASE.rglob("*.md")):
        if arq.name == "LEIAME.md":
            continue
        meta, corpo = _ler_ficha(arq)
        if meta.get("tipo") == "guia":
            partes = [p.strip() for p in re.split(r"\n\s*\n", corpo) if p.strip() and not p.startswith("# ")]
            for i, parte in enumerate(partes):
                trechos.append({"id": f"{meta['id']}_{i+1}", "fonte": meta["id"], "tipo": "guia",
                                "titulo": meta.get("titulo", ""), "texto": parte})
        else:
            trechos.append({"id": meta["id"], "fonte": meta["id"], "tipo": meta.get("tipo", ""),
                            "titulo": meta.get("titulo", ""), "texto": corpo})
    return trechos


def indexar() -> dict:
    trechos = fatiar()
    docs = [Counter(normalizar(t["titulo"] + " " + t["texto"])) for t in trechos]
    n = len(docs)
    df = Counter(w for d in docs for w in d)
    idf = {w: math.log((1 + n) / (1 + c)) + 1 for w, c in df.items()}
    for t, d in zip(trechos, docs):
        vet = {w: (1 + math.log(c)) * idf[w] for w, c in d.items()}
        norma = math.sqrt(sum(v * v for v in vet.values())) or 1.0
        t["vetor"] = {w: round(v / norma, 5) for w, v in vet.items()}
    indice = {"versao": 1, "metodo": "tf-idf", "idf": {w: round(v, 5) for w, v in idf.items()}, "trechos": trechos}
    INDICE.write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    return indice


def carregar() -> dict:
    if not INDICE.exists():
        return indexar()
    return json.loads(INDICE.read_text(encoding="utf-8"))


def _vetor_consulta(texto: str, idf: dict) -> dict:
    c = Counter(normalizar(texto))
    vet = {w: (1 + math.log(n)) * idf.get(w, 1.0) for w, n in c.items()}
    norma = math.sqrt(sum(v * v for v in vet.values())) or 1.0
    return {w: v / norma for w, v in vet.items()}


def buscar(consulta: str, k: int = 6, so_fontes: set | None = None, indice: dict | None = None) -> list[dict]:
    """Busca por cosseno. `so_fontes` limita aos ids sorteados no caso (filtro)."""
    indice = indice or carregar()
    q = _vetor_consulta(consulta, indice["idf"])
    resultado = []
    for t in indice["trechos"]:
        if so_fontes is not None and t["fonte"] not in so_fontes and t["tipo"] != "guia":
            continue
        score = sum(q.get(w, 0) * v for w, v in t["vetor"].items())
        resultado.append((score, t))
    resultado.sort(key=lambda x: -x[0])
    return [{"id": t["id"], "fonte": t["fonte"], "titulo": t["titulo"], "texto": t["texto"], "score": round(s, 3)}
            for s, t in resultado[:k]]


def contexto_do_caso(caso: dict, k_guias: int = 4) -> list[dict]:
    """Contexto que vai para a IA: ficha de cada item do caso + os trechos de guia mais úteis."""
    indice = carregar()
    fontes = set(caso["suspeitos"]) | set(caso["armas"]) | set(caso["comodos"])
    por_fonte = {t["fonte"]: t for t in indice["trechos"] if t["tipo"] != "guia"}
    fichas = [{"id": f, "titulo": por_fonte[f]["titulo"], "texto": por_fonte[f]["texto"], "score": 1.0}
              for f in caso["suspeitos"] + caso["armas"] + caso["comodos"] if f in por_fonte]
    guias = buscar("escrever pistas depoimentos mentira álibi tom classificação crime fora de cena",
                   k=k_guias, so_fontes=set(), indice=indice)
    return fichas + guias


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--indexar":
        idx = indexar()
        print(f"Índice criado: {len(idx['trechos'])} trechos, {len(idx['idf'])} palavras -> {INDICE.name}")
    else:
        consulta = " ".join(sys.argv[1:]) or "quem tem a chave do escritório"
        for r in buscar(consulta):
            print(f"{r['score']:.3f}  [{r['id']}] {r['titulo']}: {r['texto'][:90].replace(chr(10), ' ')}…")

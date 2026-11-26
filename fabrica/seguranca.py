"""Defesas da fábrica de casos contra prompt injection e saídas perigosas.

Três camadas (testadas em fabrica/testes_injecao.py e testes/casos_de_teste.py):
  1. filtrar_trechos  - antes do prompt: tira da busca do RAG qualquer trecho com cara de ordem
                        ("ignore as regras", "revele a solução", "chave da API"...)
  2. prompt v3        - o contexto vai entre <contexto> e </contexto> e o prompt diz que é só dado
  3. checar_saida     - depois da IA: conteúdo violento, vazamento de segredo ou do prompt do sistema
                        (somado às checagens do pipeline e ao validador lógico)
Além disso, a IA não decide nada da lógica: culpado, arma, cômodo e fatos vêm do código.
"""
from __future__ import annotations

import re
import unicodedata


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# Ordens escondidas num documento (texto já sem acento e em minúsculas).
PADROES_INJECAO = [
    r"\bignor\w*\b.{0,40}\b(regra|instruc|orientac|anterior|acima|sistema|tudo|fatos?)\b",
    r"\b(desconsider|esquec)\w*\b.{0,40}\b(regra|instruc|anterior|acima)",
    r"\binstruc\w*\s+(anterior|acima|do sistema|original)",
    r"\b(nova|novas)\s+(instruc|regra|ordem)",
    r"\b(prompt|mensagem|instrucoes?)\s+(de|do)\s+sistema\b",
    r"\bsystem\s+prompt\b|\bignore\s+(all|previous|the)\b",
    r"\bvoce\s+(agora\s+)?(e|sera)\s+(um|uma|o|a)\b",
    r"\b(revele|vaze|mostre|escreva|coloque|inclua|diga|conte)\b.{0,50}\b(culpado|solucao|arma do crime|comodo do crime)",
    r"\b(api[ _-]?key|chave da api|gemini_api_key|senha|token)\b",
    r"\b(responda|escreva)\s+(so|somente|apenas)\s+(em\s+)?texto\b|\bsem json\b",
]

# Tom: o crime acontece fora de cena (guia g03), sem sangue nem ferimentos.
PALAVRAS_VIOLENTAS = {"sangue": r"\bsangue\b(?! nos olhos)", "sangrento": r"sangrent", "ensanguentado": r"ensanguent",
                      "esfaquear": r"esfaque", "facada": r"\bfacadas?\b", "degolar": r"degol", "decapitar": r"decapit",
                      "mutilar": r"mutil", "tortura": r"tortur", "vísceras": r"viscera", "tripas": r"\btripas\b",
                      "estripar": r"estripa", "gore": r"\bgore\b"}

# Segredos e o próprio prompt não podem aparecer no texto do jogo.
PADROES_SEGREDO = [r"aiza[0-9a-z_\-]{20,}", r"gemini_api_key", r"roteirista do jogo", r"#\s*sistema",
                   r"regras obrigatorias", r"<contexto>"]


def suspeita_de_injecao(texto: str) -> list[str]:
    t = _norm(texto)
    return [p for p in PADROES_INJECAO if re.search(p, t)]


def filtrar_trechos(trechos: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separa os trechos do RAG em (limpos, bloqueados)."""
    limpos, bloqueados = [], []
    for t in trechos:
        (bloqueados if suspeita_de_injecao(t.get("texto", "")) else limpos).append(t)
    return limpos, bloqueados


def checar_tom(texto: str) -> list[str]:
    t = _norm(texto)
    return [nome for nome, p in PALAVRAS_VIOLENTAS.items() if re.search(p, t)]


def checar_vazamento(texto: str) -> list[str]:
    t = _norm(texto)
    return [p for p in PADROES_SEGREDO if re.search(p, t)]


def checar_saida(textos: dict[str, str]) -> list[str]:
    """Recebe {onde: texto} e devolve a lista de erros de segurança."""
    erros = []
    for onde, texto in textos.items():
        if checar_tom(texto):
            erros.append(f"{onde} tem conteúdo violento ({', '.join(checar_tom(texto))})")
        if checar_vazamento(texto):
            erros.append(f"{onde} vaza segredo ou o prompt do sistema")
    return erros

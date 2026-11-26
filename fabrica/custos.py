"""Custo por 1.000 usos e latência média, a partir do fabrica/registro.csv (execuções reais).

"Uso" = gerar um caso com a IA (sorteio + RAG + Gemini + validação, com as tentativas que precisar).
Jogar uma partida não chama a IA: o jogo só lê casos já aprovados, então custa zero.

Uso:   python fabrica/custos.py
Saída: docs/custos.md
"""
import csv
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from pipeline import PRECO_PAGO, custo  # noqa: E402

linhas = [r for r in csv.DictReader((AQUI / "registro.csv").open(encoding="utf-8")) if r["modelo"] not in ("", "simulado", "fake")]
grupos = defaultdict(list)
for r in linhas:
    grupos[r["prompt"].replace(" (n8n)", "")].append(r)
grupos["todos"] = linhas


def br(x, casas=1):
    """Número no formato brasileiro: 1.234,5"""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def linha(nome, rs):
    tot = [int(r["ms_total"]) / 1000 for r in rs]
    ia = [int(r["ms_ia"]) / 1000 for r in rs]
    tin = st.mean(int(r["tokens_entrada"]) for r in rs)
    tout = st.mean(int(r["tokens_saida"]) for r in rs)
    pago = st.mean(custo(r["modelo"], int(r["tokens_entrada"]), int(r["tokens_saida"])) or 0 for r in rs)
    aprov = sum(r["aprovado"] == "True" for r in rs)
    modelos = " e ".join(sorted({r["modelo"] for r in rs}))
    return (f"| {nome} | {len(rs)} | {aprov}/{len(rs)} | {modelos} | {br(st.mean(tot))} s (mediana {br(st.median(tot))}) | "
            f"{br(st.mean(ia))} s | {br(tin, 0)} + {br(tout, 0)} | US$ 0 | US$ {br(pago * 1000, 2)} |")


saida = ["# Custo por 1.000 usos e latência", "", f"Gerado por `python fabrica/custos.py` em {time.strftime('%d/%m/%Y %H:%M')}, "
         f"com {len(linhas)} execuções reais do `registro.csv`.", "",
         "| Prompt | Casos | Aprovados | Modelo(s) | Latência total por caso | Só a IA | Tokens por caso (entrada + saída) | "
         "Custo real por 1.000 | Custo por 1.000 se fosse pago |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
saida += [linha(k, v) for k, v in sorted(grupos.items()) if k != "todos"] + [linha("todos", grupos["todos"])]
saida += ["", "Preços pagos por milhão de tokens (entrada / saída): " +
          "; ".join(f"{m} US$ {br(a, 2)} / {br(b, 2)}" for m, (a, b) in PRECO_PAGO.items()) + " (ai.google.dev/pricing, 26/11/2026).",
          "Jogar não custa nada: o jogo só lê casos já aprovados, sem chamar a IA."]
(AQUI.parent / "docs" / "custos.md").write_text("\n".join(saida) + "\n", encoding="utf-8")
print("\n".join(saida))

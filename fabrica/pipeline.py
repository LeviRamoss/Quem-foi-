"""Fábrica de casos com IA: sorteio + RAG + Gemini + validador + registro.

Etapas (as mesmas do fluxo do n8n):
  1. preparar   - o código sorteia o caso (gerador_local) e o RAG busca o contexto
  2. ia         - o Gemini reescreve os textos (título, enredo, pistas, respostas)
  3. validar    - aplica os textos e confere tudo; reprovado -> nova tentativa (até 3)
  4. registrar  - salva o caso aprovado e uma linha em fabrica/registro.csv

Uso (no terminal, dentro da pasta do projeto):
    py fabrica/pipeline.py --casos 5 --prompt v2
    py fabrica/pipeline.py --casos 5 --prompt v1
    py fabrica/pipeline.py --simular          (sem chave: a "IA" devolve os textos-base)

Precisa de um arquivo .env na pasta do projeto com:
    GEMINI_API_KEY=sua-chave
    GEMINI_MODELO=gemini-3.6-flash        (opcional)
Só usa a biblioteca padrão do Python.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import gerador_local  # noqa: E402
import rag  # noqa: E402
import validar  # noqa: E402

PROMPTS = AQUI / "prompts"
REGISTRO = AQUI / "registro.csv"
CASOS_IA = RAIZ / "dados" / "casos" / "ia"
MAX_TENTATIVAS = 3
MODELOS_PADRAO = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
# Preço do plano pago (US$ por milhão de tokens: entrada, saída), só para comparar.
# No plano gratuito o custo real é zero. Fonte: página de preços da Gemini API, consultada em 27/10/2026.
PRECO_PAGO = {"gemini-3.1-flash-lite": (0.25, 1.50), "gemini-3.8-flash": (0.75, 3.75)}

P = gerador_local.PERSONAGENS
A = gerador_local.ARMAS
C = gerador_local.COMODOS
PERG = {q["id"]: q["texto"] for q in gerador_local._carregar("perguntas.json")}


# =========================================================================== utilidades
def ler_env() -> dict:
    env = {}
    arq = RAIZ / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, _, v = linha.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def sem_acento(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def radical(nome: str) -> str:
    """Começo da palavra sem acento, para aceitar plural e variações ("castiçais" ~ "Castiçal")."""
    n = sem_acento(nome)
    return n[:6] if len(n) > 6 else n


def cita(nome: str, texto: str) -> bool:
    return radical(nome) in sem_acento(texto)


def primeiro_nome(pid):
    return P[pid]["nome"].split()[0]


def nome_arma(aid):
    return A[aid]["nome"].split()[0]          # "Tesoura de poda" -> "Tesoura"


def nome_comodo(cid):
    return C[cid]["nome"].split()[0]          # "Sala de Estar" -> "Sala"


def fato_em_palavras(f: dict | None) -> str:
    if not f:
        return "nenhum (opinião ou clima)"
    if f["tipo"] == "nao_e":
        nomes = {"suspeito": P, "arma": A, "comodo": C}[f["categoria"]]
        return f"{nomes[f['item']]['nome']} NÃO é a resposta ({f['categoria']})"
    if f["tipo"] == "estava_em":
        return f"{P[f['suspeito']]['nome']} estava {gerador_local.no_na(f['comodo'])} na hora do crime"
    if f["tipo"] == "nao_esteve_em":
        return f"{P[f['suspeito']]['nome']} NÃO esteve {gerador_local.no_na(f['comodo'])} na hora do crime"
    return str(f)


def deve_citar_pista(p: dict) -> list[str]:
    nomes = []
    for f in p["fatos"]:
        if f["tipo"] in ("estava_em", "nao_esteve_em"):
            nomes.append(primeiro_nome(f["suspeito"]))
        elif f["tipo"] == "nao_e" and f["categoria"] == "arma":
            nomes.append(nome_arma(f["item"]))
    return nomes


def deve_citar_resposta(r: dict) -> list[str]:
    f = r.get("fato")
    if f and f["tipo"] in ("estava_em", "nao_esteve_em"):
        return [nome_comodo(f["comodo"])]
    return []


# =========================================================================== 1. preparar
def montar_caso_texto(esq: dict, versao: str) -> str:
    linhas = [f"Vítima: {esq['vitima']['nome']} ({esq['vitima']['descricao']}). Horário do crime: {esq['horario_do_crime']}.",
              f"Título-base: {esq['titulo']}", f"Enredo-base: {esq['enredo']}", "",
              "Suspeitos: " + "; ".join(f"{s} {P[s]['nome']} ({P[s]['papel']})" for s in esq["suspeitos"]),
              "Armas: " + ", ".join(f"{a} {A[a]['nome']}" for a in esq["armas"]),
              "Cômodos: " + ", ".join(f"{c} {C[c]['nome']}" for c in esq["comodos"]), "",
              "PISTAS (reescreva o texto; o fato não pode mudar):"]
    for p in esq["pistas"]:
        fatos = "; ".join(fato_em_palavras(f) for f in p["fatos"]) or "nenhum (clima)"
        extra = f" | deve citar: {', '.join(deve_citar_pista(p)) or '-'}" if versao == "v2" else ""
        linhas.append(f"- {p['id']} | {C[p['comodo']]['nome']} | fato: {fatos}{extra} | texto-base: \"{p['texto']}\"")
    linhas += ["", "RESPOSTAS DO INTERROGATÓRIO (reescreva no jeito de falar de cada um; verdade/mentira e fato não mudam):"]
    for s in esq["suspeitos"]:
        linhas.append(f"* {s} {P[s]['nome']} — jeito de falar: {P[s]['jeito_de_falar']}")
        for q, r in esq["respostas"][s].items():
            vm = "VERDADE" if r["verdade"] else "MENTIRA"
            extra = f" | deve citar: {', '.join(deve_citar_resposta(r)) or '-'}" if versao == "v2" else ""
            linhas.append(f"  - {q} \"{PERG[q]}\" | {vm} | fato: {fato_em_palavras(r.get('fato'))}{extra} | texto-base: \"{r['texto']}\"")
    return "\n".join(linhas)


def preparar(rng: random.Random, versao: str = "v2", evitar: dict | None = None) -> dict:
    t0 = time.perf_counter()
    esq = gerador_local.gerar_caso(rng, evitar=evitar)
    t1 = time.perf_counter()
    contexto = rag.contexto_do_caso(esq)
    t2 = time.perf_counter()
    ctx_txt = "\n\n".join(f"[{c['id']}] {c['texto']}" for c in contexto)
    modelo = (PROMPTS / f"{versao}.md").read_text(encoding="utf-8")
    sistema, _, pedido = modelo.partition("# PEDIDO")
    sistema = sistema.replace("# SISTEMA", "").strip()
    proibidas = ", ".join([C[c]["nome"] for c in esq["comodos"]] + [A[a]["nome"] for a in esq["armas"]])
    prompt = pedido.strip().format(contexto=ctx_txt, caso=montar_caso_texto(esq, versao),
                                   proibidas=proibidas, correcoes="")
    return {"versao": versao, "esqueleto": esq, "contexto_ids": [c["id"] for c in contexto],
            "sistema": sistema, "prompt": prompt, "proibidas": proibidas,
            "ms": {"sorteio": round((t1 - t0) * 1000, 1), "rag": round((t2 - t1) * 1000, 1)}}


# =========================================================================== 2. IA (Gemini)
class ErroIA(Exception):
    pass


def chamar_gemini(sistema: str, prompt: str, chave: str, modelos: list[str]) -> dict:
    corpo = json.dumps({
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8},
    }).encode("utf-8")
    ultimo = None
    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
        req = urllib.request.Request(url, data=corpo, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": chave})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            ultimo = f"{modelo}: HTTP {e.code} {msg}"
            if e.code in (404, 429, 503):      # modelo indisponível ou cota: tenta o próximo
                continue
            raise ErroIA(ultimo)
        except urllib.error.URLError as e:
            raise ErroIA(f"sem conexão com a API: {e}")
        ms = (time.perf_counter() - t0) * 1000
        uso = dados.get("usageMetadata", {})
        try:
            texto = dados["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ErroIA(f"{modelo}: resposta sem texto: {json.dumps(dados)[:300]}")
        return {"modelo": modelo, "texto": texto, "ms": round(ms, 1),
                "tokens_entrada": uso.get("promptTokenCount", 0),
                "tokens_saida": uso.get("candidatesTokenCount", 0) + uso.get("thoughtsTokenCount", 0)}
    raise ErroIA(f"nenhum modelo respondeu. Último erro: {ultimo}")


def simular_ia(prep: dict) -> dict:
    """Sem chave: devolve os textos-base (serve para testar o fluxo e o n8n)."""
    e = prep["esqueleto"]
    saida = {"titulo": e["titulo"].replace(" na Mansão Valverde", ""), "enredo": e["enredo"],
             "pistas": {p["id"]: p["texto"] for p in e["pistas"]},
             "respostas": {s: {q: r["texto"] for q, r in e["respostas"][s].items()} for s in e["suspeitos"]}}
    return {"modelo": "simulado", "texto": json.dumps(saida, ensure_ascii=False), "ms": 0.0,
            "tokens_entrada": 0, "tokens_saida": 0}


# =========================================================================== 3. validar
def aplicar_textos(esq: dict, texto_ia: str) -> tuple[dict | None, list[str]]:
    erros = []
    try:
        ia = json.loads(texto_ia)
    except json.JSONDecodeError as e:
        return None, [f"a IA não devolveu um JSON válido ({e.msg})"]
    caso = json.loads(json.dumps(esq))
    caso["id"] = esq["id"].replace("caso_local", "caso_ia")
    titulo = str(ia.get("titulo", "")).strip()
    caso["titulo"] = (titulo + " na Mansão Valverde") if titulo and "Valverde" not in titulo else (titulo or esq["titulo"])
    caso["enredo"] = str(ia.get("enredo", "")).strip()
    if not caso["enredo"]:
        erros.append("faltou o enredo")
    elif len(caso["enredo"].split()) > 140:
        erros.append(f"enredo com {len(caso['enredo'].split())} palavras (máximo 120)")
    fora = [x for x in P if x not in esq["suspeitos"]]
    armas_fora = [x for x in A if x not in esq["armas"]]
    pistas_ia = ia.get("pistas", {}) or {}
    for p in caso["pistas"]:
        t = str(pistas_ia.get(p["id"], "")).strip()
        if not t:
            erros.append(f"faltou a pista {p['id']}")
            continue
        p["texto"] = t
        nt = sem_acento(t)
        for nome in deve_citar_pista(p):
            if not cita(nome, t):
                erros.append(f"pista {p['id']} não cita {nome}")
        for x in fora:
            if sem_acento(primeiro_nome(x)) in nt.split() or sem_acento(P[x]["nome"]) in nt:
                erros.append(f"pista {p['id']} cita {P[x]['nome']}, que não está no caso")
        for x in armas_fora:
            if sem_acento(nome_arma(x)) in nt:
                erros.append(f"pista {p['id']} cita {A[x]['nome']}, que não está no caso")
        if len(t) > 280:
            erros.append(f"pista {p['id']} longa demais ({len(t)} caracteres)")
    resp_ia = ia.get("respostas", {}) or {}
    for s in caso["suspeitos"]:
        for q, r in caso["respostas"][s].items():
            t = str((resp_ia.get(s) or {}).get(q, "")).strip()
            if not t:
                erros.append(f"faltou a resposta {s}/{q}")
                continue
            r["texto"] = t
            for nome in deve_citar_resposta(r):
                if not cita(nome, t):
                    erros.append(f"resposta {s}/{q} não cita {nome}")
            if len(t) > 260:
                erros.append(f"resposta {s}/{q} longa demais ({len(t)} caracteres)")
    return caso, erros


def validar_caso(esq: dict, texto_ia: str) -> dict:
    t0 = time.perf_counter()
    caso, erros = aplicar_textos(esq, texto_ia)
    if caso is not None:
        erros_logica, _ = validar.validar(caso)
        erros += erros_logica
    return {"aprovado": not erros, "erros": erros, "caso": caso,
            "ms": round((time.perf_counter() - t0) * 1000, 1)}


# =========================================================================== 4. registrar
CAMPOS = ["data", "caso", "prompt", "tentativas", "modelo", "aprovado", "erros_na_1a", "primeiro_erro",
          "tokens_entrada", "tokens_saida", "ms_sorteio", "ms_rag", "ms_ia", "ms_validar", "ms_total",
          "custo_real_usd", "custo_se_fosse_pago_usd"]


def registrar(linha: dict, caso: dict | None) -> None:
    novo = not REGISTRO.exists()
    with REGISTRO.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerow({k: linha.get(k, "") for k in CAMPOS})
    if caso is not None and linha.get("aprovado"):
        CASOS_IA.mkdir(parents=True, exist_ok=True)
        (CASOS_IA / f"{caso['id']}.json").write_text(json.dumps(caso, ensure_ascii=False, indent=2), encoding="utf-8")


def custo(modelo, tin, tout):
    if modelo not in PRECO_PAGO:
        return ""
    pin, pout = PRECO_PAGO[modelo]
    return round(tin / 1e6 * pin + tout / 1e6 * pout, 6)


# =========================================================================== execução completa
def gerar_um(rng, versao, chave, modelos, evitar=None, simular=False) -> dict:
    t_ini = time.perf_counter()
    prep = preparar(rng, versao, evitar)
    tin = tout = ms_ia = ms_val = 0
    erros_1a = None
    res = None
    ia = None
    prompt = prep["prompt"]
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        ia = simular_ia(prep) if simular else chamar_gemini(prep["sistema"], prompt, chave, modelos)
        tin += ia["tokens_entrada"]; tout += ia["tokens_saida"]; ms_ia += ia["ms"]
        res = validar_caso(prep["esqueleto"], ia["texto"])
        ms_val += res["ms"]
        if erros_1a is None:
            erros_1a = len(res["erros"])
        if res["aprovado"]:
            break
        if versao == "v2":   # v2: a próxima tentativa recebe os erros
            lista = "\n".join(f"- {e}" for e in res["erros"][:15])
            prompt = prep["prompt"].replace("## Contexto (base de conhecimento)",
                                            f"## Correções da tentativa anterior (resolva todas)\n{lista}\n\n## Contexto (base de conhecimento)", 1)
    linha = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "caso": res["caso"]["id"] if res["caso"] else prep["esqueleto"]["id"],
        "prompt": versao, "tentativas": tentativa, "modelo": ia["modelo"], "aprovado": res["aprovado"],
        "erros_na_1a": erros_1a, "primeiro_erro": (res["erros"][0] if res["erros"] else ""),
        "tokens_entrada": tin, "tokens_saida": tout, "ms_sorteio": prep["ms"]["sorteio"], "ms_rag": prep["ms"]["rag"],
        "ms_ia": round(ms_ia), "ms_validar": round(ms_val, 1), "ms_total": round((time.perf_counter() - t_ini) * 1000),
        "custo_real_usd": 0, "custo_se_fosse_pago_usd": custo(ia["modelo"], tin, tout),
    }
    registrar(linha, res["caso"])
    return {"linha": linha, "erros": res["erros"], "caso": res["caso"], "solucao": prep["esqueleto"]["solucao"]}


def main():
    ap = argparse.ArgumentParser(description="Gera casos com IA (Gemini) e registra os resultados.")
    ap.add_argument("--casos", type=int, default=5)
    ap.add_argument("--prompt", choices=["v1", "v2"], default="v2")
    ap.add_argument("--semente", type=int, default=None)
    ap.add_argument("--simular", action="store_true", help="não chama a IA (teste do fluxo)")
    a = ap.parse_args()
    env = ler_env()
    chave = env.get("GEMINI_API_KEY", "")
    if not chave and not a.simular:
        print("Falta a chave. Crie o arquivo .env na pasta do projeto com a linha:\nGEMINI_API_KEY=sua-chave")
        sys.exit(1)
    modelos = [env["GEMINI_MODELO"]] + MODELOS_PADRAO if env.get("GEMINI_MODELO") else MODELOS_PADRAO
    rng = random.Random(a.semente)
    evitar = None
    resultados = []
    print(f"Gerando {a.casos} caso(s) com o prompt {a.prompt}{' (simulado)' if a.simular else ''}...\n")
    for i in range(a.casos):
        try:
            r = gerar_um(rng, a.prompt, chave, modelos, evitar, a.simular)
        except ErroIA as e:
            print(f"[{i+1}] ERRO DA IA: {e}")
            continue
        L = r["linha"]
        evitar = {**r["solucao"], "titulo": r["caso"]["titulo"] if r["caso"] else ""}
        resultados.append(L)
        status = "APROVADO" if L["aprovado"] else "REPROVADO"
        print(f"[{i+1}] {status} em {L['tentativas']} tentativa(s) | {L['modelo']} | "
              f"{L['tokens_entrada']}+{L['tokens_saida']} tokens | IA {L['ms_ia']/1000:.1f}s | total {L['ms_total']/1000:.1f}s")
        if r["caso"]:
            print(f"     {r['caso']['titulo']}: {r['caso']['enredo'][:110]}...")
        if r["erros"]:
            print(f"     erros: {r['erros'][:3]}")
    if resultados:
        n = len(resultados)
        ok = sum(1 for x in resultados if x["aprovado"])
        ok1 = sum(1 for x in resultados if x["aprovado"] and x["tentativas"] == 1)
        print(f"\nResumo ({a.prompt}): {ok}/{n} aprovados, {ok1}/{n} na 1ª tentativa | "
              f"média {sum(x['tokens_entrada'] for x in resultados)/n:.0f}+{sum(x['tokens_saida'] for x in resultados)/n:.0f} tokens | "
              f"IA {sum(x['ms_ia'] for x in resultados)/n/1000:.1f}s | total {sum(x['ms_total'] for x in resultados)/n/1000:.1f}s por caso")
        print(f"Registro: {REGISTRO}")


if __name__ == "__main__":
    main()

"""Roda os casos de teste da fábrica de casos e escreve docs/casos_de_teste.md.

Cada caso tem entrada, resultado esperado e resultado OBTIDO (o que o código
devolveu de verdade nesta execução). Também mede o tempo das etapas locais.

Uso: python testes/casos_de_teste.py
"""
import copy
import json
import random
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fabrica"))
import gerador_local  # noqa: E402
import pipeline  # noqa: E402
import rag  # noqa: E402
import validar  # noqa: E402

EXEMPLO = json.loads((RAIZ / "dados/casos/caso_exemplo.json").read_text(encoding="utf-8"))
casos = []


def registrar(n, nome, entrada, esperado, obtido, ok):
    casos.append((n, nome, entrada, esperado, obtido, "passou" if ok else "FALHOU"))


def resumo(erros, trecho=""):
    if not erros:
        return "aprovado"
    achado = next((x for x in erros if trecho in x), erros[0])
    extra = f" (+{len(erros) - 1} outros)" if len(erros) > 1 else ""
    return "reprovado: " + achado + extra


# --- 1 a 4: validador -------------------------------------------------------------
e, _ = validar.validar(EXEMPLO)
registrar(1, "Caso de exemplo íntegro", "dados/casos/caso_exemplo.json", "aprovado", resumo(e), not e)

c = copy.deepcopy(EXEMPLO)
c["pistas"][3]["fatos"] = []
e, n = validar.validar(c)
registrar(2, "Falta uma pista (álibi da Rita)", "caso de exemplo sem os fatos da pista pi04",
          "reprovado: mais de 1 solução", resumo(e, "soluções possíveis"), any("soluções possíveis" in x for x in e))

c = copy.deepcopy(EXEMPLO)
c["respostas"]["p01"]["q01"]["verdade"] = False
e, _ = validar.validar(c)
registrar(3, "Inocente mentindo", "Helena (inocente) com resposta marcada como mentira",
          "reprovado: só o culpado mente", resumo(e, "só o culpado"), any("só o culpado" in x for x in e))

c = copy.deepcopy(EXEMPLO)
c["enredo"] = "Às 22h, Rita encontrou Augusto sem vida na poltrona da biblioteca, com um copo de licor ao lado."
e, _ = validar.validar(c)
registrar(4, "Abertura entrega o local (bug achado no teste de QA)", "abertura antiga: \"...na poltrona da biblioteca...\"",
          "reprovado: abertura cita o cômodo", resumo(e, "abertura"), any("abertura" in x for x in e))

# --- 5 a 8: resposta da IA (pipeline) ---------------------------------------------
rng = random.Random(11)
prep = pipeline.preparar(rng, "v2")
esq = prep["esqueleto"]
boa = json.loads(pipeline.simular_ia(prep)["texto"])

r = pipeline.validar_caso(esq, json.dumps(boa, ensure_ascii=False))
registrar(5, "IA devolve todos os textos corretos", "JSON completo com título, abertura, 12 pistas e 50 respostas",
          "aprovado", resumo(r["erros"]), r["aprovado"])

r = pipeline.validar_caso(esq, "Claro! Aqui está o caso: {titulo: ...")
registrar(6, "IA devolve texto que não é JSON", "\"Claro! Aqui está o caso: {titulo: ...\"",
          "reprovado: JSON inválido", resumo(r["erros"]), not r["aprovado"] and "JSON" in r["erros"][0])

ruim = copy.deepcopy(boa)
pista_alibi = next(p for p in esq["pistas"] if any(f["tipo"] == "estava_em" for f in p["fatos"]))
ruim["pistas"][pista_alibi["id"]] = "Alguém ficou aqui a noite toda e nada saiu do lugar."
r = pipeline.validar_caso(esq, json.dumps(ruim, ensure_ascii=False))
registrar(7, "IA tira o nome do suspeito do álibi", f"pista {pista_alibi['id']} reescrita sem o nome",
          "reprovado: pista não cita o suspeito", resumo(r["erros"], "não cita"), any("não cita" in x for x in r["erros"]))

ruim = copy.deepcopy(boa)
fora = next(x for x in gerador_local.PERSONAGENS if x not in esq["suspeitos"])
nome_fora = gerador_local.PERSONAGENS[fora]["nome"]
ruim["pistas"]["pi02"] = f"Um bilhete assinado por {nome_fora} esquecido na mesa."
r = pipeline.validar_caso(esq, json.dumps(ruim, ensure_ascii=False))
registrar(8, "IA cita personagem fora do caso", f"pista pi02 cita {nome_fora}, que não é suspeito neste caso",
          "reprovado: personagem fora do caso", resumo(r["erros"], "não está no caso"), any("não está no caso" in x for x in r["erros"]))

ruim = copy.deepcopy(boa)
arma = gerador_local.ARMAS[esq["solucao"]["arma"]]["nome"]
ruim["enredo"] = f"Ninguém imaginava que {arma.lower()} seria usada naquela noite."
r = pipeline.validar_caso(esq, json.dumps(ruim, ensure_ascii=False))
registrar(9, "IA entrega a arma na abertura", f"abertura citando \"{arma.lower()}\"",
          "reprovado: abertura cita a arma", resumo(r["erros"], "abertura"), any("abertura" in x for x in r["erros"]))

# --- 10: gerador em sequência ------------------------------------------------------
rng = random.Random(42)
ant, ok, repet = None, 0, 0
for _ in range(300):
    cc = gerador_local.gerar_caso(rng, evitar=ant)
    ok += not validar.validar(cc)[0]
    s = cc["solucao"]
    if ant and any(s[k] == ant[k] for k in ("culpado", "arma", "comodo")):
        repet += 1
    ant = {**s, "titulo": cc["titulo"]}
registrar(10, "300 casos seguidos do gerador local", "300 sorteios, cada um evitando o anterior",
          "300 aprovados, nenhuma repetição seguida", f"{ok} aprovados, {repet} repetições", ok == 300 and repet == 0)

# --- medição de tempo das etapas locais ------------------------------------------
rng = random.Random(1)
t_sorteio, t_rag, t_valid, t_prompt = [], [], [], []
for _ in range(200):
    t0 = time.perf_counter(); cc = gerador_local.gerar_caso(rng); t1 = time.perf_counter()
    rag.contexto_do_caso(cc); t2 = time.perf_counter()
    validar.validar(cc); t3 = time.perf_counter()
    t_sorteio.append((t1 - t0) * 1000); t_rag.append((t2 - t1) * 1000); t_valid.append((t3 - t2) * 1000)
p = pipeline.preparar(random.Random(3), "v2")
p1 = pipeline.preparar(random.Random(3), "v1")
tok_v2 = round(len(p["prompt"] + p["sistema"]) / 4)
tok_v1 = round(len(p1["prompt"] + p1["sistema"]) / 4)


def ms(xs):
    return f"{statistics.mean(xs):.1f} ms (máx. {max(xs):.1f})"


linhas = ["# Casos de teste da fábrica de casos", "",
          f"Gerado por `python testes/casos_de_teste.py` em {time.strftime('%d/%m/%Y %H:%M')}. O resultado obtido é o que o código devolveu nesta execução.", "",
          "| # | Caso | Entrada | Esperado | Obtido | Status |", "| --- | --- | --- | --- | --- | --- |"]
for n, nome, ent, esp, obt, st in casos:
    linhas.append(f"| {n} | {nome} | {ent} | {esp} | {obt} | {st} |")
linhas += ["", "## Tempo das etapas locais (média de 200 casos)", "",
           "| Etapa | Tempo |", "| --- | --- |",
           f"| Sorteio do caso (gerador local) | {ms(t_sorteio)} |",
           f"| Busca no RAG (contexto do caso) | {ms(t_rag)} |",
           f"| Validação lógica | {ms(t_valid)} |",
           "", "## Tamanho do prompt (estimado: 4 caracteres por token)", "",
           "| Prompt | Tokens de entrada (aprox.) |", "| --- | --- |",
           f"| v1 | {tok_v1} |", f"| v2 | {tok_v2} |",
           "", "Os tempos e tokens da chamada ao Gemini ficam em `fabrica/registro.csv`, gerado por `py fabrica/pipeline.py`."]
(RAIZ / "docs" / "casos_de_teste.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("\n".join(linhas))
falhas = [c for c in casos if c[5] != "passou"]
sys.exit(1 if falhas else 0)

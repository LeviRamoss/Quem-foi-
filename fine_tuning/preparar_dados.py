"""Prepara os dados do experimento de fine-tuning.

Tarefa: dado um par (pista, depoimento), dizer se o depoimento CONTRADIZ a pista,
CONFIRMA a pista ou é NEUTRO em relação a ela. É o que o validador precisa para
perceber quando um depoimento escrito pela IA desmente uma pista sem querer.

Os rótulos vêm da lógica dos casos (os "fatos"), não de anotação manual:
- contradiz: a pista põe o suspeito num cômodo e ele diz que estava em outro
- confirma:  a pista e o depoimento põem o mesmo suspeito no mesmo cômodo
- neutro:    pista e depoimento sobre coisas diferentes (inclui casos difíceis,
             como o culpado dizendo que estava no mesmo cômodo de um inocente)

Treino e teste vêm de casos diferentes, para o modelo não decorar um caso.

Uso:  python fine_tuning/preparar_dados.py
Saída: fine_tuning/dados/treino.csv e teste.csv
"""
import csv
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "fabrica"))
import gerador_local as g  # noqa: E402

N_CASOS_TREINO, N_CASOS_TESTE = 320, 80
POR_CLASSE_TREINO, POR_CLASSE_TESTE = 960, 240


def texto_pista(p):
    return f"[{g.COMODOS[p['comodo']]['nome']}] {p['texto']}"


def texto_resposta(caso, s, q):
    return f"{g.PERSONAGENS[s]['nome']}: {caso['respostas'][s][q]['texto']}"


def pares_do_caso(caso):
    contradiz, confirma, neutro, dificil = [], [], [], []
    pistas_em = [(p, f) for p in caso["pistas"] for f in p["fatos"] if f["tipo"] == "estava_em"]
    for s in caso["suspeitos"]:
        for q, r in caso["respostas"][s].items():
            fr = r.get("fato")
            for p, fp in pistas_em:
                par = (texto_pista(p), texto_resposta(caso, s, q))
                if fr and fr["tipo"] == "estava_em" and fr["suspeito"] == fp["suspeito"]:
                    (confirma if fr["comodo"] == fp["comodo"] else contradiz).append(par)
                elif fr and fr["tipo"] == "estava_em" and fr["comodo"] == fp["comodo"]:
                    dificil.append(par)   # mesmo cômodo, pessoas diferentes: não é contradição
                else:
                    neutro.append(par)
    return contradiz, confirma, neutro, dificil


def montar(sementes, por_classe, rng):
    cl = {"contradiz": [], "confirma": [], "neutro": [], "dificil": []}
    for sem in sementes:
        caso = g.gerar_caso(random.Random(sem))
        a, b, c, d = pares_do_caso(caso)
        cl["contradiz"] += a
        cl["confirma"] += b
        cl["neutro"] += c
        cl["dificil"] += d
    for pares in cl.values():
        rng.shuffle(pares)
    metade = min(por_classe // 2, len(cl["dificil"]))
    neutros = cl["dificil"][:metade] + cl["neutro"][:por_classe - metade]
    linhas = [(p, d, "contradiz") for p, d in cl["contradiz"][:por_classe]]
    linhas += [(p, d, "confirma") for p, d in cl["confirma"][:por_classe]]
    linhas += [(p, d, "neutro") for p, d in neutros]
    rng.shuffle(linhas)
    return linhas, {k: len(v) for k, v in cl.items()}


def salvar(caminho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pista", "depoimento", "rotulo"])
        w.writerows(linhas)


if __name__ == "__main__":
    rng = random.Random(2026)
    treino, disp_t = montar(range(1, N_CASOS_TREINO + 1), POR_CLASSE_TREINO, rng)
    teste, disp_e = montar(range(10_001, 10_001 + N_CASOS_TESTE), POR_CLASSE_TESTE, rng)
    salvar(AQUI / "dados" / "treino.csv", treino)
    salvar(AQUI / "dados" / "teste.csv", teste)
    print(f"treino: {len(treino)} pares de {N_CASOS_TREINO} casos (disponíveis: {disp_t})")
    print(f"teste:  {len(teste)} pares de {N_CASOS_TESTE} casos diferentes (disponíveis: {disp_e})")

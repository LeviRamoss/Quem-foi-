"""Validador de casos do Quem Foi?.

Uso:
    python fabrica/validar.py dados/casos/caso_exemplo.json

Confere se o caso segue as regras do jogo e se as pistas levam a exatamente uma solução.
Não precisa de bibliotecas externas: com 5 suspeitos, 5 armas e 6 cômodos são só 150 combinações.
"""
import itertools
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"

N_SUSPEITOS, N_ARMAS, N_COMODOS = 5, 5, 6
PISTAS_POR_COMODO = 2


def carregar(nome):
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


def fato_vale(fato, culpado, arma, comodo):
    """Diz se um fato é verdadeiro numa solução (culpado, arma, cômodo)."""
    tipo = fato["tipo"]
    if tipo == "nao_e":
        valor = {"suspeito": culpado, "arma": arma, "comodo": comodo}[fato["categoria"]]
        return valor != fato["item"]
    if tipo == "estava_em":
        # quem estava em outro cômodo na hora do crime não pode ser o culpado
        return culpado != fato["suspeito"] or comodo == fato["comodo"]
    if tipo == "nao_esteve_em":
        return culpado != fato["suspeito"] or comodo != fato["comodo"]
    raise ValueError(f"tipo de fato desconhecido: {tipo}")


def contradiz(a, b):
    """Dois fatos sobre o mesmo suspeito que não podem ser verdade juntos."""
    tipos = {a["tipo"], b["tipo"]}
    if a.get("suspeito") != b.get("suspeito") or a.get("suspeito") is None:
        return False
    if tipos == {"estava_em"}:
        return a["comodo"] != b["comodo"]
    if tipos == {"estava_em", "nao_esteve_em"}:
        return a["comodo"] == b["comodo"]
    return False


def validar(caso):
    erros = []
    ids_p = {p["id"] for p in carregar("personagens.json")}
    ids_a = {a["id"] for a in carregar("armas.json")}
    ids_c = {c["id"] for c in carregar("comodos.json")}
    ids_q = {q["id"] for q in carregar("perguntas.json")}

    sus, arm, com = caso["suspeitos"], caso["armas"], caso["comodos"]
    sol = caso["solucao"]

    # 1. Estrutura
    if len(set(sus)) != N_SUSPEITOS or not set(sus) <= ids_p:
        erros.append(f"suspeitos precisam ser {N_SUSPEITOS} ids diferentes da base")
    if len(set(arm)) != N_ARMAS or not set(arm) <= ids_a:
        erros.append(f"armas precisam ser {N_ARMAS} ids diferentes da base")
    if set(com) != ids_c:
        erros.append("os 6 cômodos da mansão precisam estar no caso")
    if sol["culpado"] not in sus or sol["arma"] not in arm or sol["comodo"] not in com:
        erros.append("a solução usa um item fora das listas do caso")

    # 2. Pistas: 2 por cômodo, só com itens do caso
    for c in com:
        n = sum(1 for p in caso["pistas"] if p["comodo"] == c)
        if n != PISTAS_POR_COMODO:
            erros.append(f"cômodo {c} tem {n} pistas (precisa de {PISTAS_POR_COMODO})")
    itens = set(sus) | set(arm) | set(com)
    fatos_pistas = []
    for p in caso["pistas"]:
        for f in p["fatos"]:
            usados = {f.get("item"), f.get("suspeito"), f.get("comodo")} - {None}
            if not usados <= itens:
                erros.append(f"pista {p['id']} cita item fora do caso: {usados - itens}")
            if not fato_vale(f, sol["culpado"], sol["arma"], sol["comodo"]):
                erros.append(f"pista {p['id']} é falsa na solução: {f}")
            fatos_pistas.append((p["id"], f))

    # 3. Respostas: todos os suspeitos respondem às 10 perguntas
    for s in sus:
        r = caso["respostas"].get(s, {})
        if set(r) != ids_q:
            erros.append(f"suspeito {s} não respondeu a todas as perguntas: faltam {sorted(ids_q - set(r))}")
        for q, resp in r.items():
            f = resp.get("fato")
            if resp["verdade"]:
                if f and not fato_vale(f, sol["culpado"], sol["arma"], sol["comodo"]):
                    erros.append(f"{s}/{q} diz a verdade, mas o fato é falso na solução")
                continue
            # mentiras: só o culpado mente, e toda mentira tem de ser descoberta por uma pista
            if s != sol["culpado"]:
                erros.append(f"{s}/{q}: só o culpado pode mentir")
            if not f:
                erros.append(f"{s}/{q}: mentira sem fato não pode ser conferida")
                continue
            if fato_vale(f, sol["culpado"], sol["arma"], sol["comodo"]):
                erros.append(f"{s}/{q}: marcada como mentira, mas é verdade na solução")
            if not any(contradiz(f, fp) for _, fp in fatos_pistas):
                erros.append(f"{s}/{q}: nenhuma pista contradiz essa mentira")
    if not any(not resp["verdade"] for resp in caso["respostas"].get(sol["culpado"], {}).values()):
        erros.append("o culpado precisa mentir pelo menos uma vez")

    # 4. Lógica: só as pistas dos 6 cômodos já levam a uma única solução
    restantes = [
        combo for combo in itertools.product(sus, arm, com)
        if all(fato_vale(f, *combo) for _, f in fatos_pistas)
    ]
    if len(restantes) != 1:
        erros.append(f"as pistas deixam {len(restantes)} soluções possíveis (precisa ser 1)")
    elif restantes[0] != (sol["culpado"], sol["arma"], sol["comodo"]):
        erros.append(f"as pistas apontam para {restantes[0]}, não para a solução do caso")

    return erros, len(restantes)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    caso = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    erros, n = validar(caso)
    if erros:
        print(f"REPROVADO: {caso['id']}")
        for e in erros:
            print(" -", e)
        sys.exit(1)
    print(f"APROVADO: {caso['id']} ({len(caso['pistas'])} pistas, 1 solução entre 150 combinações)")


if __name__ == "__main__":
    main()

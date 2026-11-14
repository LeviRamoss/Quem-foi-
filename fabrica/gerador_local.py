"""Gerador de casos que roda dentro do jogo, sem internet e sem IA.

A cada chamada ele sorteia 5 suspeitos, 5 armas e a solução (culpado, arma e
cômodo), monta as 12 pistas e as 50 respostas do interrogatório a partir de
modelos de texto e confere tudo com o validador. É também a "reserva" da
arquitetura: quando a fábrica com IA estiver pronta, os casos dela entram no
lugar destes, e este gerador continua garantindo que o jogo nunca fica sem caso.

Uso no terminal (mostra um caso sorteado):
    python fabrica/gerador_local.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import validar  # noqa: E402

DADOS = AQUI.parent / "dados"


def _carregar(nome):
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


PERSONAGENS = {p["id"]: p for p in _carregar("personagens.json")}
ARMAS = {a["id"]: a for a in _carregar("armas.json")}
COMODOS = {c["id"]: c for c in _carregar("comodos.json")}
PERGUNTAS = [q["id"] for q in _carregar("perguntas.json")]

FEMININO = {"p01", "p03", "p06", "p08"}


def curto(pid):
    n = PERSONAGENS[pid]["nome"].split()[0]
    return "o doutor Otávio" if pid == "p04" else n


def no_na(cid):
    return ("no " if cid in ("l05", "l03") else "na ") + COMODOS[cid]["nome"]


def do_da(cid):
    return ("do " if cid in ("l05", "l03") else "da ") + COMODOS[cid]["nome"]


# ---------------------------------------------------------------- modelos de texto
ATIVIDADE = {   # o que alguém faz em cada cômodo
    "l01": "lendo perto da lareira",
    "l05": "revendo papéis da empresa",
    "l06": "escolhendo vinhos para o brinde",
    "l02": "ajudando com a sobremesa",
    "l04": "conversando com os convidados perto do piano",
    "l03": "tomando ar no banco perto da estufa",
}
PROVA = {       # prova de que a pessoa ficou ali
    "l01": "o livro aberto na poltrona ainda marca a página em que parou",
    "l05": "as anotações na mesa têm a letra e o horário",
    "l06": "as garrafas separadas estão marcadas com as digitais",
    "l02": "a louça que usou ainda está na pia",
    "l04": "os convidados que estavam perto do piano confirmam",
    "l03": "as pegadas no caminho de pedras vão e voltam só uma vez",
}
COMODO_LIMPO = {   # nada aconteceu neste cômodo
    "l01": ["As estantes estão em ordem e a poeira da mesa está intacta.",
            "A lareira apagou sozinha e nada saiu do lugar."],
    "l05": ["A porta ficou trancada a noite toda; a chave estava no molho de Rita.",
            "Os papéis estão empilhados como de costume. Ninguém mexeu em nada."],
    "l06": ["A poeira da escada está intacta: ninguém desceu aqui durante a noite.",
            "As prateleiras estão em ordem, e a porta pesada não foi aberta."],
    "l02": ["O chão foi encerado às 21h e não tem nenhuma marca.",
            "Tudo limpo e no lugar, como se a cozinha nem tivesse sido usada."],
    "l04": ["As almofadas estão arrumadas e o tapete não tem nenhuma marca.",
            "As cadeiras estão alinhadas do jeito que Rita deixou depois do jantar."],
    "l03": ["A grama molhada não tem pegadas além das da manhã.",
            "O portão do jardim continua trancado com cadeado."],
}
RASTRO = {         # o culpado esteve no cômodo do crime
    "p01": "Um lenço com perfume de jasmim, o mesmo de Helena, caído no chão.",
    "p02": "Uma ponta de charuto igual aos de Marcos, ainda morna, esquecida num pires.",
    "p03": "Uma das chaves do molho de Rita, esquecida perto da porta.",
    "p04": "A maleta de remédios do doutor Otávio, esquecida aberta num canto.",
    "p05": "Marcas de dedos sujos de pó de garrafa, iguais às mãos de Bruno, perto da porta.",
    "p06": "Uma folha arrancada do caderno vermelho de Clara, com horários anotados.",
    "p07": "Pegadas de bota com lama, do tamanho das botas de Jonas.",
    "p08": "Uma luva de couro de Lívia, perdida no chão.",
}
VESTIGIO_ARMA = {  # clima no cômodo do crime, sem dizer qual é a arma
    "a01": "Um copo com um resíduo de cheiro amargo.",
    "a02": "Um pano úmido escondido, como se alguém tivesse limpado algo às pressas.",
    "a03": "Fibras ásperas presas na quina de um móvel.",
    "a04": "Um leve cheiro de pólvora ainda no ar.",
    "a05": "Pingos de cera fresca no tapete.",
    "a06": "Folhas e galhos recém-cortados, com um corte limpo e rápido.",
}
ARTIGO_ARMA = {"a01": "o frasco de veneno", "a02": "a faca", "a03": "a corda",
               "a04": "o revólver", "a05": "o castiçal", "a06": "a tesoura de poda"}
CASA_DA_ARMA = {"a01": "l03", "a02": "l02", "a03": "l03", "a04": "l05", "a05": "l04", "a06": "l03"}
CLIMA = [
    "Uma janela entreaberta deixa entrar um vento frio.",
    "O relógio de parede parou às 21h47.",
    "Uma vela queimou até o fim no castiçal da parede.",
    "Um quadro torto, como se alguém tivesse esbarrado nele.",
]
RELACAO = {
    "p01": "Fui casada com ele por 25 anos. Nem sempre foi fácil.",
    "p02": "Sócio. Trinta anos de negócios, e ele queria me tirar da empresa.",
    "p03": "Trabalho nesta casa há 20 anos. Ele me prometeu muita coisa.",
    "p04": "Sou o médico da família há 15 anos. Cuidei muito bem dele.",
    "p05": "Ele era meu tio. E, sim, eu sou o herdeiro.",
    "p06": "Eu escrevia a biografia dele. Ele adorava contar vantagem.",
    "p07": "Cuido do jardim há oito anos. Ele me demitiu semana passada.",
    "p08": "Sou a advogada da família. Cuido do testamento.",
}
MOTIVO_3P = {
    "p01": "a Helena devia muito dinheiro em jogo",
    "p02": "o Marcos ia perder a empresa",
    "p03": "a Rita ficou fora do testamento",
    "p04": "o doutor Otávio tinha medo de um segredo vir à tona",
    "p05": "o Bruno precisa da herança para pagar as dívidas",
    "p06": "a Clara queria um escândalo para o livro",
    "p07": "o Jonas foi demitido sem explicação",
    "p08": "a Lívia mexia em dinheiro que não era dela",
}
DEFESA = {
    "p01": "Porque sou a viúva. As pessoas sempre olham primeiro para a viúva.",
    "p02": "Por causa da briga de ontem. Mas briga de sócio não é crime.",
    "p03": "Porque eu tenho as chaves. Mas quem tem as chaves também cuida da casa.",
    "p04": "Porque sou médico e entendo de remédios. Só isso, só isso.",
    "p05": "Por causa das minhas dívidas. Todo mundo sabe delas.",
    "p06": "Porque eu faço perguntas demais. É o meu trabalho.",
    "p07": "Porque fui demitido. Mas eu nunca faria mal a ninguém.",
    "p08": "Porque eu cuido do dinheiro da família. Isso não me faz culpada.",
}
BARULHO = ["Uma porta batendo, perto das 21h40.", "Passos apressados no corredor.",
           "Nada. Só o vento nas janelas.", "Um grito abafado. Ou talvez fosse o vento.",
           "O relógio da sala bateu, e depois um silêncio estranho."]
OBJETO = ["Um quadro torto no corredor.", "Não reparei em nada.",
          "As velas do corredor estavam apagadas.", "Uma xícara esquecida na escada."]

OCASIOES = ["o jantar de aniversário de Augusto Valverde", "a leitura do testamento da família Valverde",
            "a reunião de sócios da construtora Valverde & Teles", "o baile de inverno na Mansão Valverde"]
ABERTURAS = [
    "Durante {ocasiao}, uma tempestade derrubou a energia às 21h30. Quando as luzes voltaram, Augusto não estava mais entre os convidados. Pouco depois das 22h, foi encontrado sem vida.",
    "Era {ocasiao}. Entre um brinde e outro, os convidados se espalharam pela casa. Às 22h, um grito ecoou pelos corredores: Augusto Valverde estava morto.",
    "{Ocasiao} terminou em silêncio. Augusto se despediu de todos às 21h30 e ninguém mais o viu com vida. Às 22h, a governanta deu o alarme.",
]
FECHOS = [
    "As portas estavam trancadas por dentro e a estrada está alagada. O culpado ainda está aqui.",
    "Ninguém entrou nem saiu da mansão. Um dos convidados está mentindo.",
    "Cada um conta uma história diferente. Só uma delas é mentira.",
]
TITULOS = ["O Último Brinde", "Noite Sem Luar", "O Relógio Parado", "A Chave Perdida",
           "Sombras no Corredor", "O Silêncio das Velas", "A Herança Maldita", "Chuva de Inverno"]


def _cap(s):
    return s[0].upper() + s[1:]


# ---------------------------------------------------------------- montagem do caso
def gerar_caso(rng: random.Random | None = None, evitar: dict | None = None, n: int | None = None) -> dict:
    """Monta um caso novo. `evitar` = caso anterior (solução e título): culpado, arma, cômodo e título mudam."""
    rng = rng or random.Random()
    for _ in range(50):
        caso = _montar(rng, evitar, n)
        erros, _ = validar.validar(caso)
        if not erros:
            return caso
    raise RuntimeError(f"gerador local não conseguiu um caso válido: {erros}")


def _montar(rng, evitar, n):
    evitar = evitar or {}
    todos_c = list(COMODOS)
    culpado = rng.choice([p for p in PERSONAGENS if p != evitar.get("culpado")])
    arma = rng.choice([a for a in ARMAS if a != evitar.get("arma")])
    local = rng.choice([c for c in todos_c if c != evitar.get("comodo")])
    suspeitos = [culpado] + rng.sample([p for p in PERSONAGENS if p != culpado], 4)
    rng.shuffle(suspeitos)
    armas = [arma] + rng.sample([a for a in ARMAS if a != arma], 4)
    rng.shuffle(armas)
    inocentes = [s for s in suspeitos if s != culpado]
    outros_comodos = [c for c in todos_c if c != local]
    rng.shuffle(outros_comodos)
    onde = dict(zip(inocentes, outros_comodos))            # álibi de cada inocente
    comodo_livre = [c for c in outros_comodos if c not in onde.values()][0]
    mentira = rng.choice(outros_comodos)                    # onde o culpado diz que estava

    def ne(cat, item):
        return {"tipo": "nao_e", "categoria": cat, "item": item}

    def em(s, c):
        return {"tipo": "estava_em", "suspeito": s, "comodo": c}

    pistas = {c: [] for c in todos_c}
    # cômodo do crime: rastro do culpado + clima que lembra a arma
    pistas[local].append((RASTRO[culpado], [em(culpado, local)]))
    pistas[local].append((VESTIGIO_ARMA[arma], []))
    # cômodos com álibi: a pessoa ficou ali e nada aconteceu
    for s, c in onde.items():
        nome = PERSONAGENS[s]["nome"].split()[0]
        texto = f"{nome} ficou aqui {ATIVIDADE[c]} das 21h às 22h15: {PROVA[c]}. Nada saiu do lugar."
        pistas[c].append((texto, [ne("comodo", c), em(s, c)]))
    pistas[comodo_livre].append((rng.choice(COMODO_LIMPO[comodo_livre]), [ne("comodo", comodo_livre)]))
    # armas erradas: no cômodo de casa, se ainda houver vaga; senão, em outro cômodo vago
    for a in rng.sample([x for x in armas if x != arma], 4):
        casa = CASA_DA_ARMA[a]
        vagas = [c for c in outros_comodos if len(pistas[c]) < 2]
        if casa in vagas:
            texto = ARMAS[a]["pista_que_descarta"]
            pistas[casa].append((texto, [ne("arma", a)]))
        else:
            c = rng.choice(vagas)
            pistas[c].append((f"Alguém guardou aqui {ARTIGO_ARMA[a]}. Não há nenhum sinal de uso.", [ne("arma", a)]))
    for c in todos_c:
        while len(pistas[c]) < 2:
            pistas[c].append((rng.choice(CLIMA), []))

    lista_pistas = []
    k = 1
    for c in todos_c:
        for texto, fatos in pistas[c]:
            lista_pistas.append({"id": f"pi{k:02d}", "comodo": c, "texto": texto, "fatos": fatos})
            k += 1

    # interrogatório
    testemunha = rng.choice(inocentes)   # quem viu o culpado indo para o cômodo do crime
    respostas = {}
    for s in suspeitos:
        outros = [x for x in suspeitos if x != s]
        alvo_motivo = rng.choice(outros)
        alvo_desconfia = rng.choice(outros)
        r = {}
        if s == culpado:
            ativ = ATIVIDADE[mentira]
            r["q01"] = {"texto": f"{_cap(no_na(mentira))}, {ativ}. Fiquei lá um bom tempo.", "verdade": False, "fato": em(s, mentira)}
            quem = [x for x, c in onde.items() if c == mentira]
            if quem:
                txt6 = f"{_cap(curto(quem[0]))} me viu {no_na(mentira)}. Pode perguntar."
            else:
                txt6 = f"Eu estava sozinho{'a' if s in FEMININO else ''} {no_na(mentira)}, mas juro que é verdade."
            r["q06"] = {"texto": txt6, "verdade": False, "fato": em(s, mentira)}
            r["q07"] = {"texto": f"Fui direto para {'o' if mentira in ('l05', 'l03') else 'a'} {COMODOS[mentira]['nome']}. Precisava de um tempo sozinho{'a' if s in FEMININO else ''}.",
                        "verdade": False, "fato": em(s, mentira)}
            r["q02"] = {"texto": "Não vi ninguém. Ninguém mesmo.", "verdade": True, "fato": None}
        else:
            c = onde[s]
            r["q01"] = {"texto": f"{_cap(no_na(c))}, {ATIVIDADE[c]}.", "verdade": True, "fato": em(s, c)}
            r["q06"] = {"texto": f"Pode conferir: {PROVA[c]}.", "verdade": True, "fato": em(s, c)}
            r["q07"] = {"texto": f"Fui {'para o' if c in ('l05', 'l03') else 'para a'} {COMODOS[c]['nome']} e fiquei lá até as 22h15.", "verdade": True, "fato": em(s, c)}
            if s == testemunha:
                r["q02"] = {"texto": f"Vi {curto(culpado)} indo para os lados {do_da(local)}, lá pelas 21h30.", "verdade": True, "fato": em(culpado, local)}
            else:
                r["q02"] = {"texto": f"Não vi ninguém. Fiquei {no_na(c)} o tempo todo.", "verdade": True, "fato": None}
        r["q03"] = {"texto": RELACAO[s], "verdade": True, "fato": None}
        r["q04"] = {"texto": f"Se quer saber, {MOTIVO_3P[alvo_motivo]}.", "verdade": True, "fato": None}
        r["q05"] = {"texto": rng.choice(BARULHO), "verdade": True, "fato": None}
        r["q08"] = {"texto": rng.choice(OBJETO), "verdade": True, "fato": None}
        r["q09"] = {"texto": f"De {curto(alvo_desconfia)}. Tem alguma coisa estranha ali.", "verdade": True, "fato": None}
        r["q10"] = {"texto": DEFESA[s], "verdade": True, "fato": None}
        respostas[s] = {q: r[q] for q in PERGUNTAS}

    ocasiao = rng.choice(OCASIOES)
    abertura = rng.choice(ABERTURAS).format(ocasiao=ocasiao, Ocasiao=_cap(ocasiao))
    enredo = abertura + " " + rng.choice(FECHOS)
    seed = rng.randint(1000, 9999)
    return {
        "formato": 2,
        "id": f"caso_local_{n if n is not None else seed}",
        "titulo": rng.choice([t for t in TITULOS if t not in evitar.get("titulo", "")]) + " na Mansão Valverde",
        "vitima": {"nome": "Augusto Valverde", "descricao": "Dono da mansão e da construtora Valverde & Teles, 60 anos."},
        "horario_do_crime": "entre 21h30 e 22h",
        "enredo": enredo,
        "solucao": {"culpado": culpado, "arma": arma, "comodo": local},
        "suspeitos": suspeitos,
        "armas": armas,
        "comodos": todos_c,
        "pistas": lista_pistas,
        "respostas": respostas,
    }


if __name__ == "__main__":
    caso = gerar_caso()
    s = caso["solucao"]
    print(caso["titulo"])
    print(caso["enredo"], "\n")
    for p in caso["pistas"]:
        print(f"[{COMODOS[p['comodo']]['nome']}] {p['texto']}")
    print("\nSolução:", PERSONAGENS[s["culpado"]]["nome"], "·", ARMAS[s["arma"]]["nome"], "·", COMODOS[s["comodo"]]["nome"])

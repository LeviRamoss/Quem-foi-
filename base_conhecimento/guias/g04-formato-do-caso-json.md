---
id: g04
tipo: guia
titulo: Formato do caso (JSON)
ficticio: true
---

# Formato do caso (JSON)

O LLM devolve um único objeto JSON no formato 2, igual ao de `dados/casos/caso_exemplo.json`:

- `formato`: sempre 2. `id`, `titulo`, `vitima` (`nome`, `descricao`), `horario_do_crime` e `enredo` (até 120 palavras).
- `solucao`: `culpado`, `arma` e `comodo`. Vêm do sorteio e não podem mudar.
- `suspeitos` (5 ids), `armas` (5 ids) e `comodos` (os 6 ids): iguais aos enviados no pedido.
- `pistas`: 12 itens, 2 por cômodo, cada um com `id`, `comodo`, `texto` e `fatos` (lista, pode ser vazia).
- `respostas`: para cada suspeito, um objeto com as perguntas `q01` a `q10`. Cada resposta tem `texto` (1 ou 2 frases, no jeito de falar do personagem), `verdade` (true ou false) e `fato` (um fato ou null).

Use sempre os ids (`p04`, `a01`, `l01`) nos campos estruturados e os nomes só nos textos.

Qualquer campo faltando, id fora das listas ou caso reprovado pelo validador faz o caso ser descartado.

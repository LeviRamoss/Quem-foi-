---
id: g04
tipo: guia
titulo: Formato do caso (JSON)
ficticio: true
---

# Formato do caso (JSON)

O LLM devolve um único objeto JSON com estes campos:

- `id`, `titulo`, `enredo` (até 120 palavras)
- `solucao`: `culpado`, `arma`, `local` (vêm do sorteio e não podem mudar)
- `suspeitos`, `armas`, `locais`: listas com 5 nomes cada, iguais às sorteadas
- `cenas`: uma por local, com `descricao` e ids das pistas
- `pistas`: `id`, `texto` e `fato` estruturado (ver guia de pistas)
- `depoimentos`: `suspeito`, `pergunta`, `resposta`, `verdade` (true ou false) e `fato`

Qualquer campo faltando ou nome fora das listas faz o caso ser rejeitado.

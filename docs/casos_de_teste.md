# Casos de teste da fábrica de casos

Gerado por `python testes/casos_de_teste.py` em 17/11/2026 09:11. O resultado obtido é o que o código devolveu nesta execução.

| # | Caso | Entrada | Esperado | Obtido | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Caso de exemplo íntegro | dados/casos/caso_exemplo.json | aprovado | aprovado | passou |
| 2 | Falta uma pista (álibi da Rita) | caso de exemplo sem os fatos da pista pi04 | reprovado: mais de 1 solução | reprovado: as pistas deixam 3 soluções possíveis (precisa ser 1) | passou |
| 3 | Inocente mentindo | Helena (inocente) com resposta marcada como mentira | reprovado: só o culpado mente | reprovado: p01/q01: só o culpado pode mentir (+2 outros) | passou |
| 4 | Abertura entrega o local (bug achado no teste de QA) | abertura antiga: "...na poltrona da biblioteca..." | reprovado: abertura cita o cômodo | reprovado: a abertura ou o título entrega uma resposta: cita 'Biblioteca' | passou |
| 5 | IA devolve todos os textos corretos | JSON completo com título, abertura, 12 pistas e 50 respostas | aprovado | aprovado | passou |
| 6 | IA devolve texto que não é JSON | "Claro! Aqui está o caso: {titulo: ..." | reprovado: JSON inválido | reprovado: a IA não devolveu um JSON válido (Expecting value) | passou |
| 7 | IA tira o nome do suspeito do álibi | pista pi01 reescrita sem o nome | reprovado: pista não cita o suspeito | reprovado: pista pi01 não cita Bruno | passou |
| 8 | IA cita personagem fora do caso | pista pi02 cita Helena Valverde, que não é suspeito neste caso | reprovado: personagem fora do caso | reprovado: pista pi02 cita Helena Valverde, que não está no caso (+1 outros) | passou |
| 9 | IA entrega a arma na abertura | abertura citando "castiçal" | reprovado: abertura cita a arma | reprovado: a abertura ou o título entrega uma resposta: cita 'Castiçal' | passou |
| 10 | 300 casos seguidos do gerador local | 300 sorteios, cada um evitando o anterior | 300 aprovados, nenhuma repetição seguida | 300 aprovados, 0 repetições | passou |

## Tempo das etapas locais (média de 200 casos)

| Etapa | Tempo |
| --- | --- |
| Sorteio do caso (gerador local) | 0.6 ms (máx. 1.0) |
| Busca no RAG (contexto do caso) | 0.7 ms (máx. 1.0) |
| Validação lógica | 0.5 ms (máx. 0.8) |

## Tamanho do prompt (estimado: 4 caracteres por token)

| Prompt | Tokens de entrada (aprox.) |
| --- | --- |
| v1 | 4628 |
| v2 | 5134 |

Os tempos e tokens da chamada ao Gemini ficam em `fabrica/registro.csv`, gerado por `py fabrica/pipeline.py`.

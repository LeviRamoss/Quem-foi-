# Formato do caso (formato 2)

O caso é o arquivo que liga a **fábrica** (IA + validador) ao **jogo**. A fábrica escreve, o jogo só lê. Cada caso é um JSON em `dados/casos/`.

Exemplo completo e aprovado: [`dados/casos/caso_exemplo.json`](../dados/casos/caso_exemplo.json).

## Campos

| Campo | O que é |
| --- | --- |
| `formato` | Versão do formato. Hoje é `2`. |
| `id` | Identificador único do caso, como `caso_0042`. |
| `titulo` | Nome do caso, mostrado na abertura. |
| `vitima` | `nome` e `descricao` da vítima. |
| `horario_do_crime` | Faixa de horário, como `entre 21h30 e 22h`. |
| `enredo` | Texto de abertura, até 120 palavras. O crime acontece fora de cena. |
| `solucao` | `culpado`, `arma` e `comodo`. Sorteados pelo código, nunca pelo LLM. |
| `suspeitos` | 5 ids de `dados/personagens.json`. |
| `armas` | 5 ids de `dados/armas.json`. |
| `comodos` | Os 6 ids de `dados/comodos.json`. |
| `pistas` | 12 pistas, 2 por cômodo. Cada uma tem `id`, `comodo`, `texto` e `fatos`. |
| `respostas` | Para cada suspeito, a resposta às 10 perguntas de `dados/perguntas.json`: `texto`, `verdade` e `fato`. |

## Fatos

Os fatos são a parte que o validador entende. O jogador só vê o `texto`.

| Tipo | Campos | Significa |
| --- | --- | --- |
| `nao_e` | `categoria` (`suspeito`, `arma` ou `comodo`) e `item` | Esse item não é a resposta. |
| `estava_em` | `suspeito` e `comodo` | Na hora do crime, o suspeito estava nesse cômodo. Se ele for o culpado, o crime foi ali. |
| `nao_esteve_em` | `suspeito` e `comodo` | O suspeito não esteve nesse cômodo na hora do crime. |

Uma pista pode ter mais de um fato, ou nenhum (pista de clima, como o copo com cheiro amargo). Uma resposta tem no máximo um fato, ou `null`.

## O que o validador exige

Rode `python fabrica/validar.py dados/casos/<arquivo>.json`. O caso só é aprovado se:

1. Tiver 5 suspeitos, 5 armas e os 6 cômodos, todos da base.
2. Tiver exatamente 2 pistas por cômodo, citando só itens do caso.
3. Todos os fatos das pistas forem verdadeiros na solução.
4. **Só as pistas dos 6 cômodos** deixarem exatamente 1 das 150 combinações, e ela for a solução sorteada.
5. Cada suspeito responder às 10 perguntas.
6. Só o culpado mentir, pelo menos uma vez, e cada mentira tiver um fato **contradito por alguma pista**.

A regra 4 garante que quem visitar os 6 cômodos sempre consegue resolver o caso. O interrogatório ajuda a chegar mais rápido.

## Como o jogo usa o caso

- Ao entrar num cômodo, o jogador vê as 2 pistas daquele cômodo.
- No interrogatório, o jogo sorteia 3 das 10 perguntas, o jogador escolhe uma e um suspeito, e o jogo mostra `respostas[suspeito][pergunta].texto`.
- No palpite, o jogo compara cada item com `solucao` e mostra o que acertou e o que errou.

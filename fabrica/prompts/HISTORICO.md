# Histórico dos prompts

O prompt pede ao Gemini para **reescrever os textos** de um caso que o código já montou (sorteio, fatos, quem mente). A IA nunca decide a lógica: só escreve. Depois o validador confere tudo.

## v1 (17/11/2026)

Primeira versão. Pede para reescrever título, enredo, pistas e respostas mantendo a lógica, com tom noir, usando as fichas do RAG como contexto. Não diz o que cada texto precisa citar nem o que é proibido.

Arquivo: [`v1.md`](v1.md).

## v2 (17/11/2026)

Mudanças em relação à v1:

| Mudança | Por quê |
| --- | --- |
| Lista de palavras proibidas no enredo e no título (os 6 cômodos e as 5 armas do caso) | A abertura não pode entregar o local nem a arma; o validador reprova |
| "Deve citar" em cada pista e resposta (nome do suspeito no álibi, nome da arma descartada, cômodo no álibi) | Sem isso a pista perde a informação que o jogador precisa para deduzir |
| Limites de tamanho (enredo 120 palavras, pista 220 caracteres, resposta 200) | Textos longos não cabem nas janelas do jogo |
| Regras de tom e segurança (crime fora de cena, sem nomes reais) | Classificação a partir de 14 anos |
| Formato de saída com todas as chaves escritas | Evitar resposta sem alguma pista ou pergunta |
| Segunda tentativa recebe a lista de erros do validador (`{correcoes}`) | A IA corrige o que errou em vez de começar do zero |

Arquivo: [`v2.md`](v2.md).

## Resultados

Os números de cada versão (aprovação, tokens, tempo) ficam em `fabrica/registro.csv`, gerado por `python fabrica/pipeline.py`.

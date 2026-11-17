# fabrica

A fábrica de casos: o código monta a lógica, a IA escreve os textos, o validador confere.

| Arquivo | O que faz |
| --- | --- |
| `gerador_local.py` | Sorteia culpado, arma e cômodo e monta pistas e depoimentos com fatos lógicos. Também é o plano B do jogo quando não há casos da IA |
| `rag.py` | Fatia a `base_conhecimento/`, cria o índice TF-IDF (`indice_vetorial.json`) e busca o contexto de cada caso |
| `prompts/` | Prompts versionados (`v1.md`, `v2.md`) e o [histórico das mudanças](prompts/HISTORICO.md) |
| `pipeline.py` | Sorteio → RAG → Gemini → validação → registro, com até 3 tentativas. Linha de comando |
| `servidor.py` | As mesmas etapas como rotas HTTP em `127.0.0.1:8765`, para o n8n chamar |
| `validar.py` | Confere que o caso tem 1 solução, que só o culpado mente e que a abertura não entrega a resposta |
| `registro.csv` | Criado na primeira execução: uma linha por caso, com tokens, tempos e custo |

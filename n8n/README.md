# Fluxo do n8n: fábrica de casos

Arquivo para importar: [`fluxo_fabrica_casos.json`](fluxo_fabrica_casos.json)

```
Gatilho manual ─┐
Agenda diária ──┴─> 1. Preparar (sorteio + RAG) ─> 2. IA (Gemini) ─> 3. Validar ─> Aprovado? ─sim─> 4. Registrar
                                                        ^                              │não
                                                        └──────sim── Tentar de novo? <─┘  (até 3 tentativas)
                                                                          └─não─> 4. Registrar (reprovado)
```

| Etapa do fluxo | O que faz | Onde |
| --- | --- | --- |
| Gatilho | Manual (botão) ou agenda diária às 3h | n8n |
| 1. Preparar | O código sorteia o caso; o RAG busca as fichas dos itens sorteados | `fabrica/servidor.py` → `pipeline.preparar` |
| 2. IA | O Gemini reescreve título, abertura, pistas e respostas | `pipeline.chamar_gemini` |
| 3. Validar | Confere lógica, nomes e tamanho; se reprovar, manda os erros na próxima tentativa | `pipeline.validar_caso` |
| 4. Registrar | Grava `fabrica/registro.csv` (tokens, tempo, custo) e salva o caso aprovado em `dados/casos/ia/` | `pipeline.registrar` |

## Como rodar (Windows)

1. Instale o **Node.js LTS** (nodejs.org).
2. Na pasta do projeto, crie o arquivo `.env` com a linha `GEMINI_API_KEY=sua-chave`.
3. Abra um terminal na pasta do projeto e deixe o servidor rodando:
   ```
   py fabrica/servidor.py
   ```
4. Abra **outro** terminal e rode o n8n (a primeira vez demora alguns minutos):
   ```
   npx n8n
   ```
5. Abra **http://localhost:5678** no navegador, crie o usuário local e clique em **Create workflow**.
6. No menu **⋯** do canto de cima, escolha **Import from File** e selecione `n8n/fluxo_fabrica_casos.json`.
7. Clique em **Execute workflow**. Cada nó fica verde quando termina e mostra o tempo que levou.

Os casos aprovados aparecem no jogo na próxima partida: o jogo usa primeiro os casos da IA e, quando acabam, volta para o gerador local.

# Verificação de segredos

Gerado por `python testes/verificar_segredos.py` em 26/11/2026 17:41.

| O que foi conferido | Escopo | Resultado |
| --- | --- | --- |
| Arquivos do repositório | 150 arquivos | nenhum segredo |
| .env (onde fica a chave) | git ls-files e .gitignore | fora do git e listado no .gitignore |
| Histórico do git | 22 commits | nenhum segredo, .env nunca foi commitado |
| Fluxo do n8n exportado | 8 nós, URLs: http://127.0.0.1:8765/ia, http://127.0.0.1:8765/preparar, http://127.0.0.1:8765/registrar, http://127.0.0.1:8765/validar | sem credenciais, sem cabeçalho de chave, sem dados de execução, só chama o PC |

Padrões procurados: chave do Google (AIza...), GEMINI_API_KEY com valor, token da OpenAI/Anthropic, token do GitHub, chave privada.
A chave do Gemini fica só no arquivo `.env` do PC de quem roda a fábrica; o servidor local lê o `.env` e chama o Gemini, então o n8n nunca vê a chave.

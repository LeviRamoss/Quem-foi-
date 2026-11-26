# Experimento de fine-tuning

**Tarefa:** dado um par (pista, depoimento), dizer se o depoimento **contradiz**, **confirma** ou é **neutro** em relação à pista. É o que o validador precisa para perceber quando um depoimento escrito pela IA desmente uma pista sem querer.

| Item | Valor |
| --- | --- |
| Dados | `dados/treino.csv` (2.880 pares de 320 casos) e `dados/teste.csv` (720 pares de 80 outros casos), 1/3 de cada rótulo |
| Origem dos rótulos | A lógica dos casos (fatos), sem anotação manual. Metade dos "neutro" são casos difíceis (mesmo cômodo, pessoas diferentes) |
| Modelo base | BERTimbau base (`neuralmind/bert-base-portuguese-cased`) |
| Métrica | F1-macro no teste |

## Como rodar

1. `python fine_tuning/preparar_dados.py` (já rodado; os CSVs estão no repositório).
2. `python fine_tuning/baseline_classico.py` (linha de base clássica, precisa de `pip install scikit-learn pandas`).
3. BERTimbau no próprio PC: `py fine_tuning/treinar_bertimbau.py` (sem GPU usa o modo reduzido; instalação no começo do arquivo). Ou abra `experimento_bertimbau.ipynb` no Google Colab, escolha GPU T4 e clique em *Executar tudo* (uns 5 minutos).

## Resultados preliminares

Medidos com os mesmos dados de teste:

| Modelo | F1-macro |
| --- | --- |
| Acaso (sem treino) | 0,337 |
| Sempre a classe mais comum | 0,167 |
| TF-IDF + regressão logística, treinado (modelo clássico, não é fine-tuning) | 0,955 |
| BERTimbau base, sem fine-tuning | 0,185 |
| BERTimbau com fine-tuning (1.200 pares, 1 época, 6 min em CPU) | 0,958 |

O modelo clássico acerta todos os 240 `contradiz` e os 240 `confirma` e erra 32 dos 240 `neutro` (27 viram `confirma`, 5 viram `contradiz`), quase todos casos difíceis. Treino em 0,2 s. Arquivo: `resultados_preliminares_classico.json`.

**Limitação:** os textos de treino vêm dos modelos de texto do gerador local, então são repetitivos e a tarefa fica mais fácil do que com textos escritos pela IA. O próximo passo é montar o teste com casos gerados pelo Gemini.

**BERTimbau (17/11/2026, CPU, modo reduzido):** o fine-tuning levou o F1-macro de 0,185 para 0,958, igual à linha de base clássica. Acertou todos os 240 `contradiz` e 240 `confirma` e errou 30 dos 240 `neutro` (17 viraram `contradiz`, 13 `confirma`). Cerca de 70 ms por par em CPU. Arquivo: `resultados_bertimbau.json`.

## Comparação final (26/11/2026): base, base + RAG, ajustado e ajustado + RAG

`py fine_tuning/comparar_modelos.py` (CPU, modo reduzido: 1.200 pares de treino, 1 época) e `py fabrica/experimentos_gemini.py` (Gemini, 120 pares de `teste_120.csv`). Resultados em `resultados_comparacao.json` e `resultados_gemini.json`.

| Modelo | F1-macro (720 pares) | F1-macro (120 pares) | Tempo por par | Custo por 1.000 pares |
| --- | --- | --- | --- | --- |
| BERTimbau base | 0,185 | 0,230 | 74 ms (CPU) | US$ 0 (roda no PC) |
| BERTimbau base + RAG | 0,167 | 0,213 | 161 ms (CPU) | US$ 0 |
| **BERTimbau ajustado** | **0,958** | **0,986** | 81 ms (CPU) | US$ 0 (treino: 6,8 min de CPU, uma vez) |
| BERTimbau ajustado + RAG | 0,920 | 0,943 | 164 ms (CPU) | US$ 0 (treino: 15,6 min de CPU) |
| Gemini 3.5-flash-lite, sem RAG | — | 0,676 | 59 ms (em lotes de 20) | US$ 0 real; US$ 0,05 se pago |
| Gemini flash-lite, com RAG | — | 0,737 | 215 ms (em lotes de 20) | US$ 0 real; US$ 0,06 a 0,08 se pago |
| TF-IDF + regressão logística | 0,955 | — | menos de 1 ms | US$ 0 |

O fine-tuning compensou: +0,77 de F1 sobre o modelo base e +0,28 sobre o Gemini com RAG. O RAG ajudou o Gemini (+0,06), mas atrapalhou o BERTimbau ajustado (−0,04) e dobrou o tempo: os trechos recuperados são fichas de personagens e cômodos, que não ajudam a decidir se há contradição e ocupam espaço na entrada.

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
3. Abra `experimento_bertimbau.ipynb` no Google Colab, escolha GPU T4 e clique em *Executar tudo* (uns 5 minutos).

## Resultados preliminares

Medidos com os mesmos dados de teste:

| Modelo | F1-macro |
| --- | --- |
| Acaso (sem treino) | 0,337 |
| Sempre a classe mais comum | 0,167 |
| TF-IDF + regressão logística, treinado (modelo clássico, não é fine-tuning) | 0,955 |
| BERTimbau sem fine-tuning | rodar o caderno |
| BERTimbau com fine-tuning | rodar o caderno |

O modelo clássico acerta todos os 240 `contradiz` e os 240 `confirma` e erra 32 dos 240 `neutro` (27 viram `confirma`, 5 viram `contradiz`), quase todos casos difíceis. Treino em 0,2 s. Arquivo: `resultados_preliminares_classico.json`.

**Limitação:** os textos de treino vêm dos modelos de texto do gerador local, então são repetitivos e a tarefa fica mais fácil do que com textos escritos pela IA. O próximo passo é montar o teste com casos gerados pelo Gemini.

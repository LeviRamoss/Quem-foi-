# Custo por 1.000 usos e latência

Gerado por `python fabrica/custos.py` em 26/11/2026 17:41, com 11 execuções reais do `registro.csv`.

| Prompt | Casos | Aprovados | Modelo(s) | Latência total por caso | Só a IA | Tokens por caso (entrada + saída) | Custo real por 1.000 | Custo por 1.000 se fosse pago |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | 5 | 3/5 | gemini-3.1-flash-lite e gemini-3.6-flash | 66,9 s (mediana 44,3) | 66,4 s | 12.515 + 6.718 | US$ 0 | US$ 21,31 |
| v2 | 6 | 6/6 | gemini-3.1-flash-lite e gemini-3.6-flash | 72,1 s (mediana 67,9) | 70,8 s | 6.351 + 6.212 | US$ 0 | US$ 26,82 |
| todos | 11 | 9/11 | gemini-3.1-flash-lite e gemini-3.6-flash | 69,7 s (mediana 54,0) | 68,8 s | 9.153 + 6.442 | US$ 0 | US$ 24,31 |

Preços pagos por milhão de tokens (entrada / saída): gemini-3.1-flash-lite US$ 0,25 / 1,50; gemini-3.5-flash-lite US$ 0,30 / 2,50; gemini-3.6-flash US$ 0,75 / 3,75; gemini-3.8-flash US$ 0,75 / 3,75 (ai.google.dev/pricing, 26/11/2026).
Jogar não custa nada: o jogo só lê casos já aprovados, sem chamar a IA.

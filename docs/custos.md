# Custo por 1.000 usos e latência

Gerado por `python fabrica/custos.py` em 26/11/2026 17:53, com 16 execuções reais do `registro.csv`.

| Prompt | Casos | Aprovados | Modelo(s) | Latência total por caso | Só a IA | Tokens por caso (entrada + saída) | Custo real por 1.000 | Custo por 1.000 se fosse pago |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | 5 | 3/5 | gemini-3.1-flash-lite e gemini-3.6-flash | 66,9 s (mediana 44,3) | 66,4 s | 12.515 + 6.718 | US$ 0 | US$ 21,31 |
| v2 | 6 | 6/6 | gemini-3.1-flash-lite e gemini-3.6-flash | 72,1 s (mediana 67,9) | 70,8 s | 6.351 + 6.212 | US$ 0 | US$ 26,82 |
| v3 | 5 | 5/5 | gemini-3.5-flash-lite | 9,7 s (mediana 9,7) | 9,7 s | 11.661 + 3.176 | US$ 0 | US$ 11,44 |
| todos | 16 | 14/16 | gemini-3.1-flash-lite e gemini-3.5-flash-lite e gemini-3.6-flash | 51,0 s (mediana 40,4) | 50,3 s | 9.937 + 5.421 | US$ 0 | US$ 20,29 |

Preços pagos por milhão de tokens (entrada / saída): gemini-3.1-flash-lite US$ 0,25 / 1,50; gemini-3.5-flash-lite US$ 0,30 / 2,50; gemini-3.6-flash US$ 0,75 / 3,75; gemini-3.8-flash US$ 0,75 / 3,75 (ai.google.dev/pricing, 26/11/2026).
Jogar não custa nada: o jogo só lê casos já aprovados, sem chamar a IA.

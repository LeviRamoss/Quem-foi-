"""Linha de base do experimento de fine-tuning (modelo clássico, sem rede neural).

Treina TF-IDF + regressão logística em dados/treino.csv e mede o F1-macro em
dados/teste.csv, junto com duas referências sem treino (acaso e classe mais comum).

Uso:  pip install scikit-learn pandas
      python fine_tuning/baseline_classico.py
Saída: fine_tuning/resultados_preliminares_classico.json
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score

AQUI = Path(__file__).resolve().parent
ROTULOS = ["contradiz", "confirma", "neutro"]

treino = pd.read_csv(AQUI / "dados" / "treino.csv")
teste = pd.read_csv(AQUI / "dados" / "teste.csv")


def juntar(df):
    return (df["pista"] + " [SEP] " + df["depoimento"]).tolist()


rng = np.random.default_rng(0)
acaso = f1_score(teste["rotulo"], rng.choice(ROTULOS, len(teste)), average="macro")
comum = f1_score(teste["rotulo"], [treino["rotulo"].mode()[0]] * len(teste), average="macro")

t0 = time.perf_counter()
vet = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
modelo = LogisticRegression(max_iter=2000).fit(vet.fit_transform(juntar(treino)), treino["rotulo"])
seg = time.perf_counter() - t0
prev = modelo.predict(vet.transform(juntar(teste)))
f1 = f1_score(teste["rotulo"], prev, average="macro")

res = {
    "f1_macro": {"acaso (sem treino)": round(acaso, 3), "classe mais comum": round(comum, 3),
                 "TF-IDF + regressão logística (treinado)": round(f1, 3)},
    "treino_s": round(seg, 2), "n_treino": len(treino), "n_teste": len(teste),
    "matriz_confusao": {"ordem": ROTULOS,
                        "valores": confusion_matrix(teste["rotulo"], prev, labels=ROTULOS).tolist()},
}
(AQUI / "resultados_preliminares_classico.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))

"""Comparação do fine-tuning: BERTimbau base, base + RAG, ajustado e ajustado + RAG.

Tarefa: dado (pista, depoimento), dizer se o depoimento contradiz, confirma ou é neutro.
RAG: os 3 trechos da base de conhecimento mais parecidos com o par (fabrica/rag.py, mesmo
filtro contra prompt injection) entram no texto de entrada, depois do depoimento.

Sem GPU usa o modo reduzido (o mesmo de treinar_bertimbau.py): treino com 1.200 pares
(400 por rótulo) e 1 época. O teste é sempre o mesmo: 720 pares de 80 casos que não estão no
treino; também mede nos 120 pares de teste_120.csv, os mesmos usados com o Gemini.

Instalar (se ainda não tiver):
    py -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    py -m pip install transformers datasets accelerate scikit-learn pandas
Rodar (leva uns 30 minutos em CPU):
    py fine_tuning/comparar_modelos.py
Saída: fine_tuning/resultados_comparacao.json
"""
import inspect
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import confusion_matrix, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "fabrica"))
import rag  # noqa: E402
import seguranca  # noqa: E402

MODELO = "neuralmind/bert-base-portuguese-cased"
ROTULOS = ["contradiz", "confirma", "neutro"]
ID = {r: i for i, r in enumerate(ROTULOS)}
GPU = torch.cuda.is_available()

treino = pd.read_csv(AQUI / "dados" / "treino.csv")
teste = pd.read_csv(AQUI / "dados" / "teste.csv")
sub = pd.read_csv(AQUI / "dados" / "teste_120.csv")
if GPU:
    EPOCAS = 2
else:
    treino = treino.groupby("rotulo", group_keys=False).sample(400, random_state=42).reset_index(drop=True)
    EPOCAS = 1
chave_sub = set(zip(sub["pista"], sub["depoimento"]))
no_sub = np.array([(p, d) in chave_sub for p, d in zip(teste["pista"], teste["depoimento"])])
print(f"Treino {len(treino)} pares | teste {len(teste)} (+ {no_sub.sum()} do conjunto de 120) | {EPOCAS} época(s) | "
      f"{'GPU' if GPU else 'CPU'}")

_cache = {}


def contexto(pista, dep):
    k = (pista, dep)
    if k not in _cache:
        trechos, _ = seguranca.filtrar_trechos(rag.contexto_par(pista, dep, k=3))
        _cache[k] = " ".join(t["texto"].replace("\n", " ") for t in trechos)
    return _cache[k]


tok = AutoTokenizer.from_pretrained(MODELO)


def preparar(df, com_rag):
    maxlen = 256 if com_rag else 128
    segundo = [d + (" Contexto: " + contexto(p, d) if com_rag else "") for p, d in zip(df["pista"], df["depoimento"])]
    ds = Dataset.from_dict({"pista": list(df["pista"]), "segundo": segundo, "label": [ID[r] for r in df["rotulo"]]})
    return ds.map(lambda b: tok(b["pista"], b["segundo"], truncation="only_second", max_length=maxlen,
                                padding="max_length"), batched=True)


def argumentos():
    cfg = dict(output_dir=str(AQUI / "saida"), num_train_epochs=EPOCAS, per_device_train_batch_size=16,
               per_device_eval_batch_size=64, learning_rate=2e-5, weight_decay=0.01,
               warmup_steps=max(1, int(0.1 * EPOCAS * len(treino) / 16)), logging_steps=10, save_strategy="no",
               report_to="none", fp16=GPU, seed=42, use_cpu=not GPU)
    aceitas = inspect.signature(TrainingArguments.__init__).parameters
    return TrainingArguments(**{k: v for k, v in cfg.items() if k in aceitas})


def avaliar(trainer, ds, nome):
    t0 = time.time()
    pred = trainer.predict(ds)
    seg = time.time() - t0
    y_pred, y_true = pred.predictions.argmax(-1), pred.label_ids
    f1 = f1_score(y_true, y_pred, average="macro")
    f1_120 = f1_score(y_true[no_sub], y_pred[no_sub], average="macro")
    acc = float((y_true == y_pred).mean())
    print(f"\n== {nome}: F1-macro {f1:.3f} (720 pares) | {f1_120:.3f} (120 pares) | {seg / len(ds) * 1000:.1f} ms por par")
    print(confusion_matrix(y_true, y_pred, labels=[0, 1, 2]))
    return {"f1_macro_720": round(float(f1), 3), "f1_macro_120": round(float(f1_120), 3), "acerto_720": round(acc, 3),
            "ms_por_par": round(seg / len(ds) * 1000, 1),
            "matriz_720": confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist()}


res = {"modelo": MODELO, "dispositivo": torch.cuda.get_device_name(0) if GPU else "cpu", "pares_treino": len(treino),
       "epocas": EPOCAS, "pares_teste": len(teste), "ordem_matriz": ROTULOS, "custo_api_usd": 0}
for com_rag in (False, True):
    sufixo = " + RAG" if com_rag else ""
    print(f"\n######## {'COM' if com_rag else 'SEM'} RAG ########")
    ds_treino, ds_teste = preparar(treino, com_rag), preparar(teste, com_rag)
    torch.manual_seed(42)
    modelo = AutoModelForSequenceClassification.from_pretrained(MODELO, num_labels=3)
    trainer = Trainer(model=modelo, args=argumentos(), train_dataset=ds_treino)
    res[f"base{sufixo}"] = avaliar(trainer, ds_teste, f"BERTimbau base{sufixo}")
    t0 = time.time()
    trainer.train()
    minutos = (time.time() - t0) / 60
    res[f"ajustado{sufixo}"] = avaliar(trainer, ds_teste, f"BERTimbau ajustado{sufixo}")
    res[f"ajustado{sufixo}"]["minutos_de_treino"] = round(minutos, 1)
    (AQUI / "resultados_comparacao.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

print("\n" + json.dumps({k: v for k, v in res.items() if isinstance(v, dict)}, ensure_ascii=False, indent=1))
print("\nPronto. Tire um print desta tela para o relatório.")

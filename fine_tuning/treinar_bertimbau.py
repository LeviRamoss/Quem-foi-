"""Fine-tuning do BERTimbau rodando no próprio PC (sem Colab), mesma tarefa do caderno.

Sem GPU usa o modo reduzido: 1.200 pares de treino (400 por rótulo), 1 época, até 128 tokens.
Teste sempre com os 720 pares de 80 casos que não aparecem no treino.

Instalar (uma vez, uns 5 minutos):
    py -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    py -m pip install transformers datasets accelerate scikit-learn pandas
Rodar:
    py fine_tuning/treinar_bertimbau.py
Saída: fine_tuning/resultados_bertimbau.json
"""
import inspect
import json
import time
from pathlib import Path

import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

AQUI = Path(__file__).resolve().parent
MODELO = "neuralmind/bert-base-portuguese-cased"
ROTULOS = ["contradiz", "confirma", "neutro"]
ID = {r: i for i, r in enumerate(ROTULOS)}

treino = pd.read_csv(AQUI / "dados" / "treino.csv")
teste = pd.read_csv(AQUI / "dados" / "teste.csv")
GPU = torch.cuda.is_available()
if GPU:
    EPOCAS, MAXLEN = 2, 160
else:
    treino = treino.groupby("rotulo", group_keys=False).sample(400, random_state=42).reset_index(drop=True)
    EPOCAS, MAXLEN = 1, 128
    torch.set_num_threads(max(1, torch.get_num_threads()))
print(f"Treino: {len(treino)} pares | teste: {len(teste)} | {EPOCAS} época(s) | "
      f"{'GPU ' + torch.cuda.get_device_name(0) if GPU else 'CPU (modo reduzido)'}")

tok = AutoTokenizer.from_pretrained(MODELO)


def preparar(df):
    ds = Dataset.from_pandas(df.assign(label=df["rotulo"].map(ID))[["pista", "depoimento", "label"]])
    return ds.map(lambda b: tok(b["pista"], b["depoimento"], truncation=True, max_length=MAXLEN,
                                padding="max_length"), batched=True)


ds_treino, ds_teste = preparar(treino), preparar(teste)


def avaliar(trainer, nome):
    t0 = time.time()
    pred = trainer.predict(ds_teste)
    seg = time.time() - t0
    y_pred, y_true = pred.predictions.argmax(-1), pred.label_ids
    f1 = f1_score(y_true, y_pred, average="macro")
    print(f"\n== {nome}: F1-macro = {f1:.3f}  ({seg / len(teste) * 1000:.1f} ms por par)")
    print(classification_report(y_true, y_pred, target_names=ROTULOS, digits=3))
    print(confusion_matrix(y_true, y_pred))
    return round(float(f1), 3), round(seg / len(teste) * 1000, 2)


cfg = dict(output_dir=str(AQUI / "saida"), num_train_epochs=EPOCAS, per_device_train_batch_size=16,
           per_device_eval_batch_size=64, learning_rate=2e-5, weight_decay=0.01,
           warmup_steps=max(1, int(0.1 * EPOCAS * len(treino) / 16)), logging_steps=10, save_strategy="no",
           report_to="none", fp16=GPU, seed=42, use_cpu=not GPU)
aceitas = inspect.signature(TrainingArguments.__init__).parameters
args = TrainingArguments(**{k: v for k, v in cfg.items() if k in aceitas})

torch.manual_seed(42)
modelo = AutoModelForSequenceClassification.from_pretrained(MODELO, num_labels=3)
trainer = Trainer(model=modelo, args=args, train_dataset=ds_treino)
f1_base, ms_base = avaliar(trainer, "BERTimbau BASE (sem fine-tuning)")

t0 = time.time()
trainer.train()
minutos = (time.time() - t0) / 60
print(f"\nTreino: {minutos:.1f} min")
f1_ft, ms_ft = avaliar(trainer, "BERTimbau com FINE-TUNING")

res = {"modelo": MODELO, "pares_treino": len(treino), "pares_teste": len(teste), "epocas": EPOCAS,
       "f1_base_sem_treino": f1_base, "f1_fine_tuning": f1_ft, "minutos_de_treino": round(minutos, 1),
       "ms_por_par_base": ms_base, "ms_por_par_fine_tuning": ms_ft,
       "dispositivo": torch.cuda.get_device_name(0) if GPU else "cpu"}
(AQUI / "resultados_bertimbau.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n" + json.dumps(res, ensure_ascii=False, indent=1))
print("\nTire um print desta tela para o relatório.")

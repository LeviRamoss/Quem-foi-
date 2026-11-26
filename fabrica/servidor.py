"""Servidor local que o n8n chama, uma rota por etapa da fábrica de casos.

Rodar (deixe esta janela aberta):
    py fabrica/servidor.py

Rotas (POST, corpo e resposta em JSON; cada etapa devolve tudo o que a próxima precisa):
    /preparar   {"versao": "v3"}         -> sorteio do caso + contexto do RAG + prompt
    /ia         (saída de /preparar)     -> chama o Gemini (ou simula, se não houver chave)
    /validar    (saída de /ia)           -> aplica os textos e confere; prepara correções
    /registrar  (saída de /validar)      -> grava fabrica/registro.csv e salva o caso aprovado
    GET /status                          -> teste rápido se o servidor está no ar
Só usa a biblioteca padrão do Python.
"""
from __future__ import annotations

import json
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import pipeline  # noqa: E402

PORTA = 8765
ENV = pipeline.ler_env()
CHAVE = ENV.get("GEMINI_API_KEY", "")
MODELOS = ([ENV["GEMINI_MODELO"]] if ENV.get("GEMINI_MODELO") else []) + pipeline.MODELOS_PADRAO
RNG = random.Random()


def preparar(corpo):
    prep = pipeline.preparar(RNG, corpo.get("versao", "v3"))
    prep.update({"tentativa": 0, "tokens_entrada": 0, "tokens_saida": 0, "ms_ia": 0, "ms_validar": 0,
                 "erros_na_1a": None, "inicio": time.time(), "prompt_atual": prep["prompt"]})
    return prep


def ia(corpo):
    simular = not CHAVE or corpo.get("simular")
    r = pipeline.simular_ia(corpo) if simular else pipeline.chamar_gemini(corpo["sistema"], corpo["prompt_atual"], CHAVE, MODELOS)
    corpo["tentativa"] += 1
    corpo["tokens_entrada"] += r["tokens_entrada"]
    corpo["tokens_saida"] += r["tokens_saida"]
    corpo["ms_ia"] += r["ms"]
    corpo["modelo"] = r["modelo"]
    corpo["texto_ia"] = r["texto"]
    return corpo


def validar(corpo):
    res = pipeline.validar_caso(corpo["esqueleto"], corpo["texto_ia"])
    corpo["ms_validar"] += res["ms"]
    if corpo["erros_na_1a"] is None:
        corpo["erros_na_1a"] = len(res["erros"])
    corpo["aprovado"] = res["aprovado"]
    corpo["erros"] = res["erros"]
    corpo["caso"] = res["caso"]
    corpo["pode_tentar_de_novo"] = (not res["aprovado"]) and corpo["tentativa"] < pipeline.MAX_TENTATIVAS
    if corpo["pode_tentar_de_novo"] and corpo["versao"] != "v1":
        lista = "\n".join(f"- {e}" for e in res["erros"][:15])
        corpo["prompt_atual"] = corpo["prompt"].replace(
            "## Contexto (base de conhecimento)",
            f"## Correções da tentativa anterior (resolva todas)\n{lista}\n\n## Contexto (base de conhecimento)", 1)
    return corpo


def registrar(corpo):
    caso = corpo.get("caso")
    tin, tout = corpo["tokens_entrada"], corpo["tokens_saida"]
    linha = {
        "data": time.strftime("%Y-%m-%d %H:%M:%S"), "caso": caso["id"] if caso else corpo["esqueleto"]["id"],
        "prompt": corpo["versao"] + " (n8n)", "tentativas": corpo["tentativa"], "modelo": corpo.get("modelo", ""),
        "aprovado": corpo.get("aprovado", False), "erros_na_1a": corpo["erros_na_1a"],
        "primeiro_erro": (corpo.get("erros") or [""])[0], "tokens_entrada": tin, "tokens_saida": tout,
        "ms_sorteio": corpo["ms"]["sorteio"], "ms_rag": corpo["ms"]["rag"], "ms_ia": round(corpo["ms_ia"]),
        "ms_validar": round(corpo["ms_validar"], 1), "ms_total": round((time.time() - corpo["inicio"]) * 1000),
        "custo_real_usd": 0, "custo_se_fosse_pago_usd": pipeline.custo(corpo.get("modelo", ""), tin, tout),
    }
    pipeline.registrar(linha, caso)
    return {"registrado": True, **linha, "titulo": caso["titulo"] if caso else "", "erros": corpo.get("erros", [])}


ROTAS = {"/preparar": preparar, "/ia": ia, "/validar": validar, "/registrar": registrar}


class Handler(BaseHTTPRequestHandler):
    def _responder(self, codigo, obj):
        dados = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path.startswith("/status"):
            self._responder(200, {"ok": True, "ia": "gemini" if CHAVE else "simulada", "modelos": MODELOS})
        else:
            self._responder(404, {"erro": "rota não existe"})

    def do_POST(self):
        rota = ROTAS.get(self.path.split("?")[0])
        if not rota:
            self._responder(404, {"erro": "rota não existe"})
            return
        tamanho = int(self.headers.get("Content-Length", 0) or 0)
        corpo = json.loads(self.rfile.read(tamanho) or b"{}") if tamanho else {}
        if isinstance(corpo, list):      # o n8n às vezes manda uma lista com 1 item
            corpo = corpo[0] if corpo else {}
        try:
            self._responder(200, rota(corpo))
        except pipeline.ErroIA as e:
            self._responder(502, {"erro": str(e)})
        except Exception as e:   # noqa: BLE001
            self._responder(500, {"erro": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        print(time.strftime("%H:%M:%S"), self.command, self.path, args[1] if len(args) > 1 else "")


if __name__ == "__main__":
    print(f"Fábrica de casos no ar: http://localhost:{PORTA}  (IA: {'Gemini' if CHAVE else 'SIMULADA, falta GEMINI_API_KEY no .env'})")
    print("Deixe esta janela aberta e rode o fluxo no n8n. Ctrl+C para parar.")
    ThreadingHTTPServer(("127.0.0.1", PORTA), Handler).serve_forever()

"""Confere que nenhum segredo vazou: nos arquivos do repositório, no histórico do git e no fluxo do n8n.

Procura chaves do Google (AIza...), a GEMINI_API_KEY com valor, tokens e senhas comuns, confere que
o .env não está no git e que o fluxo exportado do n8n não guarda credenciais, cabeçalhos de chave,
dados de execução (pinData) nem endereços fora do PC.

Uso:   python testes/verificar_segredos.py
Saída: docs/verificacao_segredos.md (e código de saída 1 se achar algo)
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PADROES = {
    "chave do Google (AIza...)": r"AIza[0-9A-Za-z_\-]{35}",
    "GEMINI_API_KEY com valor": r"GEMINI_API_KEY\s*=\s*(?!coloque-sua-chave-aqui|sua-chave|\s*$)[^\s\"']{8,}",
    "token da OpenAI/Anthropic": r"\bsk-(ant-)?[A-Za-z0-9_\-]{20,}",
    "token do GitHub": r"\bgh[pousr]_[A-Za-z0-9]{30,}",
    "chave privada": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
}
BINARIOS = (".png", ".jpg", ".jpeg", ".webp", ".mp3", ".ogg", ".wav", ".pdf", ".pyc", ".ipynb")


def git(*args):
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


linhas, problemas = [], []
arquivos = [a for a in git("ls-files").splitlines() if a]

# 1. arquivos atuais
achados = []
for a in arquivos:
    if a.lower().endswith(BINARIOS):
        continue
    texto = (RAIZ / a).read_text(encoding="utf-8", errors="replace")
    for nome, p in PADROES.items():
        for m in re.finditer(p, texto):
            achados.append(f"{a}: {nome}")
linhas.append(("Arquivos do repositório", f"{len(arquivos)} arquivos", "nenhum segredo" if not achados else "; ".join(achados)))
problemas += achados

# 2. o .env fora do git
env_no_git = [a for a in arquivos if Path(a).name == ".env"]
ignorado = ".env" in (RAIZ / ".gitignore").read_text(encoding="utf-8").split()
linhas.append((".env (onde fica a chave)", "git ls-files e .gitignore",
               "fora do git e listado no .gitignore" if not env_no_git and ignorado else f"PROBLEMA: {env_no_git} ignorado={ignorado}"))
if env_no_git or not ignorado:
    problemas.append(".env no git")

# 3. histórico inteiro do git
historico = git("log", "-p", "--all", "--no-color")
n_commits = len(git("rev-list", "--all").split())
achados_h = sorted({nome for nome, p in PADROES.items() if re.search(p, historico)})
env_hist = [l for l in git("log", "--all", "--name-only", "--format=").splitlines() if Path(l).name == ".env"]
linhas.append(("Histórico do git", f"{n_commits} commits",
               "nenhum segredo, .env nunca foi commitado" if not achados_h and not env_hist else f"PROBLEMA: {achados_h} {env_hist[:3]}"))
problemas += achados_h + env_hist

# 4. fluxo do n8n
fluxo_arq = RAIZ / "n8n" / "fluxo_fabrica_casos.json"
fluxo = json.loads(fluxo_arq.read_text(encoding="utf-8"))
texto_fluxo = json.dumps(fluxo, ensure_ascii=False)
nos = fluxo.get("nodes", [])
com_credencial = [n["name"] for n in nos if n.get("credentials")]
urls = sorted({n.get("parameters", {}).get("url", "") for n in nos if n.get("parameters", {}).get("url")})
fora_do_pc = [u for u in urls if not re.match(r"https?://(127\.0\.0\.1|localhost)(:\d+)?/", u)]
cabecalho_chave = re.search(r"x-goog-api-key|authorization|bearer", texto_fluxo, re.I)
pin = bool(fluxo.get("pinData"))
ok_fluxo = not (com_credencial or fora_do_pc or cabecalho_chave or pin or any(re.search(p, texto_fluxo) for p in PADROES.values()))
linhas.append(("Fluxo do n8n exportado", f"{len(nos)} nós, URLs: {', '.join(urls)}",
               "sem credenciais, sem cabeçalho de chave, sem dados de execução, só chama o PC" if ok_fluxo else
               f"PROBLEMA: credenciais={com_credencial} fora={fora_do_pc} cabeçalho={bool(cabecalho_chave)} pinData={pin}"))
if not ok_fluxo:
    problemas.append("fluxo do n8n")

saida = ["# Verificação de segredos", "",
         f"Gerado por `python testes/verificar_segredos.py` em {time.strftime('%d/%m/%Y %H:%M')}.", "",
         "| O que foi conferido | Escopo | Resultado |", "| --- | --- | --- |"]
saida += [f"| {a} | {b} | {c} |" for a, b, c in linhas]
saida += ["", "Padrões procurados: " + ", ".join(PADROES) + ".",
          "A chave do Gemini fica só no arquivo `.env` do PC de quem roda a fábrica; o servidor local lê o `.env` "
          "e chama o Gemini, então o n8n nunca vê a chave."]
(RAIZ / "docs" / "verificacao_segredos.md").write_text("\n".join(saida) + "\n", encoding="utf-8")
print("\n".join(saida))
sys.exit(1 if problemas else 0)

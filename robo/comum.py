"""Peças comuns do robô do Pisca no GitHub Actions."""
import json, os, re, subprocess
from datetime import datetime, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
FILA = RAIZ / "fila"
ESTADO = RAIZ / "estado"
G = "https://graph.facebook.com/v23.0"
DONO = os.environ.get("DONO", "jmiguevf")

# Horários (Brasília). Reels e carrossel da mesma edição nunca têm a mesma notícia.
EDICOES = {
    "manha": {"nome": "manhã", "rotulo": "MANHÃ", "reels": "07:00", "carrossel": "08:00", "piscada": "Piscada da manhã"},
    "meio": {"nome": "meio-dia", "rotulo": "MEIO-DIA", "reels": "12:00", "carrossel": "13:00", "piscada": "Piscada do meio-dia"},
    "noite": {"nome": "noite", "rotulo": "NOITE", "reels": "18:30", "carrossel": "19:30", "piscada": "Piscada da noite"},
}
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


def agora():
    """hora de Brasília (o runner roda em UTC)"""
    return datetime.utcnow() - timedelta(hours=3)


def ler(p, padrao=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return padrao


def gravar(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def legendas_recentes(n=40):
    """últimas legendas do Instagram (para não repetir notícia e não publicar em dobro)"""
    ig, tok = os.environ.get("IG_USER_ID"), os.environ.get("META_PAGE_TOKEN")
    if not (ig and tok):
        return []
    r = requests.get(f"{G}/{ig}/media", params={"fields": "caption,timestamp,media_product_type,permalink",
                                              "limit": n, "access_token": tok}, timeout=60).json()
    return r.get("data", [])


# ---------------------------------------------------------------- GitHub (gh já vem no runner)
def gh(*args, entrada=None):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, input=entrada)
    if r.returncode != 0:
        print("gh falhou:", " ".join(args[:3]), r.stderr[-300:])
    return r.stdout.strip()


def abrir_issue(titulo, corpo, rotulo):
    gh("label", "create", rotulo, "--force", "--color", "FFB000")
    out = gh("issue", "create", "--title", titulo, "--label", rotulo, "--assignee", DONO, "--body-file", "-",
             entrada=corpo)
    m = re.search(r"/issues/(\d+)", out)
    return int(m.group(1)) if m else None


def comentar(numero, texto):
    if numero:
        gh("issue", "comment", str(numero), "--body-file", "-", entrada=texto)


def fechar(numero, texto=None):
    if numero:
        if texto:
            comentar(numero, texto)
        gh("issue", "close", str(numero))


def alerta(titulo, corpo):
    """abre issue de alerta (o GitHub manda e-mail), sem duplicar a que já está aberta com o mesmo título"""
    abertas = json.loads(gh("issue", "list", "--label", "alerta", "--state", "open", "--json", "title") or "[]")
    if any(i["title"] == titulo for i in abertas):
        return
    abrir_issue(titulo, corpo, "alerta")


def cancelamentos(numero):
    """comentários do dono na prévia: 'cancelar', 'cancelar reels', 'cancelar carrossel', 'cancelar tudo'"""
    if not numero:
        return set()
    d = json.loads(gh("issue", "view", str(numero), "--json", "comments") or "{}")
    fora = set()
    for c in d.get("comments", []):
        if (c.get("author") or {}).get("login", "").lower() != DONO.lower():
            continue
        for linha in c.get("body", "").lower().splitlines():
            linha = linha.strip()
            if linha.startswith("cancelar") or linha.startswith("cancela"):
                resto = linha.split(maxsplit=1)[1] if " " in linha else "tudo"
                if "reel" in resto:
                    fora.add("reels")
                elif "carross" in resto:
                    fora.add("carrossel")
                else:
                    fora |= {"reels", "carrossel"}
    return fora


def env_sem_chaves():
    """ambiente para o agente de produção: sem nenhuma chave de publicação (ele não publica)"""
    fora = {"META_PAGE_TOKEN", "THREADS_TOKEN", "MIDIA_TOKEN", "GH_TOKEN", "GITHUB_TOKEN", "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN", "TIKTOK_TOKEN"}
    env = {k: v for k, v in os.environ.items() if k not in fora}
    if env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        env["CLAUDE_CODE_OAUTH_TOKEN"] = re.sub(r"\s+", "", env["CLAUDE_CODE_OAUTH_TOKEN"])
    env["DISABLE_AUTOUPDATER"] = "1"
    return env

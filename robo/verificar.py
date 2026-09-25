#!/usr/bin/env python3
"""Confere as ligações do robô sem publicar nada: Claude, Instagram, Página, Threads e o pisca-midia."""
import os, subprocess, sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import G, alerta, env_sem_chaves  # noqa: E402

E = os.environ.get


def claude():
    if not (E("CLAUDE_CODE_OAUTH_TOKEN") or E("ANTHROPIC_API_KEY")):
        return "falta o secret CLAUDE_CODE_OAUTH_TOKEN"
    r = subprocess.run(["claude", "-p", "--model", E("MODELO_RAPIDO", "claude-sonnet-5"), "--max-turns", "1"],
                       input="Responda só: OK", capture_output=True, text=True, env=env_sem_chaves(), timeout=300)
    return "ok" if "OK" in r.stdout else f"recusou: {(r.stdout + r.stderr)[-200:]}"


def instagram():
    j = requests.get(f"{G}/{E('IG_USER_ID')}", params={"fields": "username,followers_count",
                                                     "access_token": E("META_PAGE_TOKEN")}, timeout=60).json()
    return f"ok (@{j['username']}, {j.get('followers_count')} seguidores)" if "username" in j else f"recusou: {j.get('error', {}).get('message')}"


def pagina():
    j = requests.get(f"{G}/{E('FB_PAGE_ID')}", params={"fields": "name", "access_token": E("META_PAGE_TOKEN")},
                     timeout=60).json()
    return f"ok ({j['name']})" if "name" in j else f"recusou: {j.get('error', {}).get('message')}"


def threads():
    if not E("THREADS_TOKEN"):
        return "sem chave"
    j = requests.get("https://graph.threads.net/v1.0/me", params={"fields": "username",
                                                                 "access_token": E("THREADS_TOKEN")}, timeout=60).json()
    return f"ok (@{j['username']})" if "username" in j else f"recusou: {j.get('error', {}).get('message')}"


def midia():
    if not E("MIDIA_TOKEN"):
        return "sem chave (Threads vai com capa + link)"
    j = requests.get(f"https://api.github.com/repos/{E('MIDIA_REPO', 'jmiguevf/pisca-midia')}",
                     headers={"Authorization": f"Bearer {E('MIDIA_TOKEN')}"}, timeout=60).json()
    return "ok" if (j.get("permissions") or {}).get("push") else f"sem permissão de escrita: {j.get('message')}"


def youtube():
    if not (E("YT_CLIENT_ID") and E("YT_REFRESH_TOKEN")):
        return "sem chave (Shorts não saem)"
    tok = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": E("YT_CLIENT_ID"), "client_secret": E("YT_CLIENT_SECRET"),
        "refresh_token": E("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=60).json()
    if "access_token" not in tok:
        return f"recusou: {tok.get('error_description') or tok.get('error')}"
    j = requests.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"},
                     headers={"Authorization": f"Bearer {tok['access_token']}"}, timeout=60).json()
    it = j.get("items") or []
    return f"ok ({it[0]['snippet']['title']})" if it else f"recusou: {j.get('error', {}).get('message', 'sem canal')}"


def main():
    linhas, ruim = [], False
    for nome, f in (("Claude", claude), ("Instagram", instagram), ("Página do Facebook", pagina),
                    ("Threads", threads), ("pisca-midia (vídeo do Threads)", midia), ("YouTube", youtube)):
        try:
            r = f()
        except Exception as e:
            r = f"erro: {str(e)[:200]}"
        ruim |= not r.startswith("ok")
        linhas.append(f"| {nome} | {r} |")
    txt = "| Ligação | Situação |\n|---|---|\n" + "\n".join(linhas)
    print(txt)
    if E("GITHUB_STEP_SUMMARY"):
        Path(E("GITHUB_STEP_SUMMARY")).write_text(txt + "\n", encoding="utf-8")
    if ruim:
        alerta("Ligação com problema", txt + "\n\nDepois de corrigir, rode Verificar ligações de novo e feche esta issue.")
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main())

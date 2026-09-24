#!/usr/bin/env python3
"""Robô publicador: solta no horário o que está na fila e não foi cancelado na prévia.

Uso: python3 robo/publicar.py            (publica o que venceu E foi APROVADO: de 10 min antes do horário até 6 h depois)
     python3 robo/publicar.py --agora ID (publica já a edição ID, ignorando o horário)
Cada item passa de novo pelas travas (checar_edicao.py) e só então vai para publica_tudo.py
(Instagram + Facebook + stories + Threads). Antes de tentar de novo, confere se já saiu (nunca publica em dobro).
"""
import json, os, re, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import EDICOES, FILA, RAIZ, agora, alerta, aprovacoes, cancelamentos, comentar, fechar, gh, gravar, legendas_recentes, ler  # noqa: E402

ANTES, DEPOIS = timedelta(minutes=10), timedelta(hours=6)


def baixa_artefato(ag):
    pasta = FILA / ag["id"]
    precisa = (pasta / "reels.mp4") if any(i["tipo"] == "reels" for i in ag["itens"]) else (pasta / "carrossel")
    if precisa.exists():
        return True
    # baixa numa pasta à parte e copia por cima (o gh não sobrescreve os textos da fila que já estão no repositório)
    import shutil, tempfile
    tmp = Path(tempfile.mkdtemp(prefix="art-"))
    r = subprocess.run(["gh", "run", "download", str(ag["run_id"]), "-n", ag["artefato"], "-D", str(tmp)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("não baixei o artefato:", r.stderr[-300:])
        return False
    shutil.copytree(tmp, RAIZ, dirs_exist_ok=True, symlinks=True)
    return True


def ja_saiu(tipo, ag, recentes):
    pasta = FILA / ag["id"]
    if tipo == "carrossel":
        cap = json.loads((pasta / "content.json").read_text(encoding="utf-8")).get("caption", "")
    else:
        cap = (pasta / "legenda.txt").read_text(encoding="utf-8")
    inicio = cap.strip().splitlines()[0][:70]
    for m in recentes:
        if inicio and inicio in (m.get("caption") or ""):
            return m.get("permalink", "sim")
    return None


def publica(tipo, ag):
    pasta = FILA / ag["id"]
    chk = subprocess.run([sys.executable, str(RAIZ / "robo" / "checar_edicao.py"), str(pasta), "--so", tipo],
                         capture_output=True, text=True, cwd=RAIZ)
    if chk.returncode != 0:
        return False, "Travado pelas regras na hora de publicar:\n" + chk.stdout[-1500:], True
    if tipo == "carrossel":
        cmd = [sys.executable, "publica_tudo.py", "carrossel", str(pasta / "carrossel")]
    else:
        cmd = [sys.executable, "publica_tudo.py", "reels", str(pasta / "reels.mp4"), str(pasta / "legenda.txt")]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ, timeout=1800)
    saida = (r.stdout + "\n" + r.stderr)
    saida = re.sub(r"(access_token=)[^&\s\"']+", r"\1***", saida)        # nunca vaza chave no registro
    return r.returncode == 0, saida[-3500:], False


def links(saida):
    return sorted(set(re.findall(r"https://(?:www\.)?(?:instagram\.com|facebook\.com|threads\.(?:net|com))/[^\s\"')]+", saida)))


def main():
    so_id = sys.argv[sys.argv.index("--agora") + 1] if "--agora" in sys.argv else None
    agora_ = agora()
    recentes = None
    for arq in sorted(FILA.glob("*/agenda.json")):
        ag = ler(arq)
        if not ag or (so_id and ag["id"] != so_id):
            continue
        mudou = False
        fora = None
        for it in ag["itens"]:
            if it["estado"] != "pendente":
                continue
            quando = datetime.fromisoformat(it["quando"])
            if not so_id and not (quando - ANTES <= agora_ <= quando + DEPOIS):
                if agora_ > quando + DEPOIS:
                    it["estado"] = "expirado"; mudou = True
                    comentar(ag.get("issue"), f"⌛ {it['tipo'].capitalize()} não foi aprovado a tempo e não foi publicado.")
                continue
            iss = it.get("issue") or ag.get("issue")          # item corrigido tem prévia própria
            fora = cancelamentos(iss)
            if it["tipo"] in fora:
                it["estado"] = "cancelado"; mudou = True
                comentar(ag.get("issue"), f"🚫 {it['tipo'].capitalize()} cancelado, como pedido. Não publiquei.")
                continue
            if it["tipo"] not in aprovacoes(iss):      # regra dele: só sai com aprovação
                print(f"aguardando aprovação: {it['tipo']} de {ag['id']}")
                continue
            if not baixa_artefato(ag):
                it["tentativas"] += 1; mudou = True
                if it["tentativas"] >= 3:
                    it["estado"] = "falhou"
                    alerta(f"Não saiu: {it['tipo']} de {ag['id']}", "Não consegui baixar os arquivos da produção.")
                continue
            recentes = recentes if recentes is not None else legendas_recentes()
            if (link := ja_saiu(it["tipo"], ag, recentes)):          # sempre: nunca publica em dobro
                it["estado"] = "publicado"; it["links"] = [link]; mudou = True
                comentar(ag.get("issue"), f"✅ {it['tipo'].capitalize()} já estava no ar: {link}")
                continue
            ok, saida, travado = publica(it["tipo"], ag)
            it["tentativas"] += 1; mudou = True
            if ok:
                it["estado"] = "publicado"; it["links"] = links(saida)
                it["publicado_em"] = agora().strftime("%Y-%m-%dT%H:%M")
                pend = [l for l in saida.splitlines() if l.startswith(("PENDENTE", "FALHOU"))]
                comentar(ag.get("issue"), f"✅ {it['tipo'].capitalize()} publicado.\n\n" + "\n".join(f"- {l}" for l in it["links"])
                         + ("\n\nFicou de fora:\n" + "\n".join(f"- {p}" for p in pend) if pend else ""))
            elif travado or it["tentativas"] >= 3:
                it["estado"] = "falhou"
                alerta(f"Não saiu: {it['tipo']} de {ag['id']}", f"Prévia #{ag.get('issue')}.\n\n```\n{saida}\n```")
                comentar(ag.get("issue"), f"❌ {it['tipo'].capitalize()} não saiu. Detalhes no alerta.")
            else:
                recentes = legendas_recentes()      # a próxima rodada confere se saiu antes de tentar de novo
                print(f"falhou ({it['tentativas']}ª tentativa), tento de novo na próxima rodada:\n{saida[-1500:]}")
                comentar(iss, f"⚠️ {it['tipo'].capitalize()}: a {it['tentativas']}ª tentativa falhou; tento de novo.\n\n```\n{saida[-1800:]}\n```")
        if mudou:
            gravar(arq, ag)
        if ag["itens"] and all(i["estado"] != "pendente" for i in ag["itens"]) and not ag.get("fechada"):
            fechar(ag.get("issue"))
            ag["fechada"] = True
            gravar(arq, ag)
    return 0


if __name__ == "__main__":
    sys.exit(main())

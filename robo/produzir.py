#!/usr/bin/env python3
"""Produz uma edição (carrossel + Reels) com o Claude Code e abre a PRÉVIA para o José Miguel.

Uso: python3 robo/produzir.py [manha|meio|noite]     (sem argumento: escolhe pela hora de Brasília)
Não publica nada: deixa a edição na fila (fila/<id>/agenda.json) e o robô publicador solta no horário.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import (DIAS, EDICOES, ESTADO, FILA, MESES, RAIZ, abrir_issue, agora, alerta, env_sem_chaves,  # noqa: E402
                   gravar, legendas_recentes, ler)

MODELO = os.environ.get("MODELO", "claude-opus-5-5")
RAPIDO = os.environ.get("MODELO_RAPIDO", "claude-sonnet-5")
TEMPO = int(os.environ.get("TEMPO_PRODUCAO_MIN", "95")) * 60


# 25/09: o agendamento do GitHub atrasa horas ou nem dispara. O fluxo agora roda a cada 15 min e só produz a
# edição cuja JANELA está aberta e que ainda não foi feita (idempotente).
JANELAS = {"manha": (4.5, 8.5), "meio": (9.5, 12.5), "noite": (15.5, 19.0)}


def escolhe_edicao():
    t = agora().hour + agora().minute / 60
    for ed, (a, b) in JANELAS.items():
        if a <= t < b:
            return ed
    return None


def rodar_claude(prompt, log):
    cmd = ["claude", "-p", "--model", MODELO, "--fallback-model", RAPIDO, "--dangerously-skip-permissions",
           "--max-turns", "500", "--output-format", "json"]
    ini = time.time()
    try:
        p = subprocess.run(cmd, input=prompt, text=True, capture_output=True, cwd=RAIZ, env=env_sem_chaves(),
                           timeout=TEMPO)
        saida, codigo = p.stdout, p.returncode
        log.write_text((p.stdout or "")[-20000:] + "\n--- stderr ---\n" + (p.stderr or "")[-5000:], encoding="utf-8")
    except subprocess.TimeoutExpired as e:
        saida, codigo = (e.stdout or b"").decode("utf-8", "ignore") if isinstance(e.stdout, bytes) else (e.stdout or ""), -9
        log.write_text("TEMPO ESGOTADO\n" + saida[-20000:], encoding="utf-8")
    try:
        j = json.loads(saida)
    except Exception:
        j = {}
    return codigo, j, int(time.time() - ini)


def miniatura(origem, destino, largura=1100):
    from PIL import Image
    im = Image.open(origem).convert("RGB")
    if im.width > largura:
        im = im.resize((largura, int(im.height * largura / im.width)))
    im.save(destino, "JPEG", quality=80)


def sobe_previa(ident, arquivos):
    """Hospeda as artes da prévia no pisca-midia (público, release "previas") para aparecerem inteiras na issue e no
    e-mail. Devolve {nome: url}. Sem MIDIA_TOKEN, devolve {} (a prévia fica só com as miniaturas)."""
    import requests
    tok, repo = os.environ.get("MIDIA_TOKEN"), os.environ.get("MIDIA_REPO", "jmiguevf/pisca-midia")
    if not tok:
        return {}
    H = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    r = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/previas", headers=H, timeout=60)
    if r.status_code == 404:
        r = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=H, timeout=60,
                          json={"tag_name": "previas", "name": "Prévias do Pisca", "body": "Artes para aprovação."})
    rel = r.json()
    urls = {}
    for arq in arquivos:
        arq = Path(arq)
        if not arq.exists():
            continue
        nome = f"{ident}-{arq.parent.name}-{arq.name}" if arq.parent.name == "carrossel" else f"{ident}-{arq.name}"
        tipo = "video/mp4" if arq.suffix == ".mp4" else "image/jpeg"
        try:
            up = requests.post(f"https://uploads.github.com/repos/{repo}/releases/{rel['id']}/assets",
                               params={"name": nome}, headers={**H, "Content-Type": tipo}, data=arq.read_bytes(),
                               timeout=600)
            if up.ok:
                urls[arq.name] = up.json()["browser_download_url"]
        except Exception as e:
            print("prévia: não subiu", arq.name, str(e)[:120])
    return urls


def main():
    ed = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in EDICOES else escolhe_edicao()
    cid = os.environ.get("CORRIGIR_ID", "").strip()
    if os.environ.get("CORRIGIR", "").strip() and cid:     # correção: a edição vem do id, a qualquer hora
        ed = next((e for e in EDICOES if f"-{e}" in cid), ed)
    if not ed:
        print("fora da janela de produção; nada a fazer")
        return 0
    E = EDICOES[ed]
    hoje = agora()
    ident = f"{hoje:%Y-%m-%d}-{ed}" + (f"-{os.environ['REFAZER']}" if os.environ.get("REFAZER") else "")
    corrigir, corr_tipo = os.environ.get("CORRIGIR", "").strip(), os.environ.get("CORRIGIR_TIPO", "carrossel")
    if corrigir:
        ident = os.environ["CORRIGIR_ID"]
    pasta = FILA / ident
    ag = ler(pasta / "agenda.json")
    ag_velha = ag if corrigir else None
    if ag and ag.get("itens") and not corrigir:
        print("edição já produzida:", ident)
        return 0
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") and not os.environ.get("ANTHROPIC_API_KEY"):
        alerta("Falta o código do Claude no GitHub",
               "O robô não consegue produzir sem o secret `CLAUDE_CODE_OAUTH_TOKEN`.\n\nNo seu PC, rode "
               "`claude setup-token`, copie o código e grave em Settings → Secrets and variables → Actions → "
               "New repository secret, com o nome `CLAUDE_CODE_OAUTH_TOKEN`.")
        return 1

    data_br = f"{DIAS[hoje.weekday()]}, {hoje:%d/%m}"
    # a edição já saiu (pedido feito à mão, antes do horário)? então não produz de novo
    recentes = legendas_recentes()
    marca = f"{E['piscada']} ({data_br})"
    if not corrigir and any(marca in (m.get("caption") or "") for m in recentes):
        print("já publicada à mão:", marca)
        return 0
    ESTADO.mkdir(exist_ok=True)
    (ESTADO / "recentes.txt").write_text("\n\n=====\n\n".join(
        f"[{m.get('timestamp','')[:16]}] {m.get('media_product_type','')}\n{(m.get('caption') or '')[:900]}"
        for m in recentes), encoding="utf-8")

    pasta.mkdir(parents=True, exist_ok=True)
    date_label = f"{DIAS[hoje.weekday()].upper()} · {hoje:%d} {MESES[hoje.month - 1]}"
    prompt = (RAIZ / "robo" / "edicao.md").read_text(encoding="utf-8") + f"""

## Variáveis desta execução
EDICAO={ed} ({E['nome']})
DATA_BR={data_br}
DATE_LABEL={date_label}
PASTA=fila/{ident}
Hora agora (Brasília): {hoje:%H:%M}. O Reels sai às {E['reels']} e o carrossel às {E['carrossel']}.
"""
    pauta = RAIZ / "pautas" / f"{hoje:%Y-%m-%d}-{ed}.md"
    if pauta.exists() and not corrigir:      # pauta pedida pelo José Miguel para esta edição
        prompt += "\n\n## PAUTA DO JOSÉ MIGUEL PARA ESTA EDIÇÃO (tem prioridade sobre a escolha do Reels)\n" + pauta.read_text(encoding="utf-8")
    if corrigir:
        prompt += f"""
## ESTA EXECUÇÃO É UMA CORREÇÃO (pedido do José Miguel / revisão)
A edição JÁ ESTÁ PRONTA em fila/{ident} (content.json, carrossel/, materia.json, reels.mp4, legenda.txt, resumo.json).
NÃO refaça a edição. Faça SOMENTE esta correção no {corr_tipo}:

{corrigir}

Depois re-renderize só o que mudou, abra a folha (Read) e confira, rode `python3 robo/checar_edicao.py fila/{ident} --so {corr_tipo}`
até passar, e acrescente em resumo.json "observacoes" uma linha dizendo o que foi corrigido.
"""
    codigo, j, seg = rodar_claude(prompt, pasta / "agente.log")
    print(f"agente terminou: código {codigo}, {seg // 60} min, custo de referência US$ {j.get('total_cost_usd', 0):.2f}")
    if codigo != 0 and not (pasta / "content.json").exists():
        erro = (j.get("result") or "")[:600] or (pasta / "agente.log").read_text(encoding="utf-8")[-800:]
        limite = any(x in erro.lower() for x in ("usage limit", "rate limit", "limite de uso"))
        alerta("Produção parada: " + ("limite de uso do plano do Claude" if limite else "problema no agente"),
               f"Edição {ident} não foi produzida.\n\n```\n{erro}\n```")
        return 1

    # confere cada parte do jeito que o publicador vai conferir
    itens, problemas = [], {}
    for tipo in ((corr_tipo,) if corrigir else ("reels", "carrossel")):
        r = subprocess.run([sys.executable, str(RAIZ / "robo" / "checar_edicao.py"), str(pasta), "--so", tipo],
                           capture_output=True, text=True, cwd=RAIZ)
        if r.returncode == 0:
            itens.append({"tipo": tipo, "quando": f"{hoje:%Y-%m-%d}T{E[tipo]}", "estado": "pendente", "tentativas": 0})
        else:
            problemas[tipo] = [l[10:] for l in r.stdout.splitlines() if l.startswith("PROBLEMA:")] or [r.stdout[-400:]]

    resumo = ler(pasta / "resumo.json", {}) or {}
    # miniaturas para a prévia (vão para o repositório; o resto vai como artefato)
    for origem, nome in ((pasta / "carrossel" / "preview.jpg", "previa_carrossel.jpg"),
                         (pasta / "reels_folha.jpg", "previa_reels.jpg")):
        if origem.exists():
            miniatura(origem, pasta / nome)

    repo, sha = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_SHA", "main")
    slides = sorted((pasta / "carrossel").glob("slide_*.jpg"))
    artes = sobe_previa(ident, slides + [pasta / "carrossel" / "story.jpg", pasta / "reels.mp4", pasta / "previa_reels.jpg"])
    img = lambda n: f"https://github.com/{repo}/blob/main/fila/{ident}/{n}?raw=true"  # noqa: E731
    linhas = [f"## {E['nome'].capitalize()} de {hoje:%d/%m}", ""]
    if any(i["tipo"] == "reels" for i in itens):
        leg = (pasta / "legenda.txt").read_text(encoding="utf-8")
        linhas += [f"### 🎬 Reels — sai às **{E['reels']}**", f"**{resumo.get('reels', '')}**", "",
                   f"![Reels]({artes.get('previa_reels.jpg') or img('previa_reels.jpg')})", ""]
        if artes.get("reels.mp4"):
            linhas += [f"▶️ **[Assistir o Reels inteiro]({artes['reels.mp4']})**", ""]
        linhas += ["**Legenda:**", "", leg, ""]
    if any(i["tipo"] == "carrossel" for i in itens):
        cap = json.loads((pasta / "content.json").read_text(encoding="utf-8")).get("caption", "")
        linhas += [f"### 🗞️ Carrossel — sai às **{E['carrossel']}**", "",
                   f"![Carrossel]({img('previa_carrossel.jpg')})", ""]
        for sl in slides:                                   # cada arte inteira, na ordem em que sai
            if artes.get(sl.name):
                linhas += [f"![{sl.stem}]({artes[sl.name]})", ""]
        if artes.get("story.jpg"):
            linhas += ["Story:", "", f"![story]({artes['story.jpg']})", ""]
        linhas += ["**Legenda:**", "", cap, ""]
    for tipo, erros in problemas.items():
        linhas += [f"### ⚠️ {tipo.capitalize()} NÃO vai sair (não passou nas travas)", ""] + [f"- {e}" for e in erros] + [""]
    if resumo.get("observacoes"):
        linhas += ["### Observação do editor", resumo["observacoes"], ""]
    linhas += ["---", "**Só publico com a sua aprovação.** Comente aqui:",
               "- `aprovar` → sai tudo no horário (se já passou do horário, sai na hora)",
               "- `aprovar reels` ou `aprovar carrossel` → sai só aquele",
               "- `cancelar reels`, `cancelar carrossel` ou `cancelar tudo` → não sai",
               "", "Reels: Instagram (reel + story), Facebook (reel + story), Threads e YouTube Shorts. Carrossel: Instagram (post + story), Facebook (post + story) e Threads. Sem aprovação, não sai."]
    if corrigir:
        linhas.insert(0, f"**Correção:** {corrigir}\n")
    titulo = ("Correção — " if corrigir else "") + f"Prévia: {E['nome']} de {hoje:%d/%m} (" + ", ".join(
        f"{i['tipo']} {E[i['tipo']]}" for i in itens) + ")" if itens else f"Edição {E['nome']} de {hoje:%d/%m} sem post"
    numero = abrir_issue(titulo, "\n".join(linhas), "previa" if itens else "alerta")

    art = f"edicao-{ident}" + (f"-c{os.environ.get('GITHUB_RUN_ID', '')}" if corrigir else "")
    if corrigir and ag_velha:
        # mantém os outros itens como estavam (e a prévia antiga deles); o corrigido passa a valer pela prévia nova
        velhos = [dict(i, issue=i.get("issue", ag_velha.get("issue"))) for i in ag_velha["itens"] if i["tipo"] != corr_tipo]
        for i in itens:
            i["issue"] = numero
        antigo = [i for i in ag_velha["itens"] if i["tipo"] == corr_tipo]
        if antigo and antigo[0].get("estado") in ("publicado",):
            print("o item já tinha sido publicado; a correção fica só registrada")
        itens = velhos + itens
        from comum import comentar
        comentar(ag_velha.get("issue"), f"✏️ O {corr_tipo} foi corrigido: veja e aprove na prévia nova #{numero}. "
                                         f"A aprovação do {corr_tipo} daqui não vale mais.")
    gravar(pasta / "agenda.json", {"id": ident, "edicao": ed, "issue": (ag_velha or {}).get("issue", numero),
                                   "run_id": os.environ.get("GITHUB_RUN_ID"), "artefato": art, "itens": itens,
                                   "problemas": problemas, "minutos_agente": seg // 60,
                                   "custo_referencia_usd": j.get("total_cost_usd")})
    # lista do que vai no artefato (a edição inteira + as fotos que ela usa)
    import foto_repete as FR
    fotos = set()
    for arq in ("content.json", "materia.json"):
        if (pasta / arq).exists():
            fotos |= {str(p.relative_to(RAIZ)) for p in FR.fotos(pasta / arq)}
    (RAIZ / "artefato_nome.txt").write_text(art, encoding="utf-8")
    (RAIZ / "artefato.txt").write_text("\n".join([f"fila/{ident}"] + sorted(fotos)), encoding="utf-8")
    print("prévia aberta:", numero, "| itens:", [i["tipo"] for i in itens], "| problemas:", list(problemas))
    return 0 if itens else 1


if __name__ == "__main__":
    sys.exit(main())

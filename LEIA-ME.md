# Pisca News — robô no GitHub

Mantém o **@pisca.news** (Instagram), a Página **Pisca** (Facebook) e o **Threads** com **3 carrosséis e 3 Reels por dia**,
pelas APIs oficiais da Meta. Um agente (Claude Code, pelo plano do Claude do José Miguel) apura e faz a arte; um robô
publica no horário, depois da prévia.

## O dia

| Edição | Produção | Prévia chega | Reels | Carrossel |
|---|---|---|---|---|
| Manhã | 5h | ~6h30 | 7h | 8h |
| Meio-dia | 10h | ~11h30 | 12h | 13h |
| Noite | 16h30 | ~18h | 18h30 | 19h30 |

Cada Reels vai para Instagram (com convite de collab), Facebook e story nos dois; cada carrossel vai para Instagram,
Facebook e story nos dois; os dois vão também para o Threads (o vídeo, hospedado no **pisca-midia**, que é público).

## A prévia (chega por e-mail, como issue) — SÓ PUBLICA COM APROVAÇÃO

Mostra a folha do carrossel, os cartões do Reels e as legendas. Comente na prévia:

- `aprovar` → sai tudo no horário (aprovou depois do horário? sai na hora, até 6 h depois)
- `aprovar reels` · `aprovar carrossel` → sai só aquele
- `cancelar reels` · `cancelar carrossel` · `cancelar tudo` → não sai

Sem aprovação, não sai nada.

## As travas (as mesmas de sempre, conferidas na produção e de novo antes de publicar)

Notícia repetida, foto repetida em 30 dias (pela imagem), Reels igual ao carrossel, legenda (tamanho, hashtags, isca,
linha da Anthropic), vídeo fora do padrão (1080x1920, 30 qps, som, sem borda). As regras que o agente segue estão em
`BOAS_PRATICAS.md` e `robo/edicao.md`.

## Ligar, desligar, rodar à mão (aba Actions)

- **Desligar o automático:** Settings → Secrets and variables → Actions → Variables → `PISCA_LIGADO` = `0` (volta com `1`). Desligado, só roda o que for disparado à mão.
- **Produzir edição** → "Run workflow" (pode escolher manha, meio ou noite).
- **Publicar (robô)** → "Run workflow" publica o que venceu; com o id (ex.: `2026-09-25-manha`) publica já.
- **Verificar ligações** → confere Claude, Instagram, Página, Threads e pisca-midia (roda sozinho toda segunda).

## Chaves (Settings → Secrets and variables → Actions)

Secrets: `CLAUDE_CODE_OAUTH_TOKEN` (no PC: `claude setup-token`; vale 1 ano), `META_PAGE_TOKEN`, `THREADS_TOKEN`
(vale 60 dias: renovar antes de ~23/11/2026), `MIDIA_TOKEN` (acesso ao pisca-midia).
Variables: `IG_USER_ID`, `FB_PAGE_ID`, `THREADS_USER_ID`, `COLLAB`, `PISCA_LIGADO`.

## Custo

Meta e Threads: sem custo. Claude: pelo plano do José Miguel (entra no mesmo limite de uso do dia a dia).
GitHub: o plano gratuito dá 2.000 minutos por mês em repositório privado; cada edição usa ~60–90 min, então o mês
passa disso. Quando os minutos acabam, o GitHub para os fluxos (não cobra sem autorização). Repositório público não
tem limite de minutos.

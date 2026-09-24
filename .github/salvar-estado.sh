#!/usr/bin/env bash
# Grava no repositório a fila, as prévias e os registros (notícias e fotos publicadas), com nova tentativa
# se outro fluxo gravou antes. Fotos, vídeos e slides NÃO entram (vão como artefato da produção).
set -u
git config user.name "Robô Pisca"
git config user.email "robo-pisca@users.noreply.github.com"
git add -A fila estado publicadas.json fotos_usadas.json comentarios_vistos.json 2>/dev/null
if git diff --cached --quiet; then echo "Nada a salvar."; exit 0; fi
git commit -q -m "$1 $(date -u +%Y-%m-%dT%H:%MZ)"
for i in 1 2 3 4 5; do
  git pull -q --rebase -X theirs && git push -q && exit 0
  sleep $((i * 7))
done
echo "Não consegui salvar o estado." >&2
exit 1

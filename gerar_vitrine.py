"""
Gera a vitrine estática (index.html) com as ofertas aprovadas mais recentes
e publica no GitHub Pages via git push automático.

Lê o promod.db em modo somente-leitura (não interfere no bot rodando).
"""

import html
import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# --- Configuração ---
DB_PATH = os.path.expanduser("~/projetos/alertapromod/promod.db")
REPO_DIR = Path(__file__).resolve().parent  # pasta onde este script está
QTD_OFERTAS = 10


def buscar_ofertas():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT titulo, link_afiliado, preco, preco_original, desconto,
               loja, foto, cupom
        FROM ofertas
        WHERE status = 'aprovada'
        ORDER BY criado_em DESC
        LIMIT ?
        """,
        (QTD_OFERTAS,),
    )
    ofertas = [dict(row) for row in cur.fetchall()]
    conn.close()
    return ofertas


def fmt_preco(valor):
    if not valor:
        valor = 0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_card(oferta):
    titulo = html.escape(oferta["titulo"] or "")
    loja = html.escape(oferta["loja"] or "")
    link = html.escape(oferta["link_afiliado"] or "#")
    foto = oferta["foto"] or ""
    preco = oferta["preco"] or 0
    preco_original = oferta["preco_original"] or 0
    desconto = oferta["desconto"] or 0
    cupom = oferta["cupom"] or ""

    tag_html = ""
    if desconto and desconto > 0:
        tag_html = f'<span class="tag">-{int(desconto)}%</span>'

    original_html = ""
    if preco_original and preco_original > preco:
        original_html = f'<span class="preco-original">{fmt_preco(preco_original)}</span>'

    cupom_html = ""
    if cupom:
        cupom_html = f'<p class="cupom">{html.escape(cupom)}</p>'

    if foto:
        img_html = f'<img src="{html.escape(foto)}" alt="{titulo}" loading="lazy" width="96" height="96">'
    else:
        img_html = '<div class="foto-vazia" aria-hidden="true"></div>'

    return f"""
    <a class="oferta" href="{link}" target="_blank" rel="nofollow sponsored noopener">
      <div class="foto-wrap">
        {img_html}
        {tag_html}
      </div>
      <div class="info">
        <p class="loja">{loja}</p>
        <p class="titulo">{titulo}</p>
        <p class="precos">
          <span class="preco">{fmt_preco(preco)}</span>
          {original_html}
        </p>
        {cupom_html}
      </div>
    </a>"""


def montar_html(ofertas):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    cards = "\n".join(montar_card(o) for o in ofertas)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alerta PromoD — ofertas aprovadas agora</title>
<meta name="description" content="Feed de ofertas aprovadas pelo Alerta PromoD na Amazon, Mercado Livre e Shopee, atualizado automaticamente.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #14161f;
  --linha: #262938;
  --texto: #f1eee3;
  --texto-fraco: #9298ab;
  --acento: #ff7a3d;
  --sucesso: #7dd8a4;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  background: var(--bg);
  color: var(--texto);
  font-family: 'IBM Plex Sans', sans-serif;
  -webkit-font-smoothing: antialiased;
}}
.topo {{
  max-width: 640px;
  margin: 0 auto;
  padding: 2.5rem 1.25rem 1.5rem;
}}
.marca {{
  font-weight: 600;
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: var(--texto-fraco);
}}
.tagline {{
  font-family: 'Fraunces', serif;
  font-style: italic;
  font-weight: 500;
  font-size: 1.6rem;
  line-height: 1.25;
  margin: 0 0 1rem;
  max-width: 26ch;
}}
.status {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--texto-fraco);
  font-size: 0.85rem;
  margin: 0;
}}
.ponto {{
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--sucesso);
  animation: pulsar 2.4s ease-in-out infinite;
}}
@media (prefers-reduced-motion: reduce) {{ .ponto {{ animation: none; }} }}
@keyframes pulsar {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
.feed {{
  max-width: 640px;
  margin: 0 auto;
  padding: 0 1.25rem 3rem;
}}
.oferta {{
  display: flex;
  gap: 1rem;
  padding: 1.1rem 0;
  border-top: 1px solid var(--linha);
  text-decoration: none;
  color: inherit;
}}
.oferta:focus-visible {{
  outline: 2px solid var(--acento);
  outline-offset: 4px;
}}
.foto-wrap {{
  position: relative;
  flex: none;
  width: 92px; height: 92px;
}}
.foto-wrap img, .foto-vazia {{
  width: 100%; height: 100%;
  object-fit: cover;
  border-radius: 6px;
  display: block;
  background: #1c1f2b;
}}
.tag {{
  position: absolute;
  left: -6px; bottom: -6px;
  background: var(--acento);
  color: #191a1f;
  font-weight: 600;
  font-size: 0.7rem;
  padding: 2px 7px 2px 10px;
  clip-path: polygon(12% 0, 100% 0, 100% 100%, 12% 100%, 0 50%);
}}
.info {{ min-width: 0; flex: 1; }}
.loja {{
  margin: 0 0 0.15rem;
  font-size: 0.72rem;
  color: var(--texto-fraco);
}}
.titulo {{
  margin: 0 0 0.4rem;
  font-size: 0.92rem;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.precos {{
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin: 0;
}}
.preco {{
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: 1.35rem;
  color: var(--acento);
}}
.preco-original {{
  font-size: 0.8rem;
  color: var(--texto-fraco);
  text-decoration: line-through;
}}
.cupom {{
  margin: 0.3rem 0 0;
  font-size: 0.75rem;
  color: var(--sucesso);
}}
.rodape {{
  max-width: 640px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
  color: var(--texto-fraco);
  font-size: 0.75rem;
  border-top: 1px solid var(--linha);
}}
@media (min-width: 520px) {{
  .foto-wrap {{ width: 108px; height: 108px; }}
  .tagline {{ font-size: 1.8rem; }}
}}
</style>
</head>
<body>
<header class="topo">
  <p class="marca">alerta promod</p>
  <h1 class="tagline">As promoções que valem a pena, sem precisar procurar.</h1>
  <p class="status"><span class="ponto" aria-hidden="true"></span>atualiza automaticamente a cada 15 minutos</p>
</header>

<main class="feed">
{cards}
</main>

<footer class="rodape">
  <p>Gerado automaticamente pelo Alerta PromoD · última atualização em {agora}</p>
</footer>
</body>
</html>
"""


def publicar_no_git():
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
    resultado = subprocess.run(
        ["git", "commit", "-m", f"Atualiza vitrine - {datetime.now().strftime('%d/%m/%Y %H:%M')}"],
        cwd=REPO_DIR,
    )
    if resultado.returncode != 0:
        print("Nada novo para publicar (sem mudanças desde a última execução).")
        return
    subprocess.run(["git", "push"], cwd=REPO_DIR, check=True)
    print("Vitrine publicada com sucesso.")


def main():
    ofertas = buscar_ofertas()
    if not ofertas:
        print("Nenhuma oferta aprovada encontrada — abortando pra não publicar página vazia.")
        return
    html_final = montar_html(ofertas)
    (REPO_DIR / "index.html").write_text(html_final, encoding="utf-8")
    print(f"{len(ofertas)} ofertas escritas em index.html.")
    publicar_no_git()


if __name__ == "__main__":
    main()

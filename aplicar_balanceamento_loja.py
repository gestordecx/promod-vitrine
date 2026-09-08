import ast
import shutil
from datetime import datetime
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "gerar_vitrine.py"

old_str = '''def buscar_ofertas():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT titulo, link_afiliado, preco, preco_original, desconto,
               loja, foto, cupom, frete_gratis, avaliacao, num_avaliacoes
        FROM ofertas
        WHERE status = 'aprovada'
        ORDER BY criado_em DESC
        LIMIT ?
        """,
        (QTD_OFERTAS,),
    )
    ofertas = [dict(row) for row in cur.fetchall()]
    conn.close()
    return ofertas'''

new_str = '''LOJAS = ["Amazon", "Mercado Livre", "Shopee"]
QTD_POR_LOJA = 4  # 4+4+4 = 12 -- distribuicao igual entre as 3 lojas (decisao 08/09/2026,
                  # evita que uma loja com mais volume de aprovacao (ex: Shopee) domine a vitrine)

_COLUNAS_OFERTA = """id, titulo, link_afiliado, preco, preco_original, desconto,
               loja, foto, cupom, frete_gratis, avaliacao, num_avaliacoes, criado_em"""


def buscar_ofertas():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    ofertas = []
    ids_usados = set()

    for loja in LOJAS:
        cur.execute(
            f"""
            SELECT {_COLUNAS_OFERTA}
            FROM ofertas
            WHERE status = 'aprovada' AND loja = ?
            ORDER BY criado_em DESC
            LIMIT ?
            """,
            (loja, QTD_POR_LOJA),
        )
        for row in cur.fetchall():
            ofertas.append(dict(row))
            ids_usados.add(row["id"])

    # Completa com as aprovadas mais recentes de qualquer loja, caso alguma
    # loja nao tenha QTD_POR_LOJA disponiveis -- garante QTD_OFERTAS cards
    # mesmo com desbalanco real de volume entre lojas.
    faltam = QTD_OFERTAS - len(ofertas)
    if faltam > 0:
        if ids_usados:
            placeholders = ",".join("?" * len(ids_usados))
            filtro_excluir = f"AND id NOT IN ({placeholders})"
            parametros = (*ids_usados, faltam)
        else:
            filtro_excluir = ""
            parametros = (faltam,)
        cur.execute(
            f"""
            SELECT {_COLUNAS_OFERTA}
            FROM ofertas
            WHERE status = 'aprovada' {filtro_excluir}
            ORDER BY criado_em DESC
            LIMIT ?
            """,
            parametros,
        )
        ofertas.extend(dict(row) for row in cur.fetchall())

    # Reordena por data (mais recente primeiro) pra nao ficar em blocos
    # "todas Amazon, depois todas ML, depois todas Shopee" na vitrine.
    ofertas.sort(key=lambda o: o["criado_em"], reverse=True)

    conn.close()
    return ofertas'''

texto = ARQUIVO.read_text(encoding="utf-8")
assert old_str in texto, "old_str nao encontrado -- arquivo pode ter mudado desde a analise"
assert texto.count(old_str) == 1, "old_str aparece mais de uma vez -- edicao ambigua"

backup = ARQUIVO.with_name(f"gerar_vitrine.py.bkp_antes_balanceamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy(ARQUIVO, backup)
print(f"Backup criado em: {backup}")

novo_texto = texto.replace(old_str, new_str)
ast.parse(novo_texto)  # valida sintaxe antes de gravar
ARQUIVO.write_text(novo_texto, encoding="utf-8")
print("gerar_vitrine.py atualizado e sintaxe validada com ast.parse.")

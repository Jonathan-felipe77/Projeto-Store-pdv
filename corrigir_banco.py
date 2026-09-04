import sqlite3
from pathlib import Path

print("=" * 60)
print("CORRIGINDO BANCO DE DADOS")
print("=" * 60)

bancos = list(Path(".").rglob("banco.db"))

if not bancos:
    print("ERRO: nenhum arquivo banco.db foi encontrado.")
    input("\nPressione ENTER para sair...")
    raise SystemExit

corrigido = False

for caminho in bancos:

    print(f"\nVerificando: {caminho.resolve()}")

    try:
        conn = sqlite3.connect(str(caminho))

        tabela = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'clientes'
        """).fetchone()

        if tabela is None:
            print("  -> Não possui tabela clientes. Ignorando.")
            conn.close()
            continue

        colunas = conn.execute(
            "PRAGMA table_info(clientes)"
        ).fetchall()

        nomes = [coluna[1] for coluna in colunas]

        print("  -> Colunas encontradas:", nomes)

        if "desconto_percentual" in nomes:

            print("  -> A coluna já existe.")
            corrigido = True

        else:

            print("  -> Criando desconto_percentual...")

            conn.execute("""
                ALTER TABLE clientes
                ADD COLUMN desconto_percentual
                REAL NOT NULL DEFAULT 0
            """)

            conn.commit()

            print("  -> OK! Coluna criada com sucesso.")
            corrigido = True

        conn.close()

    except Exception as erro:

        print(f"  -> ERRO: {erro}")


print("\n" + "=" * 60)

if corrigido:
    print("BANCO CORRIGIDO!")
else:
    print("NENHUM BANCO COM TABELA CLIENTES FOI ENCONTRADO.")

print("=" * 60)

input("\nPressione ENTER para fechar...")
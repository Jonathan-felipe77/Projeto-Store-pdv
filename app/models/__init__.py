from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.movimentacao import Movimentacao
from app.models.produto import Produto
from app.models.usuarios import Usuario
from app.models.venda import Venda, ItemVenda
from app.models.pagamento import Pagamento
# Gerar a migration

# python -m alembic revision --autogenerate -m "Criar tabela cliente."

# aplicar a migration
# python -m alembic upgrade head
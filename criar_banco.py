from app.database import Base, engine

# Importa todos os models
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.movimentacao import Movimentacao
from app.models.produto import Produto
from app.models.usuarios import Usuario
from app.models.venda import Venda, ItemVenda
from app.models.pagamento import Pagamento


print("Verificando banco de dados...")

Base.metadata.create_all(bind=engine)

print("Banco de dados atualizado com sucesso!")
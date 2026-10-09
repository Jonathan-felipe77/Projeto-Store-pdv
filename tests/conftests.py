"""Fixtures compartilhadas para os testes de regressão do PDV."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_admin, get_usuario_logado, get_usuario_opcional, hash_senha
from app.database import Base, get_db
from app.main import app

# Importar todos os modelos antes de criar as tabelas do banco de teste.
from app.models.categoria import Categoria  # noqa: F401
from app.models.cliente import Cliente  # noqa: F401
from app.models.movimentacao import Movimentacao  # noqa: F401
from app.models.pagamento import Pagamento  # noqa: F401
from app.models.produto import Produto  # noqa: F401
from app.models.usuarios import Usuario
from app.models.venda import ItemVenda, Venda  # noqa: F401

ADMIN_TESTE = {
    "id": 1,
    "sub": "admin@teste.local",
    "nome": "Administrador de teste",
    "role": "admin",
}
OPERADOR_TESTE = {
    "id": 2,
    "sub": "operador@teste.local",
    "nome": "Operador de teste",
    "role": "operador",
}


@pytest.fixture()
def db_session_test():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = TestingSessionLocal()

    session.add_all([
        Usuario(
            id=1,
            nome="Administrador de teste",
            email="admin@teste.local",
            senha_hash=hash_senha("SenhaTeste123!"),
            role="admin",
            ativo=True,
        ),
        Usuario(
            id=2,
            nome="Operador de teste",
            email="operador@teste.local",
            senha_hash=hash_senha("SenhaTeste123!"),
            role="operador",
            ativo=True,
        ),
    ])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session_test):
    def override_get_db():
        yield db_session_test

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_usuario_logado] = lambda: ADMIN_TESTE
    app.dependency_overrides[get_usuario_opcional] = lambda: ADMIN_TESTE
    app.dependency_overrides[get_admin] = lambda: ADMIN_TESTE

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def produto_teste(db_session_test):
    from app.models.produto import Produto

    produto = Produto(
        nome="Camisa de teste",
        preco=100.00,
        estoque_atual=20,
        ativo=True,
    )
    db_session_test.add(produto)
    db_session_test.commit()
    db_session_test.refresh(produto)
    return produto


@pytest.fixture()
def cliente_teste(db_session_test):
    cliente = Cliente(
        nome="Cliente de teste",
        matricula="TESTE-001",
        telefone="11999990000",
        is_associado=True,
        ativo=True,
        desconto_percentual=5.0,
    )
    db_session_test.add(cliente)
    db_session_test.commit()
    db_session_test.refresh(cliente)
    return cliente


@pytest.fixture()
def dados_teste(db_session_test):
    """Cadastra dados mínimos para testar listagens e comprovante."""
    from app.models.movimentacao import Movimentacao, TipoMovimentacao

    categoria = Categoria(nome="Uniformes", ativo=True)
    cliente = Cliente(
        nome="Ana Teste",
        matricula="ANA-001",
        telefone="11988887777",
        is_associado=True,
        ativo=True,
        desconto_percentual=5.0,
    )
    db_session_test.add_all([categoria, cliente])
    db_session_test.flush()

    produto = Produto(
        nome="Camisa Polo Teste",
        preco=100.0,
        estoque_atual=10,
        ativo=True,
        categoria_id=categoria.id,
    )
    db_session_test.add(produto)
    db_session_test.flush()

    movimento = Movimentacao(
        tipo=TipoMovimentacao.ENTRADA,
        quantidade=10,
        preco_unitario=100.0,
        observacao="Carga inicial de teste",
        produto_id=produto.id,
        usuario_id=1,
    )
    venda = Venda(
        cliente_id=cliente.id,
        usuario_id=1,
        desconto_percentual=10.0,
        total_bruto=100.0,
        total_liquido=90.0,
        observacao="Venda de teste",
    )
    db_session_test.add_all([movimento, venda])
    db_session_test.flush()
    db_session_test.add_all([
        ItemVenda(
            venda_id=venda.id,
            produto_id=produto.id,
            produto_nome=produto.nome,
            quantidade=1,
            preco_unitario=100.0,
        ),
        Pagamento(
            venda_id=venda.id,
            forma_pagamento="pix",
            valor=90.0,
        ),
    ])
    db_session_test.commit()
    db_session_test.refresh(produto)
    db_session_test.refresh(cliente)
    db_session_test.refresh(categoria)
    db_session_test.refresh(movimento)
    db_session_test.refresh(venda)

    return {
        "categoria": categoria,
        "cliente": cliente,
        "produto": produto,
        "movimentacao": movimento,
        "venda": venda,
    }

"""Parte 2 dos testes da Sprint 3: produtos, estoque/movimentações e rotas do PDV."""

from app.models.produto import Produto


def test_listagem_de_produtos(client, dados_teste):
    response = client.get("/produtos/")
    assert response.status_code == 200
    assert "Camisa Polo Teste" in response.text


def test_busca_de_produto_sem_resultado_nao_quebra_rota(client):
    response = client.get("/produtos/", params={"busca": "produto-que-nao-existe"})
    assert response.status_code == 200
    assert "produto-que-nao-existe" in response.text


def test_checkout_responde(client):
    response = client.get("/produtos/checkout")
    assert response.status_code == 200


def test_detalhe_de_produto_inexistente_redireciona(client):
    response = client.get("/produtos/99999", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"].startswith("/produtos")


def test_tela_de_nova_movimentacao(client, dados_teste):
    response = client.get("/movimentacoes/nova")
    assert response.status_code == 200
    assert "Camisa Polo Teste" in response.text


def test_historico_de_movimentacoes_com_filtro(client, dados_teste):
    response = client.get(
        "/movimentacoes/",
        params={"produto_id": dados_teste["produto"].id, "tipo": "entrada"},
    )
    assert response.status_code == 200


def test_movimentacao_rejeita_quantidade_zero(client, dados_teste):
    response = client.post(
        "/movimentacoes/nova",
        data={
            "produto_id": str(dados_teste["produto"].id),
            "tipo": "entrada",
            "quantidade": "0",
            "preco_unitario": "10.00",
            "observacao": "Teste inválido",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "quantidade" in response.text.lower()


def test_pagina_inicial_responde(client):
    response = client.get("/")
    assert response.status_code == 200


def test_rota_inexistente_retorna_404(client):
    response = client.get("/rota-que-nao-existe", follow_redirects=False)
    assert response.status_code == 404


def test_produto_de_teste_e_ativo(db_session_test, produto_teste):
    produto = db_session_test.query(Produto).filter_by(id=produto_teste.id).one()
    assert produto.ativo is True

"""Testes de regressão da Sprint 3: pagamentos, descontos e vendas."""

import json

from app.models.pagamento import Pagamento
from app.models.produto import Produto
from app.models.venda import Venda


def enviar_venda(
    client,
    produto_id,
    *,
    quantidade=1,
    forma1="dinheiro",
    valor1="100.00",
    forma2="",
    valor2="0.00",
    desconto_tipo="percentual",
    desconto_valor="0",
):
    return client.post(
        "/pdv/finalizar",
        data={
            "carrinho_json": json.dumps([
                {"id": produto_id, "quantidade": quantidade}
            ]),
            "cliente_id": "0",
            "observacao": "Teste Sprint 3",
            "forma_pagamento_1": forma1,
            "valor_pagamento_1": valor1,
            "forma_pagamento_2": forma2,
            "valor_pagamento_2": valor2,
            "desconto_manual_tipo": desconto_tipo,
            "desconto_manual_valor": desconto_valor,
        },
        follow_redirects=False,
    )


def test_pdv_tela_exibe_desconto_manual(client, produto_teste):
    response = client.get("/pdv/")
    assert response.status_code == 200
    assert "desconto-manual-tipo" in response.text
    assert "desconto-manual-valor" in response.text
    assert "pagamento-restante" in response.text


def test_venda_com_uma_forma_de_pagamento_continua_funcionando(
    client, produto_teste, db_session_test
):
    response = enviar_venda(
        client, produto_teste.id,
        forma1="pix", valor1="100.00"
    )
    assert response.status_code == 303
    assert "/pdv/venda/" in response.headers["location"]

    venda = db_session_test.query(Venda).one()
    pagamentos = db_session_test.query(Pagamento).filter_by(venda_id=venda.id).all()
    assert venda.total_bruto == 100.0
    assert venda.total_liquido == 100.0
    assert len(pagamentos) == 1
    assert pagamentos[0].forma_pagamento == "pix"
    assert pagamentos[0].valor == 100.0
    assert produto_teste.estoque_atual == 19


def test_venda_com_duas_formas_de_pagamento(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        forma1="dinheiro", valor1="60.00",
        forma2="pix", valor2="40.00",
    )
    assert response.status_code == 303

    venda = db_session_test.query(Venda).one()
    pagamentos = (
        db_session_test.query(Pagamento)
        .filter_by(venda_id=venda.id)
        .order_by(Pagamento.id)
        .all()
    )
    assert len(pagamentos) == 2
    assert {p.forma_pagamento for p in pagamentos} == {"dinheiro", "pix"}
    assert round(sum(p.valor for p in pagamentos), 2) == venda.total_liquido


def test_venda_com_desconto_manual_percentual(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        valor1="90.00",
        desconto_tipo="percentual", desconto_valor="10",
    )
    assert response.status_code == 303
    venda = db_session_test.query(Venda).one()
    assert venda.total_bruto == 100.0
    assert venda.total_liquido == 90.0
    assert round(venda.desconto_valor, 2) == 10.0


def test_venda_com_desconto_manual_em_reais(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        valor1="85.00",
        desconto_tipo="valor", desconto_valor="15",
    )
    assert response.status_code == 303
    venda = db_session_test.query(Venda).one()
    assert venda.total_liquido == 85.0
    assert round(venda.desconto_valor, 2) == 15.0


def test_bloqueia_desconto_maior_que_subtotal(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        valor1="100.00",
        desconto_tipo="valor", desconto_valor="101",
    )
    assert response.status_code == 303
    assert "erro=desconto_limite" in response.headers["location"]
    assert db_session_test.query(Venda).count() == 0
    assert produto_teste.estoque_atual == 20


def test_bloqueia_percentual_de_desconto_maior_que_cem(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        valor1="100.00",
        desconto_tipo="percentual", desconto_valor="101",
    )
    assert response.status_code == 303
    assert "erro=desconto_limite" in response.headers["location"]
    assert db_session_test.query(Venda).count() == 0


def test_bloqueia_pagamentos_que_nao_fecham_o_total(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        valor1="80.00",
    )
    assert response.status_code == 303
    assert "erro=pagamento_total" in response.headers["location"]
    assert db_session_test.query(Venda).count() == 0


def test_bloqueia_duas_formas_de_pagamento_iguais(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        forma1="pix", valor1="50.00",
        forma2="pix", valor2="50.00",
    )
    assert response.status_code == 303
    assert "erro=pagamentos_iguais" in response.headers["location"]
    assert db_session_test.query(Venda).count() == 0


def test_bloqueia_carrinho_vazio(client, db_session_test):
    response = client.post(
        "/pdv/finalizar",
        data={
            "carrinho_json": "[]",
            "forma_pagamento_1": "dinheiro",
            "valor_pagamento_1": "0",
            "forma_pagamento_2": "",
            "valor_pagamento_2": "0",
            "desconto_manual_tipo": "percentual",
            "desconto_manual_valor": "0",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "erro=vazio" in response.headers["location"]


def test_bloqueia_quantidade_maior_que_estoque(client, produto_teste, db_session_test):
    response = enviar_venda(
        client, produto_teste.id,
        quantidade=21,
        valor1="2100.00",
    )
    assert response.status_code == 303
    assert "erro=estoque" in response.headers["location"]
    assert db_session_test.query(Venda).count() == 0
    assert produto_teste.estoque_atual == 20


def test_comprovante_mostra_os_pagamentos(client, dados_teste):
    response = client.get(f"/pdv/venda/{dados_teste['venda'].id}")
    assert response.status_code == 200
    assert "Pagamentos" in response.text
    assert "PIX" in response.text


def test_historico_de_vendas_responde(client, dados_teste):
    response = client.get("/pdv/historico")
    assert response.status_code == 200
    assert "Venda" in response.text

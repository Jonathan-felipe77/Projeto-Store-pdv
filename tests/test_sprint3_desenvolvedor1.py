"""Parte 1 dos testes da Sprint 3: autenticação, usuários, categorias e clientes."""

from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.usuarios import Usuario


def test_tela_login(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "Login" in response.text or "login" in response.text.lower()


def test_tela_cadastro(client):
    response = client.get("/auth/cadastro")
    assert response.status_code == 200
    assert "Cadastrar" in response.text


def test_login_com_senha_incorreta(client):
    response = client.post(
        "/auth/login",
        data={"email": "admin@teste.local", "senha": "incorreta"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "incorretos" in response.text.lower()


def test_login_com_credenciais_corretas(client):
    response = client.post(
        "/auth/login",
        data={"email": "admin@teste.local", "senha": "SenhaTeste123!"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert "access_token" in response.headers.get("set-cookie", "")


def test_cadastro_nao_permite_email_duplicado(client):
    response = client.post(
        "/auth/cadastro",
        data={
            "nome": "Duplicado",
            "email": "admin@teste.local",
            "senha": "SenhaTeste123!",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "já está cadastrado" in response.text.lower()


def test_lista_de_usuarios(client):
    response = client.get("/usuarios/")
    assert response.status_code == 200
    assert "Administrador de teste" in response.text


def test_cadastro_de_usuario_valida_perfil(client, db_session_test):
    response = client.post(
        "/usuarios/novo",
        data={
            "nome": "Pessoa Nova",
            "email": "pessoa.nova@teste.local",
            "senha": "SenhaTeste123!",
            "role": "perfil_invalido",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Perfil de acesso inválido" in response.text
    assert db_session_test.query(Usuario).filter_by(email="pessoa.nova@teste.local").count() == 0


def test_listagem_de_categorias(client, dados_teste):
    response = client.get("/categorias/")
    assert response.status_code == 200
    assert "Uniformes" in response.text


def test_categoria_rejeita_nome_vazio(client, db_session_test):
    response = client.post(
        "/categorias/nova",
        data={"nome": "   "},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert db_session_test.query(Categoria).count() == 0


def test_categoria_pode_ser_cadastrada(client, db_session_test):
    response = client.post(
        "/categorias/nova",
        data={"nome": "Acessórios"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db_session_test.query(Categoria).filter_by(nome="Acessórios").count() == 1


def test_listagem_clientes_aceita_busca(client, dados_teste):
    response = client.get("/clientes/", params={"busca": "Ana"})
    assert response.status_code == 200
    assert "Ana Teste" in response.text


def test_cliente_rejeita_nome_vazio(client, db_session_test):
    response = client.post(
        "/clientes/novo",
        data={"nome": "   ", "matricula": "", "telefone": "", "desconto_percentual": "0"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert db_session_test.query(Cliente).count() == 0

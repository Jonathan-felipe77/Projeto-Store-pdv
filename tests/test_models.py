from app.auth import hash_senha, verificar_senha

#Rodar o teste: python -m pytest
# pip install pytest

#Testar as funções do arquivo auth.py
def test_hash_senha_gera_string_diferente_original():

    senha = "minha_senha"

    hash_gerado = hash_senha(senha)

    #Testar a função
    assert senha != hash_gerado

# Testar a função verificar_senha
def test_verificar_senha_correta():

    senha = "santos@123"
    hash_gerado = hash_senha(senha)

    resultado = verificar_senha(senha, hash_gerado)

    # Testar a função
    #assert resultado == True
    assert resultado is True

# Criar a função para verificar a senha rejeitada uma senha incorreta
def test_verificar_senha_incorreta():
    senha = "santos@12"
    hash_gerado = hash_senha(senha)

    resultado = verificar_senha("senha_incorreta", hash_gerado)

    # Testar a função
    assert resultado is False
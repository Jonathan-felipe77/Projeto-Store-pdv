
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.movimentacao import Movimentacao, TipoMovimentacao
from app.models.produto import Produto
from app.auth import get_usuario_logado, get_admin


router = APIRouter(
    prefix="/movimentacoes",
    tags=["Movimentações"]
)

templates = Jinja2Templates(
    directory="app/templates"
)


# ============================================================
# HISTÓRICO GERAL
#
# SOMENTE ADMIN
#
# Também calcula os dados usados nos cards da tela:
# - total_unidades
# - estoque_baixo
# - sem_estoque
# ============================================================

@router.get("/", response_class=HTMLResponse)
def listar_movimentacoes(
    request: Request,
    produto_id: int = 0,
    tipo: str = "",
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):
    """
    Exibe o histórico completo das movimentações.

    Somente administrador pode acessar.
    """

    # --------------------------------------------------------
    # BUSCA TODAS AS MOVIMENTAÇÕES
    # --------------------------------------------------------

    query = (
        db.query(Movimentacao)
        .order_by(Movimentacao.criado_em.desc())
    )

    # --------------------------------------------------------
    # FILTRO POR PRODUTO
    # --------------------------------------------------------

    if produto_id:
        query = query.filter(
            Movimentacao.produto_id == produto_id
        )

    # --------------------------------------------------------
    # FILTRO POR TIPO
    # --------------------------------------------------------

    if tipo in (
        "entrada",
        "saida",
        "cancelamento",
        "ajuste"
    ):
        query = query.filter(
            Movimentacao.tipo == tipo
        )

    # --------------------------------------------------------
    # LIMITA O HISTÓRICO
    # --------------------------------------------------------

    movimentacoes = (
        query
        .limit(200)
        .all()
    )

    # --------------------------------------------------------
    # BUSCA PRODUTOS ATIVOS
    #
    # Esses produtos serão usados:
    # - no filtro;
    # - na tabela de estoque;
    # - no cálculo dos cards.
    # --------------------------------------------------------

    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

    # ========================================================
    # CÁLCULO DOS CARDS DO ESTOQUE
    # ========================================================

    # --------------------------------------------------------
    # QUANTIDADE TOTAL DE UNIDADES
    #
    # Soma o estoque atual de todos os produtos ativos.
    #
    # Exemplo:
    #
    # Camisa = 10
    # Calça  = 20
    # Tênis  = 5
    #
    # Total = 35
    # --------------------------------------------------------

    total_unidades = sum(
        (produto.estoque_atual or 0)
        for produto in produtos
    )

    # --------------------------------------------------------
    # PRODUTOS COM ESTOQUE BAIXO
    #
    # Consideramos estoque baixo quando existem:
    #
    # 1 até 10 unidades.
    #
    # Produto com 0 unidades NÃO entra aqui porque possui
    # uma categoria separada de "Sem estoque".
    # --------------------------------------------------------

    estoque_baixo = sum(
        1
        for produto in produtos
        if 0 < (produto.estoque_atual or 0) <= 10
    )

    # --------------------------------------------------------
    # PRODUTOS SEM ESTOQUE
    #
    # Conta produtos com estoque:
    #
    # 0 ou menor.
    # --------------------------------------------------------

    sem_estoque = sum(
        1
        for produto in produtos
        if (produto.estoque_atual or 0) <= 0
    )

    # --------------------------------------------------------
    # TOTAL DE PRODUTOS
    # --------------------------------------------------------

    total_produtos = len(produtos)

    # --------------------------------------------------------
    # TOTAL DE MOVIMENTAÇÕES
    # --------------------------------------------------------

    total_movimentacoes = len(movimentacoes)

    # --------------------------------------------------------
    # TOTAL DE ENTRADAS
    # --------------------------------------------------------

    total_entradas = sum(
        1
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.ENTRADA
    )

    # --------------------------------------------------------
    # TOTAL DE SAÍDAS
    # --------------------------------------------------------

    total_saidas = sum(
        1
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.SAIDA
    )

    # ========================================================
    # ENVIA TUDO PARA O INDEX.HTML
    # ========================================================

    return templates.TemplateResponse(
        request,
        "movimentacoes/index.html",
        {
            "request": request,

            # Usuário logado
            "usuario": admin,

            # Movimentações
            "movimentacoes": movimentacoes,

            # Produtos
            "produtos": produtos,

            # Filtros
            "produto_id": produto_id,
            "tipo": tipo,

            # Cards de estoque
            "total_produtos": total_produtos,
            "total_unidades": total_unidades,
            "estoque_baixo": estoque_baixo,
            "sem_estoque": sem_estoque,

            # Cards de movimentação
            "total_movimentacoes": total_movimentacoes,
            "total_entradas": total_entradas,
            "total_saidas": total_saidas,
        }
    )


# ============================================================
# FORMULÁRIO DE NOVA MOVIMENTAÇÃO
#
# QUALQUER USUÁRIO LOGADO
# ============================================================

@router.get("/nova", response_class=HTMLResponse)
def form_nova_movimentacao(
    request: Request,
    produto_id: int = 0,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    """
    Exibe o formulário para registrar uma movimentação.

    Qualquer usuário autenticado pode acessar.
    """

    # --------------------------------------------------------
    # BUSCA PRODUTOS ATIVOS
    # --------------------------------------------------------

    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

    # --------------------------------------------------------
    # MOSTRA FORMULÁRIO
    # --------------------------------------------------------

    return templates.TemplateResponse(
        request,
        "movimentacoes/form.html",
        {
            "request": request,
            "usuario": usuario,
            "produtos": produtos,
            "produto_id": produto_id,
            "tipos": TipoMovimentacao,
        }
    )


# ============================================================
# REGISTRAR MOVIMENTAÇÃO
#
# QUALQUER USUÁRIO LOGADO
# ============================================================

@router.post("/nova")
def registrar_movimentacao(
    request: Request,
    produto_id: int = Form(...),
    tipo: str = Form(...),
    quantidade: int = Form(...),
    preco_unitario: float = Form(...),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    """
    Registra entrada ou saída e atualiza o estoque.

    A movimentação e a alteração de estoque são salvas
    na mesma transação.
    """

    # --------------------------------------------------------
    # BUSCA PRODUTOS PARA O FORMULÁRIO
    # --------------------------------------------------------

    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

    # --------------------------------------------------------
    # VALIDAÇÃO DO TIPO
    # --------------------------------------------------------

    if tipo not in (
        TipoMovimentacao.ENTRADA,
        TipoMovimentacao.SAIDA
    ):

        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": "Tipo de movimentação inválido.",
            },
            status_code=400
        )

    # --------------------------------------------------------
    # VALIDAÇÃO DA QUANTIDADE
    # --------------------------------------------------------

    if quantidade <= 0:

        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": "A quantidade deve ser maior que zero.",
            },
            status_code=400
        )

    # --------------------------------------------------------
    # VALIDAÇÃO DO PREÇO
    # --------------------------------------------------------

    if preco_unitario < 0:

        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": "O preço unitário não pode ser negativo.",
            },
            status_code=400
        )

    # --------------------------------------------------------
    # BUSCA PRODUTO COM LOCK
    #
    # with_for_update() ajuda a evitar problemas quando
    # duas movimentações tentam alterar o mesmo produto
    # ao mesmo tempo.
    # --------------------------------------------------------

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id
        )
        .with_for_update()
        .first()
    )

    # --------------------------------------------------------
    # PRODUTO NÃO EXISTE
    # --------------------------------------------------------

    if not produto:

        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": "Produto não encontrado.",
            },
            status_code=404
        )

    # --------------------------------------------------------
    # PRODUTO DESATIVADO
    # --------------------------------------------------------

    if not produto.ativo:

        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": "Este produto está desativado.",
            },
            status_code=400
        )

    # --------------------------------------------------------
    # PEGA ESTOQUE ATUAL
    # --------------------------------------------------------

    estoque_atual = produto.estoque_atual or 0

    # --------------------------------------------------------
    # NÃO PERMITE SAÍDA MAIOR QUE O ESTOQUE
    # --------------------------------------------------------

    if (
        tipo == TipoMovimentacao.SAIDA
        and quantidade > estoque_atual
    ):

        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": (
                    "Estoque insuficiente. "
                    f"Disponível: {estoque_atual} unidade(s)."
                ),
            },
            status_code=400
        )

    # ========================================================
    # ATUALIZA O ESTOQUE
    # ========================================================

    if tipo == TipoMovimentacao.ENTRADA:

        produto.estoque_atual = (
            estoque_atual + quantidade
        )

    elif tipo == TipoMovimentacao.SAIDA:

        produto.estoque_atual = (
            estoque_atual - quantidade
        )

    # ========================================================
    # CRIA A MOVIMENTAÇÃO
    # ========================================================

    movimentacao = Movimentacao(
        tipo=tipo,
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        observacao=observacao.strip() or None,
        produto_id=produto_id,
        usuario_id=usuario.get("id"),
    )

    db.add(movimentacao)

    # ========================================================
    # SALVA ESTOQUE + MOVIMENTAÇÃO
    # ========================================================

    try:

        db.commit()

    except Exception:

        db.rollback()

        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": (
                    "Não foi possível registrar "
                    "a movimentação."
                ),
            },
            status_code=500
        )

    # ========================================================
    # REDIRECIONA PARA O PRODUTO
    # ========================================================

    return RedirectResponse(
        url=f"/produtos/{produto_id}?movimentacao=ok",
        status_code=302
    )


# ============================================================
# HISTÓRICO POR PRODUTO
#
# ADMIN:
#   vê todas as movimentações.
#
# OPERADOR:
#   vê somente suas próprias movimentações.
# ============================================================

@router.get(
    "/produto/{produto_id}",
    response_class=HTMLResponse
)
def historico_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    """
    Exibe o histórico de um produto específico.
    """

    # --------------------------------------------------------
    # BUSCA PRODUTO
    # --------------------------------------------------------

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id
        )
        .first()
    )

    # --------------------------------------------------------
    # SE NÃO ENCONTRAR, VOLTA PARA PRODUTOS
    # --------------------------------------------------------

    if not produto:

        return RedirectResponse(
            url="/produtos",
            status_code=302
        )

    # --------------------------------------------------------
    # CRIA CONSULTA
    # --------------------------------------------------------

    query = (
        db.query(Movimentacao)
        .filter(
            Movimentacao.produto_id == produto_id
        )
        .order_by(
            Movimentacao.criado_em.desc()
        )
    )

    # --------------------------------------------------------
    # OPERADOR VÊ APENAS AS PRÓPRIAS MOVIMENTAÇÕES
    # --------------------------------------------------------

    if usuario.get("role") != "admin":

        query = query.filter(
            Movimentacao.usuario_id == usuario.get("id")
        )

    # --------------------------------------------------------
    # EXECUTA CONSULTA
    # --------------------------------------------------------

    movimentacoes = query.all()

    # ========================================================
    # CALCULA TOTAL DE ENTRADAS
    # ========================================================

    total_entradas = sum(
        movimentacao.quantidade
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.ENTRADA
    )

    # ========================================================
    # CALCULA TOTAL DE SAÍDAS
    # ========================================================

    total_saidas = sum(
        movimentacao.quantidade
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.SAIDA
    )

    # ========================================================
    # CALCULA SALDO DAS MOVIMENTAÇÕES
    # ========================================================

    saldo_movimentacoes = (
        total_entradas - total_saidas
    )

    # ========================================================
    # ENVIA PARA O TEMPLATE
    # ========================================================

    return templates.TemplateResponse(
        request,
        "movimentacoes/historico.html",
        {
            "request": request,
            "usuario": usuario,
            "produto": produto,
            "movimentacoes": movimentacoes,
            "total_entradas": total_entradas,
            "total_saidas": total_saidas,
            "saldo_movimentacoes": saldo_movimentacoes,
        }
    )
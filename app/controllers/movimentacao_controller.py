from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form
)

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
# SOMENTE ADMIN
# ============================================================

@router.get("/", response_class=HTMLResponse)
def listar_movimentacoes(
    request: Request,
    produto_id: int = 0,
    tipo: str = "",
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    query = (
        db.query(Movimentacao)
        .order_by(Movimentacao.criado_em.desc())
    )

    # Filtro por produto
    if produto_id:

        query = query.filter(
            Movimentacao.produto_id == produto_id
        )

    # Filtro por tipo
    if tipo in (
        "entrada",
        "saida",
        "cancelamento",
        "ajuste"
    ):

        query = query.filter(
            Movimentacao.tipo == tipo
        )

    # Histórico
    movimentacoes = (
        query
        .limit(200)
        .all()
    )

    # Produtos ativos
    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

    # ========================================================
    # CARDS DE ESTOQUE
    # ========================================================

    total_unidades = sum(
        (produto.estoque_atual or 0)
        for produto in produtos
    )

    estoque_baixo = sum(
        1
        for produto in produtos
        if 0 < (produto.estoque_atual or 0) <= 10
    )

    sem_estoque = sum(
        1
        for produto in produtos
        if (produto.estoque_atual or 0) <= 0
    )

    total_produtos = len(produtos)

    total_movimentacoes = len(movimentacoes)

    total_entradas = sum(
        1
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.ENTRADA
    )

    total_saidas = sum(
        1
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.SAIDA
    )

    return templates.TemplateResponse(
        request,
        "movimentacoes/index.html",
        {
            "request": request,

            "usuario": admin,

            "movimentacoes": movimentacoes,

            "produtos": produtos,

            "produto_id": produto_id,

            "tipo": tipo,

            "total_produtos": total_produtos,

            "total_unidades": total_unidades,

            "estoque_baixo": estoque_baixo,

            "sem_estoque": sem_estoque,

            "total_movimentacoes": total_movimentacoes,

            "total_entradas": total_entradas,

            "total_saidas": total_saidas,
        }
    )


# ============================================================
# FORMULÁRIO DE NOVA MOVIMENTAÇÃO
# QUALQUER USUÁRIO LOGADO
# ============================================================

@router.get("/nova", response_class=HTMLResponse)
def form_nova_movimentacao(
    request: Request,
    produto_id: int = 0,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):

    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

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

    # --------------------------------------------------------
    # BUSCA PRODUTOS
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
    # BUSCA PRODUTO
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
    # ESTOQUE ATUAL
    # --------------------------------------------------------

    estoque_atual = produto.estoque_atual or 0

    # --------------------------------------------------------
    # VERIFICA ESTOQUE PARA SAÍDA
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
    # ATUALIZA ESTOQUE
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
    # CRIA MOVIMENTAÇÃO
    # ========================================================

    movimentacao = Movimentacao(
        tipo=tipo,

        quantidade=quantidade,

        preco_unitario=preco_unitario,

        observacao=(
            observacao.strip()
            if observacao
            else None
        ),

        produto_id=produto_id,

        usuario_id=usuario.get("id"),
    )

    db.add(movimentacao)

    # ========================================================
    # SALVA
    # ========================================================

    try:

        db.commit()

        db.refresh(movimentacao)

        db.refresh(produto)

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
    # TELA DE SUCESSO
    # ========================================================

    return RedirectResponse(
        url=f"/movimentacoes/sucesso/{movimentacao.id}",
        status_code=303
    )


# ============================================================
# TELA - MOVIMENTAÇÃO REALIZADA COM SUCESSO
# ============================================================

@router.get(
    "/sucesso/{movimentacao_id}",
    response_class=HTMLResponse
)
def movimentacao_sucesso(
    movimentacao_id: int,

    request: Request,

    db: Session = Depends(get_db),

    usuario=Depends(get_usuario_logado)
):

    # Busca a movimentação
    movimentacao = (
        db.query(Movimentacao)
        .filter(
            Movimentacao.id == movimentacao_id
        )
        .first()
    )

    # Se não encontrar
    if not movimentacao:

        return RedirectResponse(
            url="/movimentacoes/",
            status_code=302
        )

    # Busca o produto
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == movimentacao.produto_id
        )
        .first()
    )

    return templates.TemplateResponse(
        request,
        "movimentacoes/sucesso.html",
        {
            "request": request,

            "usuario": usuario,

            "movimentacao": movimentacao,

            "produto": produto
        }
    )


# ============================================================
# HISTÓRICO POR PRODUTO
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

    if not produto:

        return RedirectResponse(
            url="/produtos",
            status_code=302
        )

    # --------------------------------------------------------
    # CONSULTA
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
    # OPERADOR
    # --------------------------------------------------------

    if usuario.get("role") != "admin":

        query = query.filter(
            Movimentacao.usuario_id == usuario.get("id")
        )

    movimentacoes = query.all()

    # --------------------------------------------------------
    # TOTAL DE ENTRADAS
    # --------------------------------------------------------

    total_entradas = sum(
        movimentacao.quantidade
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.ENTRADA
    )

    # --------------------------------------------------------
    # TOTAL DE SAÍDAS
    # --------------------------------------------------------

    total_saidas = sum(
        movimentacao.quantidade
        for movimentacao in movimentacoes
        if movimentacao.tipo == TipoMovimentacao.SAIDA
    )

    # --------------------------------------------------------
    # SALDO
    # --------------------------------------------------------

    saldo_movimentacoes = (
        total_entradas - total_saidas
    )

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
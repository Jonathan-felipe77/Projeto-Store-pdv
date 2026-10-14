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

templates = Jinja2Templates(directory="app/templates")


# ============================================================
# ESTOQUE
# GET /movimentacoes/
# ============================================================

@router.get("/", response_class=HTMLResponse)
def listar_estoque(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

    total_unidades = sum(
        produto.estoque_atual or 0
        for produto in produtos
    )

    estoque_baixo = sum(
        1 for produto in produtos
        if 0 < (produto.estoque_atual or 0) <= 10
    )

    sem_estoque = sum(
        1 for produto in produtos
        if (produto.estoque_atual or 0) <= 0
    )

    return templates.TemplateResponse(
        request,
        "movimentacoes/index.html",
        {
            "request": request,
            "usuario": usuario,
            "produtos": produtos,
            "total_unidades": total_unidades,
            "estoque_baixo": estoque_baixo,
            "sem_estoque": sem_estoque,
        }
    )


# ============================================================
# HISTÓRICO GERAL
# GET /movimentacoes/historico
# SOMENTE ADMINISTRADOR
# ============================================================

@router.get("/historico", response_class=HTMLResponse)
def historico_geral(
    request: Request,
    produto_id: int = 0,
    tipo: str = "",
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):
    query = db.query(Movimentacao).order_by(
        Movimentacao.criado_em.desc()
    )

    # Filtrar por produto
    if produto_id > 0:
        query = query.filter(
            Movimentacao.produto_id == produto_id
        )

    # Filtrar apenas pelos tipos disponíveis no formulário.
    # Não usar CANCELAMENTO ou AJUSTE como atributos do enum,
    # pois eles não existem no seu modelo atual.
    if tipo in ("entrada", "saida"):
        query = query.filter(
            Movimentacao.tipo == tipo
        )

    movimentacoes = query.limit(500).all()

    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "movimentacoes/historico.html",
        {
            "request": request,
            "usuario": admin,
            "movimentacoes": movimentacoes,
            "produtos": produtos,
            "produto_id": produto_id,
            "tipo": tipo,
        }
    )


# ============================================================
# FORMULÁRIO DE NOVA MOVIMENTAÇÃO
# GET /movimentacoes/nova
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
# POST /movimentacoes/nova
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
    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True)
        .order_by(Produto.nome.asc())
        .all()
    )

    def retornar_erro(mensagem, status_code=400):
        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produtos": produtos,
                "produto_id": produto_id,
                "tipos": TipoMovimentacao,
                "erro": mensagem,
            },
            status_code=status_code
        )

    # Validar tipo
    if tipo not in (
        TipoMovimentacao.ENTRADA,
        TipoMovimentacao.SAIDA
    ):
        return retornar_erro(
            "Tipo de movimentação inválido."
        )

    # Validar quantidade
    if quantidade <= 0:
        return retornar_erro(
            "A quantidade deve ser maior que zero."
        )

    # Validar preço
    if preco_unitario < 0:
        return retornar_erro(
            "O preço unitário não pode ser negativo."
        )

    # Buscar produto
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id)
        .with_for_update()
        .first()
    )

    if not produto:
        return retornar_erro(
            "Produto não encontrado.",
            status_code=404
        )

    if not produto.ativo:
        return retornar_erro(
            "Este produto está desativado."
        )

    estoque_atual = produto.estoque_atual or 0

    # Verificar estoque para saída
    if (
        tipo == TipoMovimentacao.SAIDA
        and quantidade > estoque_atual
    ):
        return retornar_erro(
            f"Estoque insuficiente. Disponível: {estoque_atual} unidade(s)."
        )

    # Atualizar quantidade
    if tipo == TipoMovimentacao.ENTRADA:
        produto.estoque_atual = estoque_atual + quantidade

    elif tipo == TipoMovimentacao.SAIDA:
        produto.estoque_atual = estoque_atual - quantidade

    # Criar movimentação
    movimentacao = Movimentacao(
        tipo=tipo,
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        observacao=observacao.strip() or None,
        produto_id=produto_id,
        usuario_id=usuario.get("id"),
    )

    db.add(movimentacao)

    try:
        db.commit()
        db.refresh(movimentacao)

    except Exception:
        db.rollback()

        return retornar_erro(
            "Não foi possível registrar a movimentação. Verifique os dados e tente novamente.",
            status_code=500
        )

    return RedirectResponse(
        url=f"/movimentacoes/sucesso/{movimentacao.id}",
        status_code=303
    )


# ============================================================
# SUCESSO DA MOVIMENTAÇÃO
# GET /movimentacoes/sucesso/{movimentacao_id}
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
    movimentacao = (
        db.query(Movimentacao)
        .filter(Movimentacao.id == movimentacao_id)
        .first()
    )

    if not movimentacao:
        return RedirectResponse(
            url="/movimentacoes/",
            status_code=302
        )

    produto = (
        db.query(Produto)
        .filter(Produto.id == movimentacao.produto_id)
        .first()
    )

    return templates.TemplateResponse(
        request,
        "movimentacoes/sucesso.html",
        {
            "request": request,
            "usuario": usuario,
            "movimentacao": movimentacao,
            "produto": produto,
        }
    )


# ============================================================
# HISTÓRICO INDIVIDUAL DO PRODUTO
# GET /movimentacoes/produto/{produto_id}
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
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id)
        .first()
    )

    if not produto:
        return RedirectResponse(
            url="/produtos/",
            status_code=302
        )

    query = (
        db.query(Movimentacao)
        .filter(Movimentacao.produto_id == produto_id)
        .order_by(Movimentacao.criado_em.desc())
    )

    # Usuários comuns veem as próprias movimentações.
    # Administradores veem todas as movimentações do produto.
    if usuario.get("role") != "admin":
        query = query.filter(
            Movimentacao.usuario_id == usuario.get("id")
        )

    movimentacoes = query.all()

    total_entradas = sum(
        m.quantidade
        for m in movimentacoes
        if m.tipo == TipoMovimentacao.ENTRADA
    )

    total_saidas = sum(
        m.quantidade
        for m in movimentacoes
        if m.tipo == TipoMovimentacao.SAIDA
    )

    saldo_movimentacoes = total_entradas - total_saidas

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
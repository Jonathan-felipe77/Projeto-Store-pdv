
import json

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venda import Venda, ItemVenda
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.auth import get_usuario_logado


router = APIRouter(
    prefix="/pdv",
    tags=["PDV"]
)

templates = Jinja2Templates(
    directory="app/templates"
)


# ============================================================
# DESCONTO
# ============================================================

# Cliente associado recebe 10% de desconto
DESCONTO_ASSOCIADO = 10.0


# ============================================================
# TELA DO PDV
# ============================================================

@router.get("/")
def tela_pdv(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    """
    Carrega a tela do PDV com:
    - produtos ativos
    - produtos com estoque
    - clientes ativos
    - percentual de desconto do associado
    """

    produtos = (
        db.query(Produto)
        .filter(
            Produto.ativo == True,
            Produto.estoque_atual > 0
        )
        .order_by(Produto.nome)
        .all()
    )

    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.ativo == True
        )
        .order_by(Cliente.nome)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "pdv/index.html",
        {
            "request": request,
            "usuario": usuario,
            "produtos": produtos,
            "clientes": clientes,
            "desconto_associado": DESCONTO_ASSOCIADO,
        }
    )


# ============================================================
# FINALIZAR VENDA
# ============================================================

@router.post("/finalizar")
def finalizar_venda(
    request: Request,

    # JSON enviado pelo JavaScript
    carrinho_json: str = Form(...),

    # Cliente selecionado no PDV
    # 0 = sem cliente
    cliente_id: int = Form(0),

    observacao: str = Form(""),

    db: Session = Depends(get_db),

    usuario=Depends(get_usuario_logado)
):
    """
    Recebe o carrinho, valida os produtos,
    verifica o tipo do cliente, calcula desconto
    e salva a venda.
    """

    # ========================================================
    # LER CARRINHO
    # ========================================================

    try:
        itens = json.loads(carrinho_json)

    except (json.JSONDecodeError, ValueError, TypeError):

        return RedirectResponse(
            url="/pdv?erro=json",
            status_code=302
        )

    # Carrinho vazio
    if not itens:

        return RedirectResponse(
            url="/pdv?erro=vazio",
            status_code=302
        )

    # ========================================================
    # BUSCAR CLIENTE
    # ========================================================

    cliente = None

    desconto_percentual = 0.0

    if cliente_id:

        cliente = (
            db.query(Cliente)
            .filter(
                Cliente.id == cliente_id,
                Cliente.ativo == True
            )
            .first()
        )

        # Cliente informado não existe
        if not cliente:

            return RedirectResponse(
                url="/pdv?erro=cliente_inexistente",
                status_code=302
            )

        # ====================================================
        # VERIFICA SE É CLIENTE ASSOCIADO
        # ====================================================
        #
        # O cadastro envia:
        #
        # tipo_cliente = "normal"
        #
        # ou
        #
        # tipo_cliente = "associado"
        #
        # ====================================================

        tipo_cliente = getattr(
            cliente,
            "tipo_cliente",
            None
        )

        if tipo_cliente:

            tipo_cliente = str(
                tipo_cliente
            ).strip().lower()

        if tipo_cliente == "associado":

            desconto_percentual = DESCONTO_ASSOCIADO

    # ========================================================
    # VALIDAR ESTOQUE E CALCULAR TOTAL BRUTO
    # ========================================================

    total_bruto = 0.0

    itens_validados = []

    for item in itens:

        # ----------------------------------------------------
        # Validar dados recebidos
        # ----------------------------------------------------

        try:

            produto_id = int(
                item["produto_id"]
            )

            quantidade = int(
                item["quantidade"]
            )

        except (KeyError, TypeError, ValueError):

            return RedirectResponse(
                url="/pdv?erro=item_invalido",
                status_code=302
            )

        # ----------------------------------------------------
        # Quantidade inválida
        # ----------------------------------------------------

        if quantidade <= 0:

            return RedirectResponse(
                url="/pdv?erro=quantidade",
                status_code=302
            )

        # ----------------------------------------------------
        # Buscar produto novamente no banco
        # ----------------------------------------------------

        produto = (
            db.query(Produto)
            .filter(
                Produto.id == produto_id,
                Produto.ativo == True
            )
            .with_for_update()
            .first()
        )

        if not produto:

            return RedirectResponse(
                url=f"/pdv?erro=produto_inexistente&id={produto_id}",
                status_code=302
            )

        # ----------------------------------------------------
        # Verificar estoque
        # ----------------------------------------------------

        if produto.estoque_atual < quantidade:

            return RedirectResponse(
                url=f"/pdv?erro=estoque&produto={produto.nome}",
                status_code=302
            )

        # ----------------------------------------------------
        # Subtotal do produto
        # ----------------------------------------------------

        subtotal = float(
            produto.preco
        ) * quantidade

        total_bruto += subtotal

        # ----------------------------------------------------
        # Guardar item validado
        # ----------------------------------------------------

        itens_validados.append(
            {
                "produto": produto,
                "quantidade": quantidade,
                "preco": float(produto.preco),
                "produto_nome": produto.nome,
            }
        )

    # ========================================================
    # CALCULAR DESCONTO
    # ========================================================

    desconto_valor = (
        total_bruto *
        (desconto_percentual / 100)
    )

    # ========================================================
    # TOTAL FINAL
    # ========================================================

    total_liquido = (
        total_bruto -
        desconto_valor
    )

    # ========================================================
    # GARANTIR DUAS CASAS DECIMAIS
    # ========================================================

    total_bruto = round(
        total_bruto,
        2
    )

    desconto_valor = round(
        desconto_valor,
        2
    )

    total_liquido = round(
        total_liquido,
        2
    )

    # ========================================================
    # CRIAR VENDA
    # ========================================================

    venda = Venda(
        cliente_id=cliente_id or None,

        usuario_id=usuario.get("id"),

        desconto_percentual=desconto_percentual,

        total_bruto=total_bruto,

        total_liquido=total_liquido,

        observacao=observacao or None,
    )

    db.add(venda)

    # Gera o ID da venda
    db.flush()

    # ========================================================
    # CRIAR ITENS DA VENDA
    # ========================================================

    for item in itens_validados:

        produto = item["produto"]

        quantidade = item["quantidade"]

        preco = item["preco"]

        # ----------------------------------------------------
        # Criar ItemVenda
        # ----------------------------------------------------

        db.add(
            ItemVenda(
                venda_id=venda.id,

                produto_id=produto.id,

                produto_nome=item["produto_nome"],

                quantidade=quantidade,

                preco_unitario=preco,
            )
        )

        # ----------------------------------------------------
        # Baixar estoque
        # ----------------------------------------------------

        produto.estoque_atual -= quantidade

    # ========================================================
    # SALVAR
    # ========================================================

    try:

        db.commit()

    except Exception:

        db.rollback()

        return RedirectResponse(
            url="/pdv?erro=salvar",
            status_code=302
        )

    # ========================================================
    # FINALIZAR
    # ========================================================

    return RedirectResponse(
        url=f"/pdv/venda/{venda.id}?sucesso=ok",
        status_code=302
    )


# ============================================================
# COMPROVANTE
# ============================================================

@router.get("/venda/{venda_id}")
def detalhe_venda(
    venda_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    """
    Exibe o comprovante da venda.
    """

    venda = (
        db.query(Venda)
        .filter(
            Venda.id == venda_id
        )
        .first()
    )

    if not venda:

        return RedirectResponse(
            url="/pdv",
            status_code=302
        )

    return templates.TemplateResponse(
        request,
        "pdv/comprovante.html",
        {
            "request": request,
            "usuario": usuario,
            "venda": venda
        }
    )


# ============================================================
# HISTÓRICO
# ============================================================

@router.get("/historico")
def historico_vendas(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    """
    Histórico das últimas 100 vendas.
    """

    vendas = (
        db.query(Venda)
        .order_by(
            Venda.criado_em.desc()
        )
        .limit(100)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "pdv/historico.html",
        {
            "request": request,
            "usuario": usuario,
            "vendas": vendas
        }
    )
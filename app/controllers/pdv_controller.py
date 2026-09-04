
import json

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form
)

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
# TELA DO PDV
# ============================================================

@router.get("/")
def tela_pdv(

    request: Request,

    db: Session = Depends(get_db),

    usuario=Depends(
        get_usuario_logado
    )
):

    produtos = (

        db.query(Produto)

        .filter(

            Produto.ativo == True,

            Produto.estoque_atual > 0
        )

        .order_by(
            Produto.nome
        )

        .all()
    )


    clientes = (

        db.query(Cliente)

        .filter(
            Cliente.ativo == True
        )

        .order_by(
            Cliente.nome
        )

        .all()
    )


    return templates.TemplateResponse(

        request=request,

        name="pdv/index.html",

        context={

            "request":
                request,

            "usuario":
                usuario,

            "produtos":
                produtos,

            "clientes":
                clientes
        }
    )


# ============================================================
# FINALIZAR VENDA
# ============================================================

@router.post("/finalizar")
def finalizar_venda(

    request: Request,

    carrinho_json: str =
        Form(...),

    cliente_id: int =
        Form(0),

    observacao: str =
        Form(""),

    db: Session =
        Depends(get_db),

    usuario=Depends(
        get_usuario_logado
    )
):

    # ========================================================
    # CARRINHO
    # ========================================================

    try:

        itens = json.loads(
            carrinho_json
        )

    except (
        json.JSONDecodeError,
        ValueError,
        TypeError
    ):

        return RedirectResponse(

            url="/pdv?erro=json",

            status_code=303
        )


    if not itens:

        return RedirectResponse(

            url="/pdv?erro=vazio",

            status_code=303
        )


    # ========================================================
    # CLIENTE
    # ========================================================

    cliente = None

    desconto_percentual = 0.0


    if cliente_id:

        cliente = (

            db.query(Cliente)

            .filter(

                Cliente.id ==
                    cliente_id,

                Cliente.ativo ==
                    True
            )

            .first()
        )


        if not cliente:

            return RedirectResponse(

                url="/pdv?erro=cliente_inexistente",

                status_code=303
            )


        # ====================================================
        # DESCONTO INDIVIDUAL DO CLIENTE
        # ====================================================

        desconto_percentual = float(

            getattr(
                cliente,
                "desconto_percentual",
                0.0
            )
            or 0.0
        )


        # Segurança
        desconto_percentual = max(
            0.0,
            min(
                100.0,
                desconto_percentual
            )
        )


        desconto_percentual = round(
            desconto_percentual,
            2
        )


    # ========================================================
    # PRODUTOS
    # ========================================================

    total_bruto = 0.0

    itens_validados = []


    for item in itens:

        try:

            produto_id = int(
                item["produto_id"]
            )

            quantidade = int(
                item["quantidade"]
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ):

            return RedirectResponse(

                url="/pdv?erro=item_invalido",

                status_code=303
            )


        if quantidade <= 0:

            return RedirectResponse(

                url="/pdv?erro=quantidade",

                status_code=303
            )


        produto = (

            db.query(Produto)

            .filter(

                Produto.id ==
                    produto_id,

                Produto.ativo ==
                    True
            )

            .with_for_update()

            .first()
        )


        if not produto:

            return RedirectResponse(

                url="/pdv?erro=produto_inexistente",

                status_code=303
            )


        if produto.estoque_atual < quantidade:

            return RedirectResponse(

                url="/pdv?erro=estoque",

                status_code=303
            )


        preco = float(
            produto.preco
        )


        subtotal = (

            preco *
            quantidade
        )


        total_bruto += subtotal


        itens_validados.append({

            "produto":
                produto,

            "quantidade":
                quantidade,

            "preco":
                preco,

            "produto_nome":
                produto.nome
        })


    # ========================================================
    # DESCONTO
    # ========================================================

    desconto_valor = (

        total_bruto *

        (
            desconto_percentual
            / 100
        )
    )


    # ========================================================
    # TOTAL FINAL
    # ========================================================

    total_liquido = (

        total_bruto -
        desconto_valor
    )


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
    # VENDA
    # ========================================================

    venda = Venda(

        cliente_id=(
            cliente_id
            if cliente_id
            else None
        ),

        usuario_id=
            usuario.get("id"),

        desconto_percentual=
            desconto_percentual,

        total_bruto=
            total_bruto,

        total_liquido=
            total_liquido,

        observacao=(
            observacao.strip()
            if observacao
            else None
        )
    )


    db.add(venda)

    db.flush()


    # ========================================================
    # ITENS
    # ========================================================

    for item in itens_validados:

        produto = item["produto"]

        quantidade = item["quantidade"]


        db.add(

            ItemVenda(

                venda_id=
                    venda.id,

                produto_id=
                    produto.id,

                produto_nome=
                    item["produto_nome"],

                quantidade=
                    quantidade,

                preco_unitario=
                    item["preco"]
            )
        )


        produto.estoque_atual -= (
            quantidade
        )


    # ========================================================
    # SALVAR
    # ========================================================

    try:

        db.commit()

    except Exception:

        db.rollback()

        return RedirectResponse(

            url="/pdv?erro=salvar",

            status_code=303
        )


    return RedirectResponse(

        url=(
            f"/pdv/venda/"
            f"{venda.id}"
            f"?sucesso=ok"
        ),

        status_code=303
    )


# ============================================================
# COMPROVANTE
# ============================================================

@router.get("/venda/{venda_id}")
def detalhe_venda(

    venda_id: int,

    request: Request,

    db: Session = Depends(get_db),

    usuario=Depends(
        get_usuario_logado
    )
):

    venda = (

        db.query(Venda)

        .filter(
            Venda.id ==
                venda_id
        )

        .first()
    )


    if not venda:

        return RedirectResponse(

            url="/pdv",

            status_code=303
        )


    return templates.TemplateResponse(

        request=request,

        name="pdv/comprovante.html",

        context={

            "request":
                request,

            "usuario":
                usuario,

            "venda":
                venda
        }
    )


# ============================================================
# HISTÓRICO
# ============================================================

@router.get("/historico")
def historico_vendas(

    request: Request,

    db: Session = Depends(get_db),

    usuario=Depends(
        get_usuario_logado
    )
):

    vendas = (

        db.query(Venda)

        .order_by(
            Venda.criado_em.desc()
        )

        .limit(100)

        .all()
    )


    return templates.TemplateResponse(

        request=request,

        name="pdv/historico.html",

        context={

            "request":
                request,

            "usuario":
                usuario,

            "vendas":
                vendas
        }
    )
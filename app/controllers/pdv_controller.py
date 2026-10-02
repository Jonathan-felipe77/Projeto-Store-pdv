
import json

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venda import Venda, ItemVenda
from app.models.pagamento import Pagamento
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


FORMAS_PAGAMENTO_VALIDAS = {
    "dinheiro",
    "pix",
    "debito",
    "credito"
}


def redirecionar_erro(codigo):
    return RedirectResponse(
        url=f"/pdv/?erro={codigo}",
        status_code=303
    )


# ==========================================================
# TELA DO PDV
# ==========================================================

@router.get("/")
def pdv(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    produtos = (
        db.query(Produto)
        .filter(
            Produto.ativo == True,
            Produto.estoque_atual > 0
        )
        .order_by(Produto.nome.asc())
        .all()
    )

    clientes = (
        db.query(Cliente)
        .order_by(Cliente.nome.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "pdv/index.html",
        {
            "request": request,
            "produtos": produtos,
            "clientes": clientes,
            "usuario": usuario
        }
    )


# ==========================================================
# FINALIZAR VENDA
# ==========================================================

@router.post("/finalizar")
def finalizar_venda(
    request: Request,
    carrinho_json: str = Form(...),
    cliente_id: int = Form(0),
    observacao: str = Form(""),
    forma_pagamento_1: str = Form(""),
    valor_pagamento_1: float = Form(0.0),
    forma_pagamento_2: str = Form(""),
    valor_pagamento_2: float = Form(0.0),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    # ======================================================
    # LER CARRINHO
    # ======================================================

    try:
        carrinho = json.loads(carrinho_json)
    except Exception:
        return redirecionar_erro("json")

    if not isinstance(carrinho, list) or len(carrinho) == 0:
        return redirecionar_erro("vazio")

    # ======================================================
    # CLIENTE E DESCONTO DO ASSOCIADO
    # ======================================================

    cliente = None
    desconto_percentual = 0.0

    if cliente_id and cliente_id != 0:

        cliente = (
            db.query(Cliente)
            .filter(
                Cliente.id == cliente_id
            )
            .first()
        )

        if not cliente:
            return redirecionar_erro(
                "cliente_inexistente"
            )

        desconto_percentual = float(
            cliente.desconto_percentual or 0
        )

        if desconto_percentual < 0:
            desconto_percentual = 0

        if desconto_percentual > 100:
            desconto_percentual = 100

    # ======================================================
    # FORMAS DE PAGAMENTO
    # ======================================================

    forma_pagamento_1 = (
        forma_pagamento_1 or ""
    ).strip().lower()

    forma_pagamento_2 = (
        forma_pagamento_2 or ""
    ).strip().lower()

    # ======================================================
    # VALORES DE PAGAMENTO
    # ======================================================

    try:
        valor_pagamento_1 = float(
            valor_pagamento_1 or 0
        )

        valor_pagamento_2 = float(
            valor_pagamento_2 or 0
        )

    except Exception:
        return redirecionar_erro(
            "pagamento_valor"
        )

    # ======================================================
    # PRIMEIRO PAGAMENTO
    # ======================================================

    if (
        forma_pagamento_1
        not in FORMAS_PAGAMENTO_VALIDAS
    ):
        return redirecionar_erro(
            "pagamento_invalido"
        )

    if valor_pagamento_1 <= 0:
        return redirecionar_erro(
            "pagamento_valor"
        )

    # ======================================================
    # SEGUNDO PAGAMENTO
    # ======================================================

    if forma_pagamento_2:

        if (
            forma_pagamento_2
            not in FORMAS_PAGAMENTO_VALIDAS
        ):
            return redirecionar_erro(
                "pagamento_invalido"
            )

        if valor_pagamento_2 <= 0:
            return redirecionar_erro(
                "pagamento_valor"
            )

        if (
            forma_pagamento_1
            == forma_pagamento_2
        ):
            return redirecionar_erro(
                "pagamentos_iguais"
            )

    else:
        valor_pagamento_2 = 0.0

    # ======================================================
    # VALIDAR PRODUTOS
    # ======================================================

    total_bruto = 0.0
    itens_validados = []

    for item in carrinho:

        try:
            produto_id = int(
                item.get("id")
            )

            quantidade = int(
                item.get("quantidade")
            )

        except Exception:
            db.rollback()
            return redirecionar_erro(
                "item_invalido"
            )

        if quantidade <= 0:
            db.rollback()
            return redirecionar_erro(
                "quantidade"
            )

        produto = (
            db.query(Produto)
            .filter(
                Produto.id == produto_id
            )
            .first()
        )

        if not produto:
            db.rollback()
            return redirecionar_erro(
                "produto_inexistente"
            )

        if not produto.ativo:
            db.rollback()
            return redirecionar_erro(
                "produto_inexistente"
            )

        if quantidade > produto.estoque_atual:
            db.rollback()
            return redirecionar_erro(
                "estoque"
            )

        preco = float(
            produto.preco or 0
        )

        subtotal = (
            preco * quantidade
        )

        total_bruto += subtotal

        itens_validados.append(
            {
                "produto": produto,
                "quantidade": quantidade,
                "preco": preco,
                "subtotal": subtotal
            }
        )

    # ======================================================
    # CALCULAR DESCONTO
    # ======================================================

    valor_desconto = (
        total_bruto
        * desconto_percentual
        / 100
    )

    total_liquido = (
        total_bruto
        - valor_desconto
    )

    if total_liquido < 0:
        total_liquido = 0.0

    total_bruto = round(
        total_bruto,
        2
    )

    valor_desconto = round(
        valor_desconto,
        2
    )

    total_liquido = round(
        total_liquido,
        2
    )

    # ======================================================
    # VALIDAR TOTAL PAGO
    # ======================================================

    total_pago = (
        valor_pagamento_1
        + valor_pagamento_2
    )

    total_pago = round(
        total_pago,
        2
    )

    if abs(
        total_pago - total_liquido
    ) > 0.01:

        db.rollback()

        return redirecionar_erro(
            "pagamento_total"
        )

    # ======================================================
    # SALVAR VENDA
    # ======================================================

    try:

        venda = Venda(
            cliente_id=(
                cliente.id
                if cliente
                else None
            ),

            usuario_id=(
                usuario.id
                if usuario
                else None
            ),

            desconto_percentual=(
                desconto_percentual
            ),

            total_bruto=(
                total_bruto
            ),

            total_liquido=(
                total_liquido
            ),

            observacao=(
                observacao.strip()
                if observacao
                else None
            )
        )

        db.add(venda)
        db.flush()

        # ==================================================
        # ITENS DA VENDA
        # ==================================================

        for item in itens_validados:

            produto = item["produto"]

            item_venda = ItemVenda(
                venda_id=venda.id,
                produto_id=produto.id,
                produto_nome=produto.nome,
                quantidade=item["quantidade"],
                preco_unitario=item["preco"]
            )

            db.add(item_venda)

            produto.estoque_atual -= (
                item["quantidade"]
            )

        # ==================================================
        # PAGAMENTO 1
        # ==================================================

        pagamento_1 = Pagamento(
            venda_id=venda.id,
            forma_pagamento=(
                forma_pagamento_1
            ),
            valor=round(
                valor_pagamento_1,
                2
            )
        )

        db.add(pagamento_1)

        # ==================================================
        # PAGAMENTO 2
        # ==================================================

        if forma_pagamento_2:

            pagamento_2 = Pagamento(
                venda_id=venda.id,
                forma_pagamento=(
                    forma_pagamento_2
                ),
                valor=round(
                    valor_pagamento_2,
                    2
                )
            )

            db.add(pagamento_2)

        # ==================================================
        # COMMIT
        # ==================================================

        db.commit()

        return RedirectResponse(
            url=(
                f"/pdv/venda/"
                f"{venda.id}"
                f"?sucesso=ok"
            ),
            status_code=303
        )

    except Exception as erro:

        db.rollback()

        print(
            "ERRO AO FINALIZAR VENDA:",
            erro
        )

        return redirecionar_erro(
            "salvar"
        )


# ==========================================================
# COMPROVANTE
# ==========================================================

@router.get("/venda/{venda_id}")
def comprovante(
    venda_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    venda = (
        db.query(Venda)
        .filter(
            Venda.id == venda_id
        )
        .first()
    )

    if not venda:

        return RedirectResponse(
            url="/pdv/?erro=venda_inexistente",
            status_code=303
        )

    return templates.TemplateResponse(
        request,
        "pdv/comprovante.html",
        {
            "request": request,
            "venda": venda,
            "usuario": usuario
        }
    )


# ==========================================================
# HISTÓRICO
# ==========================================================

@router.get("/historico")
def historico(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):
    vendas = (
        db.query(Venda)
        .order_by(
            Venda.id.desc()
        )
        .limit(100)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "pdv/historico.html",
        {
            "request": request,
            "vendas": vendas,
            "usuario": usuario
        }
    )

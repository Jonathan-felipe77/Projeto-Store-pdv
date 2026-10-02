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

from app.models.venda import (
    Venda,
    ItemVenda
)

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


# ==========================================================
# ERRO
# ==========================================================

def redirecionar_erro(codigo, produto=None):

    if produto:

        return RedirectResponse(
            url=(
                f"/pdv/?erro={codigo}"
                f"&produto={produto}"
            ),
            status_code=303
        )

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
            Produto.nome.asc()
        )

        .all()
    )


    clientes = (

        db.query(Cliente)

        .order_by(
            Cliente.nome.asc()
        )

        .all()
    )


    return templates.TemplateResponse(

        request=request,

        name="pdv/index.html",

        context={

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

    usuario=Depends(
        get_usuario_logado
    )

):

    # ======================================================
    # 1. CARRINHO
    # ======================================================

    try:

        carrinho = json.loads(
            carrinho_json
        )

    except Exception as erro:

        print(
            "ERRO JSON:",
            repr(erro)
        )

        return redirecionar_erro(
            "json"
        )


    if not isinstance(
        carrinho,
        list
    ):

        return redirecionar_erro(
            "vazio"
        )


    if len(carrinho) == 0:

        return redirecionar_erro(
            "vazio"
        )


    # ======================================================
    # 2. CLIENTE
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


        if hasattr(
            cliente,
            "ativo"
        ):

            if not cliente.ativo:

                return redirecionar_erro(
                    "cliente_inexistente"
                )


        desconto_percentual = float(

            getattr(
                cliente,
                "desconto_percentual",
                0
            )
            or 0

        )


        desconto_percentual = max(
            0.0,
            min(
                100.0,
                desconto_percentual
            )
        )


    # ======================================================
    # 3. PAGAMENTOS
    # ======================================================

    forma_pagamento_1 = (

        forma_pagamento_1
        or ""

    ).strip().lower()


    forma_pagamento_2 = (

        forma_pagamento_2
        or ""

    ).strip().lower()


    # ======================================================
    # PRIMEIRA FORMA
    # ======================================================

    if (

        forma_pagamento_1
        not in FORMAS_PAGAMENTO_VALIDAS

    ):

        return redirecionar_erro(
            "pagamento_invalido"
        )


    # ======================================================
    # VALORES
    # ======================================================

    try:

        valor_pagamento_1 = round(
            float(
                valor_pagamento_1 or 0
            ),
            2
        )


        valor_pagamento_2 = round(
            float(
                valor_pagamento_2 or 0
            ),
            2
        )

    except (
        ValueError,
        TypeError
    ):

        return redirecionar_erro(
            "pagamento_valor"
        )


    if valor_pagamento_1 <= 0:

        return redirecionar_erro(
            "pagamento_valor"
        )


    # ======================================================
    # SEGUNDA FORMA
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
    # 4. PRODUTOS
    # ======================================================

    total_bruto = 0.0

    itens_validados = []


    for item in carrinho:

        try:

            produto_id = int(

                item.get(
                    "id",
                    item.get(
                        "produto_id"
                    )
                )

            )


            quantidade = int(

                item.get(
                    "quantidade"
                )

            )

        except Exception as erro:

            print(
                "ERRO ITEM:",
                repr(erro)
            )

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


        estoque = int(
            produto.estoque_atual or 0
        )


        if quantidade > estoque:

            db.rollback()

            return redirecionar_erro(
                "estoque",
                produto.nome
            )


        preco = round(

            float(
                produto.preco or 0
            ),

            2

        )


        subtotal = round(

            preco * quantidade,

            2

        )


        total_bruto += subtotal


        itens_validados.append({

            "produto": produto,

            "quantidade": quantidade,

            "preco": preco,

            "subtotal": subtotal

        })


    # ======================================================
    # 5. TOTAIS
    # ======================================================

    total_bruto = round(
        total_bruto,
        2
    )


    valor_desconto = round(

        total_bruto
        * desconto_percentual
        / 100,

        2

    )


    total_liquido = round(

        total_bruto
        - valor_desconto,

        2

    )


    if total_liquido < 0:

        total_liquido = 0.0


    # ======================================================
    # 6. TOTAL PAGO
    # ======================================================

    total_pago = round(

        valor_pagamento_1
        +
        valor_pagamento_2,

        2

    )


    print()
    print("=" * 70)
    print("FINALIZANDO VENDA")
    print("=" * 70)
    print("Total bruto:", total_bruto)
    print("Desconto:", valor_desconto)
    print("Total líquido:", total_liquido)
    print("Forma 1:", forma_pagamento_1)
    print("Valor 1:", valor_pagamento_1)
    print("Forma 2:", forma_pagamento_2)
    print("Valor 2:", valor_pagamento_2)
    print("Total pago:", total_pago)
    print("=" * 70)


    if abs(

        total_pago
        -
        total_liquido

    ) > 0.01:

        db.rollback()

        return redirecionar_erro(
            "pagamento_total"
        )


    # ======================================================
    # 7. USUÁRIO
    # ======================================================

    if isinstance(
        usuario,
        dict
    ):

        usuario_id = usuario.get(
            "id"
        )

    else:

        usuario_id = getattr(
            usuario,
            "id",
            None
        )


    # ======================================================
    # 8. SALVAR VENDA
    # ======================================================

    try:

        venda = Venda(

            cliente_id=(

                cliente.id

                if cliente

                else None

            ),

            usuario_id=(
                usuario_id
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

                if (

                    observacao
                    and
                    observacao.strip()

                )

                else None

            )

        )


        db.add(
            venda
        )


        db.flush()


        print(
            "VENDA CRIADA:",
            venda.id
        )


        # ==================================================
        # 9. ITENS
        # ==================================================

        for item in itens_validados:

            produto = item[
                "produto"
            ]


            quantidade = item[
                "quantidade"
            ]


            preco = item[
                "preco"
            ]


            novo_item = ItemVenda(

                venda_id=
                    venda.id,

                produto_id=
                    produto.id,

                produto_nome=
                    produto.nome,

                quantidade=
                    quantidade,

                preco_unitario=
                    preco

            )


            db.add(
                novo_item
            )


            produto.estoque_atual = (

                int(
                    produto.estoque_atual
                    or 0
                )
                -
                quantidade

            )


        # ==================================================
        # 10. PAGAMENTO 1
        # ==================================================

        pagamento_1 = Pagamento(

            venda_id=
                venda.id,

            forma_pagamento=
                forma_pagamento_1,

            valor=
                valor_pagamento_1

        )


        db.add(
            pagamento_1
        )


        # ==================================================
        # 11. PAGAMENTO 2
        # ==================================================

        if (

            forma_pagamento_2
            and
            valor_pagamento_2 > 0

        ):

            pagamento_2 = Pagamento(

                venda_id=
                    venda.id,

                forma_pagamento=
                    forma_pagamento_2,

                valor=
                    valor_pagamento_2

            )


            db.add(
                pagamento_2
            )


        # ==================================================
        # 12. COMMIT
        # ==================================================

        db.commit()


        print(
            "VENDA SALVA COM SUCESSO"
        )

        print(
            "ID:",
            venda.id
        )

        print("=" * 70)
        print()


        return RedirectResponse(

            url=(
                f"/pdv/venda/"
                f"{venda.id}"
                "?sucesso=ok"
            ),

            status_code=303

        )


    except Exception as erro:

        db.rollback()

        print()
        print("=" * 70)
        print("ERRO AO SALVAR VENDA")
        print("=" * 70)

        print(
            "TIPO:",
            type(erro).__name__
        )

        print(
            "MENSAGEM:",
            str(erro)
        )

        print(
            "REPR:",
            repr(erro)
        )

        print("=" * 70)
        print()


        return redirecionar_erro(
            "salvar"
        )


# ==========================================================
# COMPROVANTE
# ==========================================================

@router.get(
    "/venda/{venda_id}"
)
def comprovante(

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
            Venda.id == venda_id
        )

        .first()

    )


    if not venda:

        return redirecionar_erro(
            "venda_inexistente"
        )


    return templates.TemplateResponse(

        request=request,

        name="pdv/comprovante.html",

        context={

            "request":
                request,

            "venda":
                venda,

            "usuario":
                usuario

        }

    )


# ==========================================================
# HISTÓRICO
# ==========================================================

@router.get(
    "/historico"
)
def historico(

    request: Request,

    db: Session = Depends(
        get_db
    ),

    usuario=Depends(
        get_usuario_logado
    )

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

        request=request,

        name="pdv/historico.html",

        context={

            "request":
                request,

            "vendas":
                vendas,

            "usuario":
                usuario

        }

    )
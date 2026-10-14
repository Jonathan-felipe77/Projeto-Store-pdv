import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_usuario_logado
from app.database import get_db
from app.models.cliente import Cliente
from app.models.pagamento import Pagamento
from app.models.produto import Produto
from app.models.venda import ItemVenda, Venda

router = APIRouter(prefix="/pdv", tags=["PDV"])
templates = Jinja2Templates(directory="app/templates")
FORMAS_PAGAMENTO_VALIDAS = {"dinheiro", "pix", "debito", "credito"}
CENTAVO = Decimal("0.01")


def dinheiro(valor):
    """Converte e arredonda valores monetários para duas casas decimais."""
    try:
        return Decimal(str(valor if valor is not None else 0)).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("valor monetário inválido")


def redirecionar_erro(codigo, produto=None):
    if produto:
        from urllib.parse import quote
        return RedirectResponse(
            url=f"/pdv/?erro={codigo}&produto={quote(str(produto))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/pdv/?erro={codigo}", status_code=303)


@router.get("/")
def pdv(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    produtos = (
        db.query(Produto)
        .filter(Produto.ativo == True, Produto.estoque_atual > 0)  # noqa: E712
        .order_by(Produto.nome.asc())
        .all()
    )
    clientes = db.query(Cliente).order_by(Cliente.nome.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="pdv/index.html",
        context={"request": request, "produtos": produtos, "clientes": clientes, "usuario": usuario},
    )


@router.post("/finalizar")
def finalizar_venda(
    request: Request,
    carrinho_json: str = Form(...),
    cliente_id: int = Form(0),
    observacao: str = Form(""),
    forma_pagamento_1: str = Form(""),
    valor_pagamento_1: str = Form("0"),
    forma_pagamento_2: str = Form(""),
    valor_pagamento_2: str = Form("0"),
    desconto_manual_tipo: str = Form("percentual"),
    desconto_manual_valor: str = Form("0"),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    # 1. Validar o carrinho recebido.
    try:
        carrinho = json.loads(carrinho_json)
    except (json.JSONDecodeError, TypeError):
        return redirecionar_erro("json")
    if not isinstance(carrinho, list) or not carrinho:
        return redirecionar_erro("vazio")

    # 2. Validar cliente e desconto cadastrado. O desconto de associado só
    # é aplicado se o cliente estiver marcado como associado.
    cliente = None
    desconto_percentual = Decimal("0.00")
    if cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente or (hasattr(cliente, "ativo") and not cliente.ativo):
            return redirecionar_erro("cliente_inexistente")
        if bool(getattr(cliente, "is_associado", False)):
            try:
                desconto_percentual = Decimal(
                    str(getattr(cliente, "desconto_percentual", 0) or 0)
                )
            except (InvalidOperation, ValueError, TypeError):
                desconto_percentual = Decimal("0")
        desconto_percentual = max(Decimal("0"), min(Decimal("100"), desconto_percentual))

    # 3. Validar tipo e valor do desconto manual enviado pelo pdv/index.html.
    desconto_manual_tipo = (desconto_manual_tipo or "percentual").strip().lower()
    if desconto_manual_tipo not in {"percentual", "valor"}:
        return redirecionar_erro("desconto_invalido")
    try:
        entrada_desconto_manual = dinheiro(desconto_manual_valor)
    except ValueError:
        return redirecionar_erro("desconto_invalido")
    if entrada_desconto_manual < 0:
        return redirecionar_erro("desconto_invalido")
    if desconto_manual_tipo == "percentual" and entrada_desconto_manual > 100:
        return redirecionar_erro("desconto_invalido")

    # 4. Validar formas e valores de pagamento (aceita campos enviados como texto).
    forma_pagamento_1 = (forma_pagamento_1 or "").strip().lower()
    forma_pagamento_2 = (forma_pagamento_2 or "").strip().lower()
    if forma_pagamento_1 not in FORMAS_PAGAMENTO_VALIDAS:
        return redirecionar_erro("pagamento_invalido")
    try:
        valor_pagamento_1_dec = dinheiro(valor_pagamento_1)
        valor_pagamento_2_dec = dinheiro(valor_pagamento_2)
    except ValueError:
        return redirecionar_erro("pagamento_valor")
    if valor_pagamento_1_dec < 0 or valor_pagamento_2_dec < 0:
        return redirecionar_erro("pagamento_valor")
    if forma_pagamento_2:
        if forma_pagamento_2 not in FORMAS_PAGAMENTO_VALIDAS:
            return redirecionar_erro("pagamento_invalido")
    elif valor_pagamento_2_dec != 0:
        return redirecionar_erro("pagamento_valor")

    # 5. Conferir produtos, preços e estoque no banco (nunca confiar nos preços do navegador).
    total_bruto_dec = Decimal("0.00")
    itens_validados = []
    quantidade_por_produto = {}
    produtos_por_id = {}

    for item in carrinho:
        if not isinstance(item, dict):
            return redirecionar_erro("item_invalido")
        try:
            produto_id = int(item.get("id", item.get("produto_id")))
            quantidade = int(item.get("quantidade"))
        except (ValueError, TypeError):
            return redirecionar_erro("item_invalido")
        if produto_id <= 0:
            return redirecionar_erro("item_invalido")
        if quantidade <= 0:
            return redirecionar_erro("quantidade")
        produto = produtos_por_id.get(produto_id)
        if produto is None:
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if produto is None or not produto.ativo:
                return redirecionar_erro("produto_inexistente")
            produtos_por_id[produto_id] = produto
        quantidade_por_produto[produto_id] = quantidade_por_produto.get(produto_id, 0) + quantidade
        if quantidade_por_produto[produto_id] > int(produto.estoque_atual or 0):
            return redirecionar_erro("estoque", produto.nome)
        try:
            preco = dinheiro(produto.preco or 0)
        except ValueError:
            return redirecionar_erro("produto_inexistente")
        subtotal_item = (preco * quantidade).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        tamanho = str(item.get("tamanho") or "Único").strip() or "Único"
        nome_item = produto.nome
        if tamanho.lower() != "único" and tamanho.lower() != "unico":
            nome_item = f"{produto.nome} (Tamanho {tamanho})"
        itens_validados.append({
            "produto": produto,
            "quantidade": quantidade,
            "preco": preco,
            "subtotal": subtotal_item,
            "nome": nome_item,
        })
        total_bruto_dec += subtotal_item

    total_bruto_dec = total_bruto_dec.quantize(CENTAVO, rounding=ROUND_HALF_UP)

    # 6. Calcular ambos os descontos no servidor, limitando ao valor disponível.
    desconto_cliente_valor_dec = (total_bruto_dec * desconto_percentual / Decimal("100")).quantize(
        CENTAVO, rounding=ROUND_HALF_UP
    )
    desconto_cliente_valor_dec = min(total_bruto_dec, desconto_cliente_valor_dec)
    base_desconto_manual = max(Decimal("0.00"), total_bruto_dec - desconto_cliente_valor_dec)
    if desconto_manual_tipo == "valor":
        desconto_manual_valor_dec = min(base_desconto_manual, entrada_desconto_manual)
    else:
        desconto_manual_valor_dec = (base_desconto_manual * entrada_desconto_manual / Decimal("100")).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )
        desconto_manual_valor_dec = min(base_desconto_manual, desconto_manual_valor_dec)
    desconto_valor_dec = min(
        total_bruto_dec,
        desconto_cliente_valor_dec + desconto_manual_valor_dec,
    ).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    total_liquido_dec = max(Decimal("0.00"), total_bruto_dec - desconto_valor_dec).quantize(
        CENTAVO, rounding=ROUND_HALF_UP
    )

    # 7. Validar se a soma dos pagamentos corresponde ao total já descontado.
    total_pago_dec = (valor_pagamento_1_dec + valor_pagamento_2_dec).quantize(CENTAVO)
    if total_liquido_dec == 0:
        if total_pago_dec != 0:
            return redirecionar_erro("pagamento_total")
    else:
        if valor_pagamento_1_dec <= 0:
            return redirecionar_erro("pagamento_valor")
        if forma_pagamento_2 and valor_pagamento_2_dec <= 0:
            return redirecionar_erro("pagamento_valor")
        if abs(total_pago_dec - total_liquido_dec) > CENTAVO:
            return redirecionar_erro("pagamento_total")

    # 8. Obter operador.
    usuario_id = usuario.get("id") if isinstance(usuario, dict) else getattr(usuario, "id", None)

    # 9. Salvar venda, itens, pagamentos e estoque em uma única transação.
    try:
        # Mantém compatibilidade com o modelo Venda existente do projeto.
        # O valor do desconto sempre pode ser obtido por total_bruto - total_liquido;
        # por isso não exigimos que exista uma coluna adicional desconto_valor.
        dados_venda = {
            "cliente_id": cliente.id if cliente else None,
            "usuario_id": usuario_id,
            "desconto_percentual": float(desconto_percentual),
            "total_bruto": float(total_bruto_dec),
            "total_liquido": float(total_liquido_dec),
            "observacao": observacao.strip() if observacao and observacao.strip() else None,
        }
        # Não passamos desconto_valor ao construtor: projetos antigos podem não ter
        # esse campo mapeado. O valor é recuperado no comprovante por bruto - líquido.
        venda = Venda(**dados_venda)
        db.add(venda)
        db.flush()

        for item in itens_validados:
            produto = item["produto"]
            db.add(ItemVenda(
                venda_id=venda.id,
                produto_id=produto.id,
                produto_nome=item["nome"],
                quantidade=item["quantidade"],
                preco_unitario=float(item["preco"]),
            ))
            produto.estoque_atual = int(produto.estoque_atual or 0) - item["quantidade"]

        if total_liquido_dec > 0:
            db.add(Pagamento(
                venda_id=venda.id,
                forma_pagamento=forma_pagamento_1,
                valor=float(valor_pagamento_1_dec),
            ))
            if forma_pagamento_2 and valor_pagamento_2_dec > 0:
                db.add(Pagamento(
                    venda_id=venda.id,
                    forma_pagamento=forma_pagamento_2,
                    valor=float(valor_pagamento_2_dec),
                ))

        db.commit()
        return RedirectResponse(url=f"/pdv/venda/{venda.id}?sucesso=ok", status_code=303)
    except Exception as erro:
        import traceback
        db.rollback()
        print("ERRO AO SALVAR VENDA:", type(erro).__name__, str(erro))
        traceback.print_exc()
        return redirecionar_erro("salvar")


@router.get("/venda/{venda_id}")
def comprovante(
    venda_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    venda = db.query(Venda).filter(Venda.id == venda_id).first()
    if not venda:
        return redirecionar_erro("venda_inexistente")
    return templates.TemplateResponse(
        request=request,
        name="pdv/comprovante.html",
        context={"request": request, "venda": venda, "usuario": usuario},
    )


@router.get("/historico")
def historico(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    vendas = db.query(Venda).order_by(Venda.id.desc()).limit(100).all()
    return templates.TemplateResponse(
        request=request,
        name="pdv/historico.html",
        context={"request": request, "vendas": vendas, "usuario": usuario},
    )

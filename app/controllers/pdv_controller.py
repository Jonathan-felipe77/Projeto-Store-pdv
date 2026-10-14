"""Rotas do ponto de venda (PDV): vendas, pagamentos e comprovantes."""

import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.auth import get_usuario_logado
from app.database import get_db
from app.models.cliente import Cliente
from app.models.pagamento import Pagamento
from app.models.produto import Produto
from app.models.venda import ItemVenda, Venda

router = APIRouter(prefix="/pdv", tags=["PDV"])
templates = Jinja2Templates(directory="app/templates")

FORMAS_PAGAMENTO_VALIDAS = {"dinheiro", "pix", "debito", "credito"}


def redirecionar_erro(codigo: str, produto: str | None = None):
    url = f"/pdv/?erro={quote(codigo)}"
    if produto:
        url += f"&produto={quote(produto)}"
    return RedirectResponse(url=url, status_code=303)


def _id_usuario(usuario):
    """O JWT usado pelo projeto retorna um dicionário com id/sub/role."""
    if isinstance(usuario, dict):
        return usuario.get("id")
    return getattr(usuario, "id", None)


@router.get("/")
def pdv(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    produtos = (
        db.query(Produto)
        .filter(Produto.ativo.is_(True), Produto.estoque_atual > 0)
        .order_by(Produto.nome.asc())
        .all()
    )
    clientes = (
        db.query(Cliente)
        .filter(Cliente.ativo.is_(True))
        .order_by(Cliente.nome.asc())
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="pdv/index.html",
        context={
            "request": request,
            "produtos": produtos,
            "clientes": clientes,
            "usuario": usuario,
        },
    )


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
    desconto_manual_tipo: str = Form("percentual"),
    desconto_manual_valor: float = Form(0.0),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    # 1. Carrinho recebido do navegador: aceitar apenas uma lista válida.
    try:
        carrinho = json.loads(carrinho_json)
    except (TypeError, json.JSONDecodeError):
        return redirecionar_erro("json")

    if not isinstance(carrinho, list) or not carrinho:
        return redirecionar_erro("vazio")

    # 2. Cliente e desconto automático previamente configurado no cadastro.
    cliente = None
    desconto_cliente_pct = 0.0
    if cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente or not cliente.ativo:
            return redirecionar_erro("cliente_inexistente")
        desconto_cliente_pct = (
            float(cliente.desconto_percentual or 0.0)
            if cliente.is_associado else 0.0
        )
        if not 0 <= desconto_cliente_pct <= 100:
            return redirecionar_erro("desconto_limite")

    # 3. Validar as duas formas de pagamento.
    forma_pagamento_1 = (forma_pagamento_1 or "").strip().lower()
    forma_pagamento_2 = (forma_pagamento_2 or "").strip().lower()
    try:
        valor_pagamento_1 = round(float(valor_pagamento_1 or 0), 2)
        valor_pagamento_2 = round(float(valor_pagamento_2 or 0), 2)
        desconto_manual_valor = float(desconto_manual_valor or 0)
    except (TypeError, ValueError):
        return redirecionar_erro("pagamento_valor")

    if forma_pagamento_1 not in FORMAS_PAGAMENTO_VALIDAS:
        return redirecionar_erro("pagamento_invalido")
    if valor_pagamento_1 < 0 or valor_pagamento_2 < 0:
        return redirecionar_erro("pagamento_valor")

    if forma_pagamento_2:
        if forma_pagamento_2 not in FORMAS_PAGAMENTO_VALIDAS:
            return redirecionar_erro("pagamento_invalido")
        if forma_pagamento_2 == forma_pagamento_1:
            return redirecionar_erro("pagamentos_iguais")
    else:
        valor_pagamento_2 = 0.0

    # 4. Recalcular os itens usando preços do banco, nunca preços do navegador.
    total_bruto = 0.0
    itens_validados = []
    produtos_vistos = set()

    for item in carrinho:
        if not isinstance(item, dict):
            return redirecionar_erro("item_invalido")
        try:
            produto_id = int(item.get("id", item.get("produto_id")))
            quantidade = int(item.get("quantidade"))
        except (TypeError, ValueError):
            return redirecionar_erro("item_invalido")

        if quantidade <= 0:
            return redirecionar_erro("quantidade")
        # Evita um mesmo produto repetido com quantidades que somadas superem o estoque.
        if produto_id in produtos_vistos:
            return redirecionar_erro("item_duplicado")
        produtos_vistos.add(produto_id)

        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if not produto or not produto.ativo:
            return redirecionar_erro("produto_inexistente")

        estoque = int(produto.estoque_atual or 0)
        if quantidade > estoque:
            return redirecionar_erro("estoque", produto.nome)

        preco = round(float(produto.preco or 0), 2)
        if preco < 0:
            return redirecionar_erro("preco_invalido")
        subtotal_item = round(preco * quantidade, 2)
        total_bruto = round(total_bruto + subtotal_item, 2)
        itens_validados.append({
            "produto": produto,
            "quantidade": quantidade,
            "preco": preco,
        })

    if total_bruto <= 0:
        return redirecionar_erro("total_invalido")

    # 5. Desconto manual (% ou valor fixo em reais).
    desconto_manual_tipo = (desconto_manual_tipo or "percentual").strip().lower()
    if desconto_manual_tipo not in {"percentual", "valor"}:
        return redirecionar_erro("desconto_invalido")
    if desconto_manual_valor < 0:
        return redirecionar_erro("desconto_limite")
    if desconto_manual_tipo == "percentual" and desconto_manual_valor > 100:
        return redirecionar_erro("desconto_limite")

    desconto_cliente_valor = round(total_bruto * desconto_cliente_pct / 100, 2)
    if desconto_manual_tipo == "percentual":
        desconto_manual_valor = round(total_bruto * desconto_manual_valor / 100, 2)
    else:
        desconto_manual_valor = round(desconto_manual_valor, 2)

    desconto_total = round(desconto_cliente_valor + desconto_manual_valor, 2)
    if desconto_total > total_bruto + 0.001:
        return redirecionar_erro("desconto_limite")

    total_liquido = round(max(0.0, total_bruto - desconto_total), 2)
    # A versão do banco já armazena subtotal e total líquido. Guardamos a porcentagem
    # equivalente para manter compatibilidade e a propriedade desconto_valor retorna
    # exatamente total_bruto - total_liquido, que representa o desconto em reais.
    desconto_percentual_salvo = (
        round((desconto_total / total_bruto) * 100, 6)
        if total_bruto > 0 else 0.0
    )

    # 6. A soma deve coincidir com o total final, inclusive em vendas sem desconto.
    total_pago = round(valor_pagamento_1 + valor_pagamento_2, 2)
    if total_liquido > 0 and valor_pagamento_1 <= 0:
        return redirecionar_erro("pagamento_valor")
    if forma_pagamento_2 and total_liquido > 0 and valor_pagamento_2 <= 0:
        return redirecionar_erro("pagamento_valor")
    if abs(total_pago - total_liquido) > 0.009:
        return redirecionar_erro("pagamento_total")

    # 7. Gravar venda, itens, baixar estoque e registrar pagamentos na mesma transação.
    try:
        venda = Venda(
            cliente_id=cliente.id if cliente else None,
            usuario_id=_id_usuario(usuario),
            desconto_percentual=desconto_percentual_salvo,
            total_bruto=total_bruto,
            total_liquido=total_liquido,
            observacao=observacao.strip() or None,
        )
        db.add(venda)
        db.flush()

        for item in itens_validados:
            produto = item["produto"]
            db.add(ItemVenda(
                venda_id=venda.id,
                produto_id=produto.id,
                produto_nome=produto.nome,
                quantidade=item["quantidade"],
                preco_unitario=item["preco"],
            ))
            produto.estoque_atual = int(produto.estoque_atual or 0) - item["quantidade"]

        db.add(Pagamento(
            venda_id=venda.id,
            forma_pagamento=forma_pagamento_1,
            valor=valor_pagamento_1,
        ))

        if forma_pagamento_2:
            db.add(Pagamento(
                venda_id=venda.id,
                forma_pagamento=forma_pagamento_2,
                valor=valor_pagamento_2,
            ))

        db.commit()
        db.refresh(venda)
        return RedirectResponse(
            url=f"/pdv/venda/{venda.id}?sucesso=ok",
            status_code=303,
        )
    except Exception as erro:
        db.rollback()
        print(f"[ERRO PDV] {type(erro).__name__}: {erro}")
        return redirecionar_erro("salvar")


@router.get("/venda/{venda_id}")
def comprovante(
    venda_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    venda = (
        db.query(Venda)
        .options(
            joinedload(Venda.cliente),
            joinedload(Venda.usuario),
            joinedload(Venda.itens),
            joinedload(Venda.pagamentos),
        )
        .filter(Venda.id == venda_id)
        .first()
    )
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
    vendas = (
        db.query(Venda)
        .options(
            joinedload(Venda.cliente),
            joinedload(Venda.usuario),
            joinedload(Venda.itens),
            joinedload(Venda.pagamentos),
        )
        .order_by(Venda.id.desc())
        .limit(100)
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="pdv/historico.html",
        context={"request": request, "vendas": vendas, "usuario": usuario},
    )

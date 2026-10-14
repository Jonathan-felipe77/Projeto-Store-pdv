"""Rotas do ponto de venda (PDV): vendas, pagamentos e comprovantes."""

import json
<<<<<<< HEAD
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
=======
from urllib.parse import quote
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
<<<<<<< HEAD
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
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a


@router.get("/")
def pdv(
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    produtos = (
        db.query(Produto)
<<<<<<< HEAD
        .filter(Produto.ativo == True, Produto.estoque_atual > 0)  # noqa: E712
        .order_by(Produto.nome.asc())
        .all()
    )
    clientes = db.query(Cliente).order_by(Cliente.nome.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="pdv/index.html",
        context={"request": request, "produtos": produtos, "clientes": clientes, "usuario": usuario},
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a
    )


@router.post("/finalizar")
def finalizar_venda(
    request: Request,
    carrinho_json: str = Form(...),
    cliente_id: int = Form(0),
    observacao: str = Form(""),
    forma_pagamento_1: str = Form(""),
<<<<<<< HEAD
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
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a

    for item in carrinho:
        if not isinstance(item, dict):
            return redirecionar_erro("item_invalido")
        try:
            produto_id = int(item.get("id", item.get("produto_id")))
            quantidade = int(item.get("quantidade"))
<<<<<<< HEAD
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
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a
        itens_validados.append({
            "produto": produto,
            "quantidade": quantidade,
            "preco": preco,
<<<<<<< HEAD
            "subtotal": subtotal_item,
            "nome": nome_item,
=======
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a
        })
        total_bruto_dec += subtotal_item

<<<<<<< HEAD
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
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a
        db.add(venda)
        db.flush()

        for item in itens_validados:
            produto = item["produto"]
            db.add(ItemVenda(
                venda_id=venda.id,
                produto_id=produto.id,
<<<<<<< HEAD
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
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a
        return redirecionar_erro("salvar")


@router.get("/venda/{venda_id}")
def comprovante(
    venda_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
<<<<<<< HEAD
    venda = db.query(Venda).filter(Venda.id == venda_id).first()
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a
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
<<<<<<< HEAD
    vendas = db.query(Venda).order_by(Venda.id.desc()).limit(100).all()
=======
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
>>>>>>> cf0932eae84a6e7463f4f85ed0b04252e3bfd15a
    return templates.TemplateResponse(
        request=request,
        name="pdv/historico.html",
        context={"request": request, "vendas": vendas, "usuario": usuario},
    )

# controllers/produto_controller.py
# CRUD de produtos - AAPM SENAI

import os
import shutil

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    UploadFile,
    File
)

from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.produto import Produto
from app.models.categoria import Categoria
from app.auth import get_usuario_logado, get_admin


# ============================================================
# CONFIGURAÇÃO
# ============================================================

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"]
)

templates = Jinja2Templates(
    directory="app/templates"
)

UPLOAD_DIR = "app/static/uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ============================================================
# FUNÇÃO PARA BUSCAR CATEGORIAS
# ============================================================

def buscar_categorias(db: Session):
    """
    Busca todas as categorias cadastradas no banco.
    Ordena pelo nome para aparecer organizado no formulário.
    """
    return db.query(Categoria).order_by(
        Categoria.nome.asc()
    ).all()


# ============================================================
# LISTAGEM DE PRODUTOS
# ============================================================

@router.get("/")
def listar_produtos(
    request: Request,
    busca: str = "",
    categoria_id: int = 0,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):

    query = db.query(Produto).filter(
        Produto.ativo == True
    )

    # Busca pelo nome
    if busca:
        query = query.filter(
            Produto.nome.ilike(f"%{busca}%")
        )

    # Filtro por categoria
    if categoria_id:
        query = query.filter(
            Produto.categoria_id == categoria_id
        )

    produtos = query.order_by(
        Produto.nome.asc()
    ).all()

    # BUSCA AS CATEGORIAS DO BANCO
    categorias = buscar_categorias(db)

    return templates.TemplateResponse(
        request,
        "produtos/index.html",
        {
            "request": request,
            "usuario": usuario,
            "produtos": produtos,
            "categorias": categorias,
            "busca": busca,
            "categoria_id": categoria_id
        }
    )


# ============================================================
# FORMULÁRIO - NOVO PRODUTO
# ============================================================

@router.get("/novo")
def form_novo_produto(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    # BUSCA TODAS AS CATEGORIAS
    categorias = buscar_categorias(db)

    return templates.TemplateResponse(
        request,
        "produtos/form.html",
        {
            "request": request,
            "usuario": admin,
            "editando": None,
            "categorias": categorias,
            "valores": {}
        }
    )


# ============================================================
# CADASTRAR PRODUTO
# ============================================================

@router.post("/novo")
async def criar_produto(
    request: Request,

    nome: str = Form(...),

    preco: float = Form(...),

    estoque_atual: int = Form(...),

    categoria_id: int = Form(0),

    imagem: UploadFile | None = File(None),

    db: Session = Depends(get_db),

    admin=Depends(get_admin)
):

    # Busca novamente as categorias
    categorias = buscar_categorias(db)

    # ========================================================
    # VERIFICA SE O PRODUTO JÁ EXISTE
    # ========================================================

    produto_existente = db.query(Produto).filter(
        Produto.nome.ilike(nome)
    ).first()

    if produto_existente:

        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": None,
                "categorias": categorias,
                "erro": "Já existe um produto com este nome.",
                "valores": {
                    "nome": nome,
                    "preco": preco,
                    "estoque_atual": estoque_atual,
                    "categoria_id": categoria_id
                }
            },
            status_code=400
        )

    # ========================================================
    # VERIFICA A CATEGORIA
    # ========================================================

    categoria = None

    if categoria_id:

        categoria = db.query(Categoria).filter(
            Categoria.id == categoria_id
        ).first()

        if not categoria:

            return templates.TemplateResponse(
                request,
                "produtos/form.html",
                {
                    "request": request,
                    "usuario": admin,
                    "editando": None,
                    "categorias": categorias,
                    "erro": "A categoria selecionada não existe.",
                    "valores": {
                        "nome": nome,
                        "preco": preco,
                        "estoque_atual": estoque_atual,
                        "categoria_id": categoria_id
                    }
                },
                status_code=400
            )

    # ========================================================
    # SALVA IMAGEM
    # ========================================================

    imagem_path = await _salvar_imagem(imagem)

    # ========================================================
    # CRIA PRODUTO
    # ========================================================

    produto = Produto(
        nome=nome,
        preco=preco,
        estoque_atual=estoque_atual,
        categoria_id=categoria_id if categoria else None,
        imagem_path=imagem_path
    )

    db.add(produto)

    db.commit()

    db.refresh(produto)

    # ========================================================
    # VOLTA PARA LISTAGEM
    # ========================================================

    return RedirectResponse(
        url="/produtos?criado=ok",
        status_code=302
    )


# ============================================================
# CHECKOUT
# ============================================================

@router.get(
    "/checkout",
    response_class=HTMLResponse
)
def checkout(
    request: Request,
    usuario=Depends(get_usuario_logado)
):

    return templates.TemplateResponse(
        request,
        "produtos/checkout.html",
        {
            "request": request,
            "usuario": usuario
        }
    )


# ============================================================
# DETALHE DO PRODUTO
# ============================================================

@router.get("/{produto_id}")
def detalhe_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado)
):

    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.ativo == True
    ).first()

    if not produto:

        return RedirectResponse(
            url="/produtos",
            status_code=302
        )

    return templates.TemplateResponse(
        request,
        "produtos/detalhe.html",
        {
            "request": request,
            "usuario": usuario,
            "produto": produto
        }
    )


# ============================================================
# FORMULÁRIO - EDITAR PRODUTO
# ============================================================

@router.get("/{produto_id}/editar")
def form_editar_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    produto = db.query(Produto).filter(
        Produto.id == produto_id
    ).first()

    # BUSCA AS CATEGORIAS
    categorias = buscar_categorias(db)

    if not produto:

        return RedirectResponse(
            url="/produtos",
            status_code=302
        )

    return templates.TemplateResponse(
        request,
        "produtos/form.html",
        {
            "request": request,
            "usuario": admin,
            "editando": produto,
            "categorias": categorias,
            "valores": {}
        }
    )


# ============================================================
# EDITAR PRODUTO
# ============================================================

@router.post("/{produto_id}/editar")
async def editar_produto(
    produto_id: int,

    request: Request,

    nome: str = Form(...),

    preco: float = Form(...),

    estoque_atual: int = Form(...),

    categoria_id: int = Form(0),

    imagem: UploadFile | None = File(None),

    db: Session = Depends(get_db),

    admin=Depends(get_admin)
):

    produto = db.query(Produto).filter(
        Produto.id == produto_id
    ).first()

    # Busca categorias
    categorias = buscar_categorias(db)

    if not produto:

        return RedirectResponse(
            url="/produtos",
            status_code=302
        )

    # ========================================================
    # VERIFICA NOME DUPLICADO
    # ========================================================

    conflito = db.query(Produto).filter(
        Produto.nome.ilike(nome),
        Produto.id != produto_id
    ).first()

    if conflito:

        return templates.TemplateResponse(
            request,
            "produtos/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": produto,
                "categorias": categorias,
                "erro": "Já existe outro produto com este nome."
            },
            status_code=400
        )

    # ========================================================
    # VERIFICA CATEGORIA
    # ========================================================

    categoria = None

    if categoria_id:

        categoria = db.query(Categoria).filter(
            Categoria.id == categoria_id
        ).first()

        if not categoria:

            return templates.TemplateResponse(
                request,
                "produtos/form.html",
                {
                    "request": request,
                    "usuario": admin,
                    "editando": produto,
                    "categorias": categorias,
                    "erro": "A categoria selecionada não existe."
                },
                status_code=400
            )

    # ========================================================
    # NOVA IMAGEM
    # ========================================================

    nova_imagem_path = await _salvar_imagem(imagem)

    if nova_imagem_path:

        _remover_imagem(
            produto.imagem_path
        )

        produto.imagem_path = nova_imagem_path

    # ========================================================
    # ATUALIZA PRODUTO
    # ========================================================

    produto.nome = nome

    produto.preco = preco

    produto.estoque_atual = estoque_atual

    produto.categoria_id = (
        categoria_id if categoria else None
    )

    db.commit()

    db.refresh(produto)

    return RedirectResponse(
        url=f"/produtos/{produto_id}?editado=ok",
        status_code=302
    )


# ============================================================
# DESATIVAR PRODUTO
# ============================================================

@router.post("/{produto_id}/desativar")
def desativar_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    produto = db.query(Produto).filter(
        Produto.id == produto_id
    ).first()

    if produto:

        produto.ativo = False

        db.commit()

    return RedirectResponse(
        url="/produtos?desativado=ok",
        status_code=302
    )


# ============================================================
# SALVAR IMAGEM
# ============================================================

async def _salvar_imagem(
    imagem: UploadFile | None
) -> str | None:

    if not imagem or not imagem.filename:
        return None

    extensoes_permitidas = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    _, ext = os.path.splitext(
        imagem.filename.lower()
    )

    if ext not in extensoes_permitidas:
        return None

    nome_arquivo = imagem.filename

    caminho_completo = os.path.join(
        UPLOAD_DIR,
        nome_arquivo
    )

    with open(
        caminho_completo,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            imagem.file,
            buffer
        )

    return f"uploads/{nome_arquivo}"


# ============================================================
# REMOVER IMAGEM
# ============================================================

def _remover_imagem(
    imagem_path: str | None
) -> None:

    if not imagem_path:
        return

    caminho = os.path.join(
        "app/static",
        imagem_path
    )

    if os.path.exists(caminho):
        os.remove(caminho)
# app/controllers/categoria_controller.py

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.categoria import Categoria
from app.auth import get_admin


router = APIRouter(
    prefix="/categorias",
    tags=["Categorias"]
)

templates = Jinja2Templates(directory="app/templates")


# ============================================================
# LISTAR CATEGORIAS
# ============================================================

@router.get("/", response_class=HTMLResponse)
def listar_categorias(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):
    categorias = (
        db.query(Categoria)
        .order_by(Categoria.nome)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "categorias/index.html",
        {
            "request": request,
            "usuario": admin,
            "categorias": categorias
        }
    )


# ============================================================
# FORMULÁRIO NOVA CATEGORIA
# ============================================================

@router.get("/nova", response_class=HTMLResponse)
def form_nova_categoria(
    request: Request,
    admin=Depends(get_admin)
):
    return templates.TemplateResponse(
        request,
        "categorias/form.html",
        {
            "request": request,
            "usuario": admin,
            "categoria": None
        }
    )


# ============================================================
# CRIAR CATEGORIA
# ============================================================

@router.post("/nova")
def criar_categoria(
    request: Request,
    nome: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    # Remove espaços desnecessários
    nome = nome.strip()

    # Não permite nome vazio
    if not nome:
        return templates.TemplateResponse(
            request,
            "categorias/form.html",
            {
                "request": request,
                "usuario": admin,
                "categoria": None,
                "erro": "Digite o nome da categoria."
            },
            status_code=400
        )

    # Verifica se já existe
    categoria_existente = (
        db.query(Categoria)
        .filter(Categoria.nome.ilike(nome))
        .first()
    )

    if categoria_existente:
        return templates.TemplateResponse(
            request,
            "categorias/form.html",
            {
                "request": request,
                "usuario": admin,
                "categoria": None,
                "erro": "Essa categoria já está cadastrada.",
                "nome": nome
            },
            status_code=400
        )

    # Cria categoria ATIVA
    categoria = Categoria(
        nome=nome,
        ativo=True
    )

    db.add(categoria)
    db.commit()
    db.refresh(categoria)

    return RedirectResponse(
        url="/categorias?criado=ok",
        status_code=303
    )


# ============================================================
# FORMULÁRIO EDITAR
# ============================================================

@router.get("/{categoria_id}/editar", response_class=HTMLResponse)
def form_editar_categoria(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    categoria = (
        db.query(Categoria)
        .filter(Categoria.id == categoria_id)
        .first()
    )

    if not categoria:
        return RedirectResponse(
            url="/categorias",
            status_code=303
        )

    return templates.TemplateResponse(
        request,
        "categorias/form.html",
        {
            "request": request,
            "usuario": admin,
            "categoria": categoria
        }
    )


# ============================================================
# EDITAR CATEGORIA
# ============================================================

@router.post("/{categoria_id}/editar")
def editar_categoria(
    categoria_id: int,
    request: Request,
    nome: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    nome = nome.strip()

    categoria = (
        db.query(Categoria)
        .filter(Categoria.id == categoria_id)
        .first()
    )

    if not categoria:
        return RedirectResponse(
            url="/categorias",
            status_code=303
        )

    if not nome:
        return templates.TemplateResponse(
            request,
            "categorias/form.html",
            {
                "request": request,
                "usuario": admin,
                "categoria": categoria,
                "erro": "Digite o nome da categoria."
            },
            status_code=400
        )

    # Verifica duplicidade ignorando a própria categoria
    outra_categoria = (
        db.query(Categoria)
        .filter(
            Categoria.nome.ilike(nome),
            Categoria.id != categoria_id
        )
        .first()
    )

    if outra_categoria:
        return templates.TemplateResponse(
            request,
            "categorias/form.html",
            {
                "request": request,
                "usuario": admin,
                "categoria": categoria,
                "erro": "Já existe outra categoria com esse nome."
            },
            status_code=400
        )

    categoria.nome = nome

    db.commit()

    return RedirectResponse(
        url="/categorias?editado=ok",
        status_code=303
    )


# ============================================================
# ATIVAR / DESATIVAR
# ============================================================

@router.post("/{categoria_id}/toggle-ativo")
def toggle_categoria(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    categoria = (
        db.query(Categoria)
        .filter(Categoria.id == categoria_id)
        .first()
    )

    if not categoria:
        return RedirectResponse(
            url="/categorias",
            status_code=303
        )

    # Se está ativa, verifica se possui produtos vinculados
    if categoria.ativo:

        if categoria.produtos:
            return RedirectResponse(
                url="/categorias?erro=vinculo",
                status_code=303
            )

        categoria.ativo = False

    else:
        categoria.ativo = True

    db.commit()

    return RedirectResponse(
        url="/categorias",
        status_code=303
    )
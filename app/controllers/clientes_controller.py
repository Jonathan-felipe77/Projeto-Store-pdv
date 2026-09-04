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

from app.models.cliente import Cliente

from app.auth import get_admin


router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"]
)

templates = Jinja2Templates(
    directory="app/templates"
)


# ============================================================
# LISTAR
# ============================================================

@router.get("/")
def listar_clientes(
    request: Request,
    busca: str = "",
    apenas_associados: bool = False,
    db: Session = Depends(get_db),
    admin=Depends(get_admin)
):

    query = db.query(Cliente)

    if busca:

        texto = busca.strip()

        query = query.filter(
            Cliente.nome.ilike(
                f"%{texto}%"
            )
            |
            Cliente.matricula.ilike(
                f"%{texto}%"
            )
        )

    if apenas_associados:

        query = query.filter(
            Cliente.is_associado == True
        )

    clientes = (
        query
        .order_by(Cliente.nome)
        .all()
    )

    total_associados = (
        db.query(Cliente)
        .filter(
            Cliente.is_associado == True,
            Cliente.ativo == True
        )
        .count()
    )

    return templates.TemplateResponse(
        request=request,
        name="clientes/index.html",
        context={
            "request": request,
            "usuario": admin,
            "clientes": clientes,
            "busca": busca,
            "apenas_associados":
                apenas_associados,
            "total_associados":
                total_associados
        }
    )


# ============================================================
# NOVO
# ============================================================

@router.get("/novo")
def form_novo(
    request: Request,
    admin=Depends(get_admin)
):

    return templates.TemplateResponse(
        request=request,
        name="clientes/form.html",
        context={
            "request": request,
            "usuario": admin,
            "editando": None
        }
    )


# ============================================================
# CRIAR
# ============================================================

@router.post("/novo")
def criar(
    request: Request,

    nome: str = Form(...),

    matricula: str = Form(""),

    telefone: str = Form(""),

    is_associado: bool = Form(False),

    desconto_percentual: float = Form(0.0),

    db: Session = Depends(get_db),

    admin=Depends(get_admin)
):

    nome = nome.strip()

    matricula = matricula.strip()

    telefone = telefone.strip()

    # --------------------------------------------------------
    # DESCONTO
    # --------------------------------------------------------

    try:
        desconto_percentual = float(
            desconto_percentual
        )
    except (TypeError, ValueError):
        desconto_percentual = 0.0

    # Limites
    desconto_percentual = max(
        0.0,
        min(100.0, desconto_percentual)
    )

    desconto_percentual = round(
        desconto_percentual,
        2
    )

    # --------------------------------------------------------
    # NOME
    # --------------------------------------------------------

    if not nome:

        return templates.TemplateResponse(
            request=request,
            name="clientes/form.html",
            context={
                "request": request,
                "usuario": admin,
                "editando": None,
                "erro":
                    "O nome do cliente é obrigatório.",
                "valores": {
                    "nome": nome,
                    "matricula": matricula,
                    "telefone": telefone,
                    "is_associado":
                        is_associado,
                    "desconto_percentual":
                        desconto_percentual
                }
            },
            status_code=400
        )

    # --------------------------------------------------------
    # MATRÍCULA
    # --------------------------------------------------------

    if matricula:

        existente = (
            db.query(Cliente)
            .filter(
                Cliente.matricula ==
                matricula
            )
            .first()
        )

        if existente:

            return templates.TemplateResponse(
                request=request,
                name="clientes/form.html",
                context={
                    "request": request,
                    "usuario": admin,
                    "editando": None,
                    "erro":
                        f"Matrícula {matricula} "
                        "já cadastrada.",
                    "valores": {
                        "nome": nome,
                        "matricula":
                            matricula,
                        "telefone":
                            telefone,
                        "is_associado":
                            is_associado,
                        "desconto_percentual":
                            desconto_percentual
                    }
                },
                status_code=400
            )

    # --------------------------------------------------------
    # CLIENTE
    # --------------------------------------------------------

    cliente = Cliente(

        nome=nome,

        matricula=(
            matricula
            if matricula
            else None
        ),

        telefone=(
            telefone
            if telefone
            else None
        ),

        is_associado=is_associado,

        ativo=True,

        desconto_percentual=
            desconto_percentual
    )

    db.add(cliente)

    db.commit()

    return RedirectResponse(
        url="/clientes?criado=ok",
        status_code=303
    )


# ============================================================
# FORMULÁRIO EDITAR
# ============================================================

@router.get("/{cliente_id}/editar")
def form_editar(

    cliente_id: int,

    request: Request,

    db: Session = Depends(get_db),

    admin=Depends(get_admin)
):

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id
        )
        .first()
    )

    if not cliente:

        return RedirectResponse(
            url="/clientes?erro=nao_encontrado",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="clientes/form.html",
        context={
            "request": request,
            "usuario": admin,
            "editando": cliente
        }
    )


# ============================================================
# EDITAR
# ============================================================

@router.post("/{cliente_id}/editar")
def editar(

    cliente_id: int,

    request: Request,

    nome: str = Form(...),

    matricula: str = Form(""),

    telefone: str = Form(""),

    is_associado: bool = Form(False),

    desconto_percentual: float = Form(0.0),

    db: Session = Depends(get_db),

    admin=Depends(get_admin)
):

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id
        )
        .first()
    )

    if not cliente:

        return RedirectResponse(
            url="/clientes",
            status_code=303
        )

    nome = nome.strip()

    matricula = matricula.strip()

    telefone = telefone.strip()

    # --------------------------------------------------------
    # DESCONTO
    # --------------------------------------------------------

    try:

        desconto_percentual = float(
            desconto_percentual
        )

    except (TypeError, ValueError):

        desconto_percentual = 0.0

    desconto_percentual = max(
        0.0,
        min(100.0, desconto_percentual)
    )

    desconto_percentual = round(
        desconto_percentual,
        2
    )

    # --------------------------------------------------------
    # MATRÍCULA
    # --------------------------------------------------------

    if matricula:

        conflito = (
            db.query(Cliente)
            .filter(
                Cliente.matricula ==
                    matricula,

                Cliente.id !=
                    cliente_id
            )
            .first()
        )

        if conflito:

            return templates.TemplateResponse(
                request=request,
                name="clientes/form.html",
                context={
                    "request":
                        request,

                    "usuario":
                        admin,

                    "editando":
                        cliente,

                    "erro":
                        f"Matrícula {matricula} "
                        "já pertence a outro cliente."
                },
                status_code=400
            )

    # --------------------------------------------------------
    # ATUALIZAR
    # --------------------------------------------------------

    cliente.nome = nome

    cliente.matricula = (
        matricula
        if matricula
        else None
    )

    cliente.telefone = (
        telefone
        if telefone
        else None
    )

    cliente.is_associado = (
        is_associado
    )

    cliente.desconto_percentual = (
        desconto_percentual
    )

    db.commit()

    return RedirectResponse(
        url="/clientes?editado=ok",
        status_code=303
    )


# ============================================================
# ATIVAR / DESATIVAR
# ============================================================

@router.post("/{cliente_id}/toggle-ativo")
def toggle_ativo(

    cliente_id: int,

    db: Session = Depends(get_db),

    admin=Depends(get_admin)
):

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id
        )
        .first()
    )

    if cliente:

        cliente.ativo = (
            not cliente.ativo
        )

        db.commit()

    return RedirectResponse(
        url="/clientes",
        status_code=303
    )


# ============================================================
# EXCLUIR
# ============================================================

@router.post("/{cliente_id}/excluir")
def excluir_cliente(

    cliente_id: int,

    db: Session = Depends(get_db),

    admin=Depends(get_admin)
):

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id
        )
        .first()
    )

    if not cliente:

        return RedirectResponse(
            url="/clientes?erro=nao_encontrado",
            status_code=303
        )

    try:

        db.delete(cliente)

        db.commit()

        return RedirectResponse(
            url="/clientes?excluido=ok",
            status_code=303
        )

    except Exception:

        db.rollback()

        return RedirectResponse(
            url="/clientes?erro=exclusao",
            status_code=303
        )
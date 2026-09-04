from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuarios import Usuario
from app.auth import hash_senha, verificar_senha, criar_token

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"]
)

templates = Jinja2Templates(directory="app/templates")


# ==========================
# TELA DE CADASTRO
# ==========================
@router.get("/cadastro", response_class=HTMLResponse)
def tela_cadastro(request: Request):
   return templates.TemplateResponse(
    request=request,
    name="auth/cadastro.html",
    context={"request": request}
)


# ==========================
# TELA DE LOGIN
# ==========================
@router.get("/login", response_class=HTMLResponse)
def tela_login(request: Request):
   return templates.TemplateResponse(
    request=request,
    name="auth/login.html",
    context={"request": request}
)


# ==========================
# CADASTRAR USUÁRIO
# ==========================
@router.post("/cadastro")
def fazer_cadastro(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):

    usuario_existente = (
        db.query(Usuario)
        .filter(Usuario.email == email)
        .first()
    )

    if usuario_existente:
        return templates.TemplateResponse(
            "auth/cadastro.html",
            {
                "request": request,
                "erro": "Este e-mail já está cadastrado."
            },
            status_code=400
        )

    novo_usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=hash_senha(senha)
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return RedirectResponse(
        url="/auth/login?cadastro=ok",
        status_code=302
    )


# ==========================
# LOGIN
# ==========================
@router.post("/login")
def fazer_login(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):

    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == email)
        .first()
    )

    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        # CORREÇÃO: Altere a linha 104 para este formato:
        return templates.TemplateResponse(
    request=request,
    name="auth/login.html",
    context={"erro": "Usuário ou senha incorretos"},  # substitua pelo dicionário que estava aí
    status_code=400
)
    if not usuario.ativo:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "erro": "Usuário inativo."
            },
            status_code=403
        )

    token = criar_token(
        {
            "sub": usuario.email,
            "id": usuario.id,
            "nome": usuario.nome,
            "role": usuario.role
        }
    )

    response = RedirectResponse(
        url="/",
        status_code=302
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax"
    )

    return response


# ==========================
# LOGOUT
# ==========================
@router.get("/logout")
def sair():

    response = RedirectResponse(
        url="/auth/login",
        status_code=302
    )

    response.delete_cookie("access_token")

    return response
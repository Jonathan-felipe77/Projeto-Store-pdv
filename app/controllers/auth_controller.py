from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import criar_token, hash_senha, verificar_senha
from app.database import get_db
from app.models.usuarios import Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/cadastro", response_class=HTMLResponse)
def tela_cadastro(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/cadastro.html",
        context={"request": request},
    )


@router.get("/login", response_class=HTMLResponse)
def tela_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request},
    )


@router.post("/cadastro", response_class=HTMLResponse)
def fazer_cadastro(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    email_normalizado = email.strip().lower()
    usuario_existente = (
        db.query(Usuario)
        .filter(Usuario.email == email_normalizado)
        .first()
    )

    if usuario_existente:
        return templates.TemplateResponse(
            request=request,
            name="auth/cadastro.html",
            context={
                "request": request,
                "erro": "Este e-mail já está cadastrado.",
            },
            status_code=400,
        )

    novo_usuario = Usuario(
        nome=nome.strip(),
        email=email_normalizado,
        senha_hash=hash_senha(senha),
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return RedirectResponse(
        url="/auth/login?cadastro=ok",
        status_code=303,
    )


@router.post("/login", response_class=HTMLResponse)
def fazer_login(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    email_normalizado = email.strip().lower()
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == email_normalizado)
        .first()
    )

    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "erro": "Usuário ou senha incorretos.",
            },
            status_code=400,
        )

    if not usuario.ativo:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"request": request, "erro": "Usuário inativo."},
            status_code=403,
        )

    token = criar_token(
        {
            "sub": usuario.email,
            "id": usuario.id,
            "nome": usuario.nome,
            "role": usuario.role,
        }
    )
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax",
    )
    return response


@router.get("/logout")
def sair():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response

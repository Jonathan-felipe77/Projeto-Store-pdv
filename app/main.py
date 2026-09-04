import os

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import get_usuario_opcional

# Importação dos controladores existentes no seu projeto
from app.controllers import auth_controller
from app.controllers import usuario_controller
from app.controllers import categoria_controller
from app.controllers import produto_controller
from app.controllers import movimentacao_controller
from app.controllers import clientes_controller
from app.controllers import pdv_controller


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="M&J Store - Sistema de Ponto de Venda e Estoque"
)


# ============================================================
# PASTA DE ARQUIVOS ESTÁTICOS
# ============================================================

if os.path.exists("app/static"):
    PASTA_ESTATICOS = "app/static"

elif os.path.exists("static"):
    PASTA_ESTATICOS = "static"

else:
    os.makedirs("app/static", exist_ok=True)
    PASTA_ESTATICOS = "app/static"


app.mount(
    "/static",
    StaticFiles(directory=PASTA_ESTATICOS),
    name="static"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory="app/templates"
)


# ============================================================
# CONTROLADORES
# ============================================================

app.include_router(auth_controller.router)
app.include_router(usuario_controller.router)
app.include_router(categoria_controller.router)
app.include_router(produto_controller.router)
app.include_router(movimentacao_controller.router)
app.include_router(clientes_controller.router)
app.include_router(pdv_controller.router)


# ============================================================
# ERRO 404 — ROTA NÃO EXISTE
# ============================================================

@app.exception_handler(404)
async def erro_404(
    request: Request,
    exc: StarletteHTTPException
):
    return templates.TemplateResponse(
        request=request,
        name="erros/404.html",
        context={
            "codigo": 404,
            "titulo": "Página não encontrada",
            "mensagem": "A página ou rota que você tentou acessar não existe."
        },
        status_code=404
    )


# ============================================================
# ERRO 401 — NÃO ESTÁ LOGADO
# ============================================================

@app.exception_handler(401)
async def erro_401(
    request: Request,
    exc: StarletteHTTPException
):
    return templates.TemplateResponse(
        request=request,
        name="erros/401.html",
        context={
            "codigo": 401,
            "titulo": "Acesso não autorizado",
            "mensagem": "Você precisa estar logado para acessar esta página."
        },
        status_code=401
    )


# ============================================================
# ERRO 403 — SEM PERMISSÃO
# ============================================================

@app.exception_handler(403)
async def erro_403(
    request: Request,
    exc: StarletteHTTPException
):
    return templates.TemplateResponse(
        request=request,
        name="erros/401.html",
        context={
            "codigo": 403,
            "titulo": "Acesso negado",
            "mensagem": "Você não possui permissão para acessar esta página."
        },
        status_code=403
    )


# ============================================================
# ROTA PRINCIPAL
# ============================================================

@app.get("/")
def tela_inicial(
    request: Request,
    usuario=Depends(get_usuario_opcional)
):
    """
    Rota Raiz (/).

    Se NÃO estiver logado:
        mostra index.html

    Se estiver logado:
        mostra home.html
    """

    # --------------------------------------------------------
    # USUÁRIO NÃO LOGADO
    # --------------------------------------------------------

    if usuario is None:

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "usuario": None
            }
        )

    # --------------------------------------------------------
    # USUÁRIO LOGADO
    # --------------------------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "usuario": usuario
        }
    )


# ============================================================
# PAINEL
# ============================================================

@app.get("/painel")
def redireciona_painel(
    usuario=Depends(get_usuario_opcional)
):
    """
    Atalho para o painel.

    Se não estiver logado:
        envia para login.

    Se estiver logado:
        envia para dashboard.
    """

    if not usuario:

        return RedirectResponse(
            url="/auth/login",
            status_code=303
        )

    return RedirectResponse(
        url="/",
        status_code=303
    )


# ============================================================
# ROTA ANTIGA DE USUÁRIOS
# ============================================================

@app.get("/auth/usuarios")
def corrigir_rota_usuarios_antiga():
    """
    Redireciona a rota antiga para /usuarios.
    """

    return RedirectResponse(
        url="/usuarios",
        status_code=303
    )


# ============================================================
# ROTA ANTIGA DE PRODUTOS
# ============================================================

@app.get("/auth/produtos")
def corrigir_rota_produtos():
    """
    Redireciona a rota antiga para /produtos.
    """

    return RedirectResponse(
        url="/produtos",
        status_code=303
    )


# ============================================================
# ROTA ANTIGA DE CATEGORIAS
# ============================================================

@app.get("/auth/categorias")
def corrigir_rota_categorias():
    """
    Redireciona a rota antiga para /categorias.
    """

    return RedirectResponse(
        url="/categorias",
        status_code=303
    )
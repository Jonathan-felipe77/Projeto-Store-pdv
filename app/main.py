import os

from fastapi import (
    FastAPI,
    Request,
    Depends,
    HTTPException
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    Response
)

from fastapi.exception_handlers import (
    http_exception_handler
)

from app.auth import get_usuario_opcional

from app.controllers import auth_controller
from app.controllers import usuario_controller
from app.controllers import categoria_controller
from app.controllers import produto_controller
from app.controllers import movimentacao_controller
from app.controllers import clientes_controller
from app.controllers import pdv_controller


app = FastAPI(
    title="M&J Store - Sistema de Ponto de Venda e Estoque"
)


# ============================================================
# ARQUIVOS ESTÁTICOS
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
# ROTAS
# ============================================================

app.include_router(auth_controller.router)
app.include_router(usuario_controller.router)
app.include_router(categoria_controller.router)
app.include_router(produto_controller.router)
app.include_router(movimentacao_controller.router)
app.include_router(clientes_controller.router)
app.include_router(pdv_controller.router)


# ============================================================
# PÁGINA INICIAL
# ============================================================

@app.get("/")
def tela_inicial(
    request: Request,
    usuario=Depends(get_usuario_opcional)
):

    if usuario is None:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "usuario": None
            }
        )

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
# ROTAS ANTIGAS
# ============================================================

@app.get("/auth/usuarios")
def corrigir_rota_usuarios_antiga():

    return RedirectResponse(
        url="/usuarios",
        status_code=303
    )


@app.get("/auth/produtos")
def corrigir_rota_produtos():

    return RedirectResponse(
        url="/produtos",
        status_code=303
    )


@app.get("/auth/categorias")
def corrigir_rota_categorias():

    return RedirectResponse(
        url="/categorias",
        status_code=303
    )


# ============================================================
# FAVICON
# ============================================================

@app.get(
    "/favicon.ico",
    include_in_schema=False
)
def favicon():

    return Response(
        status_code=204
    )


# ============================================================
# ERRO 401 — NÃO AUTENTICADO
# ============================================================

@app.exception_handler(401)
async def erro_401(
    request: Request,
    exc
):
    return templates.TemplateResponse(
        request,
        "errors/erro.html",
        {
            "request": request,
            "status_code": 401,

            "titulo": "Autenticação necessária",

            "mensagem": (
                "Você precisa estar autenticado "
                "para acessar esta área."
            ),

            "detalhe": (
                "Faça login para continuar."
            ),
        },
        status_code=401
    )


# ============================================================
# ERRO 403 — ACESSO NÃO PERMITIDO
# ============================================================

@app.exception_handler(403)
async def erro_403(
    request: Request,
    exc
):
    return templates.TemplateResponse(
        request,
        "errors/erro.html",
        {
            "request": request,
            "status_code": 403,

            "titulo": "Acesso não permitido",

            "mensagem": (
                "Você não possui permissão "
                "para acessar esta área."
            ),

            "detalhe": (
                "Entre com uma conta de administrador "
                "para continuar."
            ),
        },
        status_code=403
    )


# ============================================================
# ERRO 404 — ROTA NÃO ENCONTRADA
# ============================================================

@app.exception_handler(404)
async def erro_404(
    request: Request,
    exc
):
    return templates.TemplateResponse(
        request,
        "errors/erro.html",
        {
            "request": request,
            "status_code": 404,

            "titulo": "Rota não encontrada",

            "mensagem": (
                "A página que você tentou acessar "
                "não existe."
            ),

            "detalhe": (
                "Verifique o endereço ou volte "
                "para a página inicial."
            ),
        },
        status_code=404
    )

# ============================================================
# ERROS HTTP GENÉRICOS
# ============================================================

@app.exception_handler(HTTPException)
async def tratar_http_exception(
    request: Request,
    exc: HTTPException
):

    if exc.status_code == 404:
        return await erro_404(
            request,
            exc
        )

    return await http_exception_handler(
        request,
        exc
    )
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
# ERRO 404
# ============================================================

@app.exception_handler(404)
async def erro_404(
    request: Request,
    exc: HTTPException
):

    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">

            <title>Página não encontrada</title>

            <style>

                * {
                    box-sizing: border-box;
                }

                body {
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;

                    font-family:
                        Arial,
                        Helvetica,
                        sans-serif;

                    background:
                        linear-gradient(
                            135deg,
                            #020617,
                            #0f172a
                        );

                    color: white;
                }

                .erro {
                    width: 90%;
                    max-width: 550px;
                    text-align: center;

                    background: #111827;

                    border: 1px solid #1f2937;

                    border-radius: 20px;

                    padding: 50px 30px;

                    box-shadow:
                        0 20px 50px
                        rgba(0,0,0,.5);
                }

                .numero {
                    font-size: 100px;
                    font-weight: 900;
                    line-height: 1;

                    color: #00ff88;

                    margin-bottom: 15px;
                }

                h1 {
                    margin: 0 0 12px;
                    font-size: 30px;
                }

                p {
                    color: #94a3b8;
                    font-size: 16px;
                    line-height: 1.6;
                    margin-bottom: 30px;
                }

                a {
                    display: inline-block;

                    padding: 12px 22px;

                    background: #00ff88;
                    color: #020617;

                    border-radius: 10px;

                    text-decoration: none;

                    font-weight: 800;

                    transition: .2s;
                }

                a:hover {
                    transform: translateY(-2px);
                    box-shadow:
                        0 8px 20px
                        rgba(0,255,136,.25);
                }

            </style>
        </head>

        <body>

            <div class="erro">

                <div class="numero">
                    404
                </div>

                <h1>
                    Página não encontrada
                </h1>

                <p>
                    A página que você tentou acessar
                    não existe ou foi removida.
                </p>

                <a href="/">
                    Voltar para o início
                </a>

            </div>

        </body>
        </html>
        """,
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
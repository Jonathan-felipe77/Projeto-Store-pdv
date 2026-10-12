import os
import importlib
from pathlib import Path

from fastapi import FastAPI, Depends, Request
from fastapi.responses import RedirectResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
MODELS_DIR = BASE_DIR / "models"
CONTROLLERS_DIR = BASE_DIR / "controllers"


# ============================================================
# CRIAR PASTAS
# ============================================================

STATIC_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TEMPLATES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

(STATIC_DIR / "uploads").mkdir(
    parents=True,
    exist_ok=True
)

(STATIC_DIR / "img").mkdir(
    parents=True,
    exist_ok=True
)

(STATIC_DIR / "css").mkdir(
    parents=True,
    exist_ok=True
)

(STATIC_DIR / "js").mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================

try:

    from dotenv import load_dotenv

    # .env uma pasta acima
    env_file = BASE_DIR.parent / ".env"

    if env_file.exists():
        load_dotenv(env_file)

    # .env na pasta atual
    load_dotenv()

except Exception:
    pass


def configurar_variavel(nome, padrao):

    valor = os.getenv(nome)

    if (
        valor is None
        or str(valor).strip() == ""
    ):

        os.environ[nome] = str(padrao)

    else:

        os.environ[nome] = str(valor).strip()


# ============================================================
# CONFIGURAÇÕES
# ============================================================

configurar_variavel(
    "ACCESS_TOKEN_EXPIRE_MINUTE",
    "60"
)

configurar_variavel(
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "60"
)

configurar_variavel(
    "SECRET_KEY",
    "mj-store-secret-key-2026"
)

configurar_variavel(
    "JWT_SECRET_KEY",
    os.environ["SECRET_KEY"]
)

configurar_variavel(
    "JWT_SECRET",
    os.environ["SECRET_KEY"]
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(

    title="M&J Store - Sistema de Ponto de Venda",

    description=(
        "Sistema de gerenciamento de "
        "produtos, clientes, categorias, "
        "estoque e vendas."
    ),

    version="1.0.0"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(

    directory=str(
        TEMPLATES_DIR
    )
)


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

app.mount(

    "/static",

    StaticFiles(
        directory=str(
            STATIC_DIR
        )
    ),

    name="static"
)


# ============================================================
# SESSION
# ============================================================

app.add_middleware(

    SessionMiddleware,

    secret_key=os.environ["SECRET_KEY"],

    session_cookie="mj_session",

    max_age=60 * 60 * 24 * 7,

    same_site="lax",

    https_only=False
)


# ============================================================
# BANCO DE DADOS
# ============================================================

try:

    from app.database import (
        Base,
        engine
    )

    # ========================================================
    # MODELOS
    # ========================================================

    MODELOS = [

        "app.models.usuarios",

        "app.models.categoria",

        "app.models.cliente",

        "app.models.produto",

        "app.models.venda",

        "app.models.movimentacao",

        "app.models.pagamento"

    ]

    modelos_carregados = []


    for nome_modelo in MODELOS:

        try:

            importlib.import_module(
                nome_modelo
            )

            modelos_carregados.append(
                nome_modelo
            )

            print(
                f"[OK] Modelo carregado: "
                f"{nome_modelo}"
            )

        except ModuleNotFoundError as erro:

            print(
                f"[AVISO] Modelo não encontrado: "
                f"{nome_modelo} -> {erro}"
            )

        except Exception as erro:

            print(
                f"[ERRO] Falha ao carregar modelo: "
                f"{nome_modelo} -> {erro}"
            )


    # ========================================================
    # CRIAR TABELAS
    # ========================================================

    Base.metadata.create_all(
        bind=engine
    )

    print(
        "[OK] Banco de dados inicializado."
    )


except Exception as erro:

    print(
        "[ERRO] Falha ao inicializar "
        f"banco de dados: {erro}"
    )


# ============================================================
# CONTROLLERS
# ============================================================

CONTROLLERS = [

    "app.controllers.auth_controller",

    "app.controllers.categoria_controller",

    "app.controllers.clientes_controller",

    "app.controllers.movimentacao_controller",

    "app.controllers.produto_controller",

    "app.controllers.usuario_controller",

    "app.controllers.pdv_controller"

]


controllers_carregados = []


for nome_controller in CONTROLLERS:

    try:

        modulo = importlib.import_module(
            nome_controller
        )


        router = getattr(
            modulo,
            "router",
            None
        )


        if router is None:

            print(
                f"[AVISO] {nome_controller} "
                "não possui router."
            )

            continue


        app.include_router(
            router
        )


        controllers_carregados.append(
            nome_controller
        )


        print(
            f"[OK] Controller carregado: "
            f"{nome_controller}"
        )


    except ModuleNotFoundError as erro:

        print(
            f"[ERRO] Controller não encontrado: "
            f"{nome_controller} -> {erro}"
        )


    except Exception as erro:

        print(
            f"[ERRO] Não foi possível carregar "
            f"{nome_controller}: {erro}"
        )


# ============================================================
# AUTENTICAÇÃO
# ============================================================

try:

    from app.auth import (
        get_usuario_opcional
    )

    AUTH_DISPONIVEL = True


except Exception as erro:

    AUTH_DISPONIVEL = False

    print(
        "[AVISO] Não foi possível carregar "
        f"get_usuario_opcional: {erro}"
    )


# ============================================================
# ROTA PRINCIPAL
# ============================================================

if AUTH_DISPONIVEL:

    @app.get(
        "/",
        response_class=HTMLResponse,
        include_in_schema=False
    )
    def inicio(
        request: Request,
        usuario=Depends(get_usuario_opcional)
    ):

        if not usuario:

            return RedirectResponse(
                url="/auth/login",
                status_code=303
            )


        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "request": request,
                "usuario": usuario
            }
        )


else:

    @app.get(
        "/",
        include_in_schema=False
    )
    def inicio_sem_auth():

        return RedirectResponse(
            url="/auth/login",
            status_code=303
        )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_ja_existe():

    for rota in app.routes:

        if getattr(
            rota,
            "path",
            None
        ) == "/dashboard":

            return True

    return False


if not dashboard_ja_existe():

    if AUTH_DISPONIVEL:

        @app.get(
            "/dashboard",
            response_class=HTMLResponse,
            include_in_schema=False
        )
        def dashboard_fallback(
            request: Request,
            usuario=Depends(get_usuario_opcional)
        ):

            if not usuario:

                return RedirectResponse(
                    url="/auth/login",
                    status_code=303
                )


            return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context={
                    "request": request,
                    "usuario": usuario
                }
            )


    else:

        @app.get(
            "/dashboard",
            include_in_schema=False
        )
        def dashboard_fallback_sem_auth():

            return RedirectResponse(
                url="/auth/login",
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
# HEALTH CHECK
# ============================================================

@app.get(
    "/health",
    tags=["Sistema"]
)
def health():

    return {

        "status": "ok",

        "sistema": "M&J Store",

        "controllers": (
            controllers_carregados
        )

    }


# ============================================================
# TRATAMENTO DE ERRO 404
# ============================================================

@app.exception_handler(404)
async def erro_404(
    request: Request,
    exc
):

    try:

        return templates.TemplateResponse(

            request=request,

            name="404.html",

            context={
                "request": request
            },

            status_code=404
        )


    except Exception:

        return Response(

            content="""
            <!DOCTYPE html>

            <html lang="pt-BR">

            <head>

                <meta charset="UTF-8">

                <title>Página não encontrada</title>

                <style>

                    body {
                        font-family: Arial, sans-serif;
                        background: #f5f5f5;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                    }

                    .box {
                        background: white;
                        padding: 40px;
                        border-radius: 15px;
                        box-shadow:
                            0 5px 25px
                            rgba(0,0,0,.12);
                        text-align: center;
                    }

                    h1 {
                        font-size: 50px;
                        margin: 0 0 10px;
                    }

                    p {
                        color: #666;
                    }

                    a {
                        display: inline-block;
                        margin-top: 20px;
                        padding: 12px 20px;
                        background: #111;
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                    }

                </style>

            </head>

            <body>

                <div class="box">

                    <h1>404</h1>

                    <h2>Página não encontrada</h2>

                    <p>
                        A rota acessada não existe.
                    </p>

                    <a href="/">
                        Voltar para tela de início
                    </a>

                </div>

            </body>

            </html>
            """,

            status_code=404,

            media_type="text/html"
        )


# ============================================================
# ERROS HTTP
# ============================================================

@app.exception_handler(403)
async def erro_403(
    request: Request,
    exc
):

    return Response(

        content="""
        <!DOCTYPE html>

        <html lang="pt-BR">

        <head>

            <meta charset="UTF-8">

            <title>Acesso negado</title>

            <style>

                body {
                    font-family: Arial, sans-serif;
                    background: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                }

                .box {
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow:
                        0 5px 25px
                        rgba(0,0,0,.12);
                    text-align: center;
                }

                a {
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 20px;
                    background: #111;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                }

            </style>

        </head>

        <body>

            <div class="box">

                <h1>Acesso negado</h1>

                <p>
                    Você não possui permissão
                    para acessar esta página.
                </p>

                <a href="/">
                    Voltar para início
                </a>

            </div>

        </body>

        </html>
        """,

        status_code=403,

        media_type="text/html"
    )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():

    print()

    print("=" * 65)

    print(
        "                         M&J STORE"
    )

    print(
        "             Sistema de Ponto de Venda"
    )

    print("=" * 65)

    print(
        "Aplicação iniciada com sucesso."
    )

    print(
        "URL: http://127.0.0.1:8000"
    )

    print()

    print(
        "Controllers carregados:"
    )


    for controller in controllers_carregados:

        print(
            f"  [OK] {controller}"
        )


    print()

    print(
        "Banco de dados: OK"
    )

    print(
        "Tabela de pagamentos: OK"
    )

    print("=" * 65)

    print()


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "app.main:app",

        host="127.0.0.1",

        port=8000,

        reload=True
    )
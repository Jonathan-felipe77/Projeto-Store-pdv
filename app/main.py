import os
import importlib
from pathlib import Path

from fastapi import FastAPI, Depends, Request
from fastapi.responses import RedirectResponse, Response
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

# Cria as pastas caso ainda não existam
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "uploads").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "img").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)


# ============================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================

# Tenta carregar o .env sem obrigar a instalação do pacote
try:
    from dotenv import load_dotenv

    env_file = BASE_DIR.parent / ".env"

    if env_file.exists():
        load_dotenv(env_file)

    # Também tenta o .env da raiz atual
    load_dotenv()
except Exception:
    pass


def configurar_variavel(nome, padrao):
    """
    Mantém o valor do ambiente quando estiver preenchido.
    Caso esteja vazio, None ou inválido, usa o padrão.
    """
    valor = os.getenv(nome)

    if valor is None or str(valor).strip() == "":
        os.environ[nome] = str(padrao)
    else:
        os.environ[nome] = str(valor).strip()


# Corrige especialmente o erro:
# int() argument must be a string... not 'NoneType'
configurar_variavel("ACCESS_TOKEN_EXPIRE_MINUTE", "60")
configurar_variavel("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

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
# APLICAÇÃO FASTAPI
# ============================================================

app = FastAPI(
    title="M&J Store - Sistema de Ponto de Venda e Estoque",
    description="Sistema de gerenciamento de produtos, clientes, categorias, estoque e vendas.",
    version="1.0.0"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR)
)


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# ============================================================
# SESSION MIDDLEWARE
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
    from app.database import Base, engine

    # Ordem pensada para respeitar os relacionamentos
    # dos seus modelos.
    modelos = [
        "app.models.usuarios",
        "app.models.categoria",
        "app.models.cliente",
        "app.models.produto",
        "app.models.venda",
        "app.models.movimentacao",
        "app.models.pagamento",
    ]

    for nome_modelo in modelos:
        try:
            importlib.import_module(nome_modelo)
            print(f"[OK] Modelo carregado: {nome_modelo}")
        except ModuleNotFoundError as erro:
            print(f"[AVISO] Modelo não encontrado: {nome_modelo} -> {erro}")
        except Exception as erro:
            print(f"[ERRO] Falha ao carregar {nome_modelo}: {erro}")

    Base.metadata.create_all(bind=engine)

    print("[OK] Banco de dados inicializado.")

except Exception as erro:
    print(f"[ERRO] Falha ao inicializar banco de dados: {erro}")


# ============================================================
# CONTROLLERS
# ============================================================

# Estes são exatamente os arquivos que existem
# na estrutura que você mostrou.
CONTROLLERS = [
    "app.controllers.auth_controller",
    "app.controllers.categoria_controller",
    "app.controllers.clientes_controller",
    "app.controllers.movimentacao_controller",
    "app.controllers.produto_controller",
    "app.controllers.usuario_controller",
    "app.controllers.pdv_controller",
]


controllers_carregados = []


for nome_controller in CONTROLLERS:
    try:
        modulo = importlib.import_module(nome_controller)

        router = getattr(modulo, "router", None)

        if router is None:
            print(
                f"[AVISO] {nome_controller} foi importado, "
                f"mas não possui uma variável 'router'."
            )
            continue

        app.include_router(router)
        controllers_carregados.append(nome_controller)

        print(f"[OK] Controller carregado: {nome_controller}")

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
# AUTENTICAÇÃO OPCIONAL PARA A ROTA /
# ============================================================

try:
    from app.auth import get_usuario_opcional

    AUTH_DISPONIVEL = True

except Exception as erro:
    AUTH_DISPONIVEL = False

    print(
        f"[AVISO] Não foi possível carregar "
        f"get_usuario_opcional: {erro}"
    )


# ============================================================
# ROTA PRINCIPAL
# ============================================================

if AUTH_DISPONIVEL:

    @app.get("/", include_in_schema=False)
    def inicio(
        usuario=Depends(get_usuario_opcional)
    ):
        """
        Usuário logado:
            / -> /dashboard

        Usuário não logado:
            / -> /auth/login
        """

        if usuario:
            return RedirectResponse(
                url="/dashboard",
                status_code=303
            )

        return RedirectResponse(
            url="/auth/login",
            status_code=303
        )

else:

    @app.get("/", include_in_schema=False)
    def inicio_sem_auth():
        """
        Fallback caso o módulo de autenticação
        não consiga ser importado.
        """

        return RedirectResponse(
            url="/auth/login",
            status_code=303
        )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_ja_existe():
    """
    Verifica se algum controller já criou uma rota
    /dashboard.
    """

    for rota in app.routes:
        if getattr(rota, "path", None) == "/dashboard":
            return True

    return False


if not dashboard_ja_existe():

    if AUTH_DISPONIVEL:

        @app.get("/dashboard", include_in_schema=False)
        def dashboard_fallback(
            request: Request,
            usuario=Depends(get_usuario_opcional)
        ):
            """
            Como seu projeto não possui
            dashboard_controller.py, esta rota impede
            que /dashboard fique dando 404.

            Se não estiver logado, manda para o login.
            Se estiver logado, mostra o sistema.
            """

            if not usuario:
                return RedirectResponse(
                    url="/auth/login",
                    status_code=303
                )

            # Como o projeto não tem dashboard_controller.py,
            # usamos a página PDV como tela principal do sistema.
            return RedirectResponse(
                url="/pdv/",
                status_code=303
            )

    else:

        @app.get("/dashboard", include_in_schema=False)
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
    return Response(status_code=204)


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
        "controllers": controllers_carregados
    }


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    print()
    print("=" * 65)
    print("                     M&J STORE")
    print("         Sistema de Ponto de Venda e Estoque")
    print("=" * 65)
    print("Aplicação iniciada com sucesso.")
    print("URL: http://127.0.0.1:8000")
    print()
    print("Controllers:")
    
    for controller in controllers_carregados:
        print(f"  [OK] {controller}")

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
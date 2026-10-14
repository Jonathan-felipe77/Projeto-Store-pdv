import importlib
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware


# ============================================================
# CAMINHOS DO PROJETO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
MODELS_DIR = BASE_DIR / "models"
CONTROLLERS_DIR = BASE_DIR / "controllers"


# ============================================================
# GARANTIR QUE AS PASTAS NECESSÁRIAS EXISTAM
# ============================================================

for pasta in (
    STATIC_DIR,
    TEMPLATES_DIR,
    MODELS_DIR,
    CONTROLLERS_DIR,
    STATIC_DIR / "uploads",
    STATIC_DIR / "img",
    STATIC_DIR / "css",
    STATIC_DIR / "js",
):
    pasta.mkdir(parents=True, exist_ok=True)


# ============================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================

try:
    from dotenv import load_dotenv

    # Primeiro tenta o .env na raiz do projeto (um nível acima de app/).
    env_file = BASE_DIR.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Também aceita um .env no diretório de trabalho atual.
    load_dotenv()
except ImportError:
    # O projeto continua funcionando se python-dotenv não estiver instalado,
    # desde que as variáveis necessárias já estejam definidas no ambiente.
    pass


def configurar_variavel(nome: str, padrao: str) -> None:
    """Define um valor padrão sem sobrescrever variáveis existentes."""
    valor = os.getenv(nome)
    if valor is None or not str(valor).strip():
        os.environ[nome] = str(padrao)
    else:
        os.environ[nome] = str(valor).strip()


configurar_variavel("ACCESS_TOKEN_EXPIRE_MINUTE", "60")
configurar_variavel("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
configurar_variavel("SECRET_KEY", "mj-store-secret-key-2026")
configurar_variavel("JWT_SECRET_KEY", os.environ["SECRET_KEY"])
configurar_variavel("JWT_SECRET", os.environ["SECRET_KEY"])


# ============================================================
# APLICAÇÃO FASTAPI
# ============================================================

app = FastAPI(
    title="M&J Store - Sistema de Ponto de Venda",
    description=(
        "Sistema de gerenciamento de produtos, clientes, categorias, "
        "estoque e vendas."
    ),
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SECRET_KEY"],
    session_cookie="mj_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)


# ============================================================
# BANCO DE DADOS E MODELOS
# ============================================================

BANCO_DISPONIVEL = False
modelos_carregados = []

try:
    from app.database import Base, engine

    MODELOS = [
        "app.models.usuarios",
        "app.models.categoria",
        "app.models.cliente",
        "app.models.produto",
        "app.models.venda",
        "app.models.movimentacao",
        "app.models.pagamento",
    ]

    # Importar todos os modelos antes de create_all(), incluindo Pagamento.
    for nome_modelo in MODELOS:
        try:
            importlib.import_module(nome_modelo)
            modelos_carregados.append(nome_modelo)
            print(f"[OK] Modelo carregado: {nome_modelo}")
        except ModuleNotFoundError as erro:
            print(f"[AVISO] Modelo/dependência não encontrado: {nome_modelo} -> {erro}")
        except Exception as erro:
            print(f"[ERRO] Falha ao carregar modelo {nome_modelo}: {erro}")

    Base.metadata.create_all(bind=engine)
    BANCO_DISPONIVEL = True
    print("[OK] Banco de dados inicializado.")

except Exception as erro:
    print(f"[ERRO] Falha ao inicializar o banco de dados: {erro}")


# ============================================================
# CARREGAR CONTROLLERS E REGISTRAR ROTAS
# ============================================================

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
            print(f"[AVISO] {nome_controller} não possui um objeto 'router'.")
            continue

        app.include_router(router)
        controllers_carregados.append(nome_controller)
        print(f"[OK] Controller carregado: {nome_controller}")

    except ModuleNotFoundError as erro:
        print(f"[ERRO] Controller ou dependência não encontrado: {nome_controller} -> {erro}")
    except Exception as erro:
        print(f"[ERRO] Não foi possível carregar {nome_controller}: {erro}")


# ============================================================
# AUTENTICAÇÃO
# ============================================================

try:
    from app.auth import get_usuario_opcional
    AUTH_DISPONIVEL = True
except Exception as erro:
    AUTH_DISPONIVEL = False
    get_usuario_opcional = None
    print(f"[AVISO] Não foi possível carregar get_usuario_opcional: {erro}")


# ============================================================
# ROTA PRINCIPAL
# ============================================================

if AUTH_DISPONIVEL:

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def inicio(request: Request, usuario=Depends(get_usuario_opcional)):
        if not usuario:
            return RedirectResponse(url="/auth/login", status_code=303)

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"request": request, "usuario": usuario},
        )

else:

    @app.get("/", include_in_schema=False)
    def inicio_sem_auth():
        return RedirectResponse(url="/auth/login", status_code=303)


# ============================================================
# ROTA DASHBOARD DE RESERVA
# Só é criada se nenhum controller já tiver registrado /dashboard.
# ============================================================

def dashboard_ja_existe() -> bool:
    return any(getattr(rota, "path", None) == "/dashboard" for rota in app.routes)


if not dashboard_ja_existe():
    if AUTH_DISPONIVEL:

        @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
        def dashboard_fallback(request: Request, usuario=Depends(get_usuario_opcional)):
            if not usuario:
                return RedirectResponse(url="/auth/login", status_code=303)

            return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context={"request": request, "usuario": usuario},
            )

    else:

        @app.get("/dashboard", include_in_schema=False)
        def dashboard_fallback_sem_auth():
            return RedirectResponse(url="/auth/login", status_code=303)


# ============================================================
# FAVICON E HEALTH CHECK
# ============================================================

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health", tags=["Sistema"])
def health():
    return {
        "status": "ok",
        "sistema": "M&J Store",
        "banco_disponivel": BANCO_DISPONIVEL,
        "modelos_carregados": modelos_carregados,
        "controllers": controllers_carregados,
    }


# ============================================================
# PÁGINA SIMPLES DE RESERVA PARA ERROS HTTP
# ============================================================

def pagina_erro_html(codigo: int, titulo: str, mensagem: str, detalhe: str = "") -> str:
    detalhe_html = f"<p>{detalhe}</p>" if detalhe else ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{codigo} - {titulo}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
               padding: 20px; font-family: Arial, sans-serif; background: #f5f5f5; color: #222; }}
        .box {{ width: min(560px, 100%); padding: 36px; border-radius: 16px;
                background: white; box-shadow: 0 8px 28px #0001; text-align: center; }}
        h1 {{ margin: 0 0 8px; color: #111; font-size: 42px; }}
        p {{ color: #666; line-height: 1.6; }}
        a {{ display: inline-block; margin-top: 14px; padding: 12px 20px;
             border-radius: 8px; background: #111; color: #c8ff1a; text-decoration: none; font-weight: bold; }}
    </style>
</head>
<body>
    <main class="box">
        <h1>{codigo}</h1>
        <h2>{titulo}</h2>
        <p>{mensagem}</p>
        {detalhe_html}
        <a href="/">Voltar ao início</a>
    </main>
</body>
</html>"""


@app.exception_handler(404)
async def erro_404(request: Request, exc):
    try:
        return templates.TemplateResponse(
            request=request,
            name="errors/erro.html",
            context={
                "request": request,
                "status_code": 404,
                "titulo": "Rota não encontrada",
                "mensagem": "A página que você tentou acessar não existe.",
                "detalhe": "Verifique o endereço ou volte para a página inicial.",
            },
            status_code=404,
        )
    except Exception:
        return Response(
            content=pagina_erro_html(
                404,
                "Página não encontrada",
                "A página que você tentou acessar não existe.",
                "Verifique o endereço ou volte para a página inicial.",
            ),
            status_code=404,
            media_type="text/html",
        )


@app.exception_handler(403)
async def erro_403(request: Request, exc):
    try:
        return templates.TemplateResponse(
            request=request,
            name="errors/erro.html",
            context={
                "request": request,
                "status_code": 403,
                "titulo": "Acesso não permitido",
                "mensagem": "Você não possui permissão para acessar esta área.",
                "detalhe": "Entre com uma conta autorizada para continuar.",
            },
            status_code=403,
        )
    except Exception:
        return Response(
            content=pagina_erro_html(
                403,
                "Acesso negado",
                "Você não possui permissão para acessar esta página.",
                "Entre com uma conta autorizada para continuar.",
            ),
            status_code=403,
            media_type="text/html",
        )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    print("\n" + "=" * 65)
    print("                         M&J STORE")
    print("                 Sistema de Ponto de Venda")
    print("=" * 65)
    print("Aplicação iniciada.")
    print("URL: http://127.0.0.1:8000")
    print(f"Banco de dados: {'OK' if BANCO_DISPONIVEL else 'verificar erro acima'}")
    print("\nControllers carregados:")
    for controller in controllers_carregados:
        print(f"  [OK] {controller}")
    print("=" * 65 + "\n")


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

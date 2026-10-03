"""Execute na raiz WorkAdapter: python -m uvicorn backend.api.main_router:app --reload

API sem autenticação para a fase local. CORS aberto a todas as origens,
métodos e cabeçalhos, sem credenciais/cookies cross-origin.
WORKADAPTER_DB pode definir outro caminho para o SQLite.
"""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from ..database.models import inicializar_banco
from ..agents.gen_model import QwenClient, ErroIA
from ..database.repository import RegistroNaoEncontrado, OperacaoNaoPermitida
from .routes import (
    usuarios,
)
from .routes import candidaturas
from .routes import curriculos
from .routes import cursos
from .routes import experiencias
from .routes import formacoes
from .routes import habilidades
from .routes import ia
from .routes import idiomas
from .routes import movimentacoes
from .routes import pdf
from .routes import projetos

main_router = APIRouter(prefix="/api")
for modulo in (usuarios, experiencias, formacoes, cursos, projetos, idiomas,
               habilidades, curriculos, candidaturas, movimentacoes, ia, pdf):
    main_router.include_router(modulo.router)


def criar_app(caminho_banco: str | Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = inicializar_banco(caminho_banco or os.getenv("WORKADAPTER_DB"))
        app.state.qwen = QwenClient()
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title="WorkAdapter API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
    app.include_router(main_router)

    @app.exception_handler(ErroIA)
    async def erro_ia(request: Request, exc: ErroIA):
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.exception_handler(RegistroNaoEncontrado)
    async def nao_encontrado(request: Request, exc: RegistroNaoEncontrado):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(OperacaoNaoPermitida)
    async def conflito(request: Request, exc: OperacaoNaoPermitida):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(IntegrityError)
    async def integridade(request: Request, exc: IntegrityError):
        # Não expõe SQL nem valores pessoais nos erros.
        return JSONResponse(status_code=409, content={"detail": "Os dados violam uma restrição do banco: verifique duplicações, vínculos e datas."})

    @app.exception_handler(ValueError)
    async def valor_invalido(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/health", tags=["sistema"])
    def health():
        return {"status": "ok"}

    return app


app = criar_app()

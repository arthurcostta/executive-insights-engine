"""API web para upload de planilhas e geração da análise executiva."""
from datetime import UTC, datetime
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from data_loader import format_as_context, load_uploaded_files
from gemini_client import generate_analysis, get_client
from prompts import SYSTEM_PROMPT, WEB_USER_PROMPT_TEMPLATE


ROOT_DIR = Path(__file__).parent.parent
WEB_DIR = ROOT_DIR / "web"

app = FastAPI(
    title="Executive Insights Engine",
    description="Upload de CSV/Excel e análise executiva com IA generativa.",
    version="0.2.0",
)


def _public_error_message(error: RuntimeError) -> str:
    message = str(error)
    lowered = message.lower()

    if "certificado ssl" in lowered or "certificate_verify_failed" in lowered:
        return (
            "A IA não conseguiu se conectar ao Gemini porque a rede está "
            "interceptando o certificado HTTPS. Tente novamente após rodar "
            "`python -m pip install -r requirements.txt` e reiniciar o servidor. "
            "Se persistir, use outra rede ou configure GEMINI_CA_BUNDLE no .env "
            "com o certificado raiz corporativo em formato .pem."
        )

    if "tempo limite excedido" in lowered or "read timed out" in lowered or "timeout" in lowered:
        return (
            "A IA demorou mais do que o limite configurado para responder. "
            "Isso pode acontecer na primeira execução por aquecimento da conexão "
            "ou latência temporária da API. Tente gerar novamente. Se ocorrer "
            "com frequência, aumente GEMINI_TIMEOUT_SECONDS no .env."
        )

    if "10013" in message or "permission denied" in lowered:
        return (
            "O Windows bloqueou a conexão de saída da IA para o Gemini. Verifique "
            "firewall, VPN ou proxy corporativo e libere "
            "generativelanguage.googleapis.com na porta 443."
        )

    return message


def _error_status_code(error: RuntimeError) -> int:
    lowered = str(error).lower()
    if "tempo limite excedido" in lowered or "read timed out" in lowered or "timeout" in lowered:
        return 504
    return 502


allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        os.getenv("CORS_ORIGINS", ""),
    ).split(",")
    if origin.strip()
]

if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "executive-insights-engine"}


@app.post("/api/analyze")
async def analyze(files: list[UploadFile] = File(...)) -> dict:
    payloads: list[tuple[str, bytes]] = []
    for uploaded_file in files:
        payloads.append((uploaded_file.filename or "arquivo", await uploaded_file.read()))

    try:
        data, metadata = load_uploaded_files(payloads)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    context = format_as_context(data, max_rows_per_table=35)
    user_prompt = WEB_USER_PROMPT_TEMPLATE.format(contexto_dados=context)

    try:
        analysis = generate_analysis(get_client(), SYSTEM_PROMPT, user_prompt)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=_error_status_code(exc),
            detail={
                "message": _public_error_message(exc),
                "generated_at": datetime.now(UTC).isoformat(),
                "table_count": len(metadata),
                "tables": metadata,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar os arquivos: {exc}",
        ) from exc

    return {
        "analysis": analysis,
        "generated_at": datetime.now(UTC).isoformat(),
        "table_count": len(metadata),
        "tables": metadata,
    }


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

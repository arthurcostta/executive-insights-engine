"""Cliente do Gemini API."""
import os
import socket
from collections.abc import Mapping
from pathlib import Path

import google.generativeai as genai
from google.api_core import retry as google_retry
from dotenv import load_dotenv


load_dotenv(override=True)

DEFAULT_MODEL_NAME = "gemini-3.5-flash-lite"
DEFAULT_FALLBACK_MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.6-flash",
)
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_OUTPUT_TOKENS = 900
DEFAULT_TRANSPORT = "rest"
GEMINI_API_HOST = "generativelanguage.googleapis.com"


def _is_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _configure_ca_bundle() -> bool:
    ca_bundle = os.getenv("GEMINI_CA_BUNDLE")
    if not ca_bundle:
        return False

    ca_bundle_path = Path(ca_bundle).expanduser()
    if not ca_bundle_path.exists():
        raise RuntimeError(
            f"GEMINI_CA_BUNDLE aponta para um arquivo que não existe: {ca_bundle_path}"
        )

    os.environ["REQUESTS_CA_BUNDLE"] = str(ca_bundle_path)
    os.environ["SSL_CERT_FILE"] = str(ca_bundle_path)
    os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = str(ca_bundle_path)
    return True


def _configure_system_certificates() -> None:
    if _configure_ca_bundle():
        return
    if not _is_enabled(os.getenv("GEMINI_USE_SYSTEM_CERTS"), default=True):
        return

    try:
        import truststore
    except ImportError:
        return

    truststore.inject_into_ssl()


def _get_timeout_seconds() -> int:
    raw_timeout = os.getenv("GEMINI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return int(raw_timeout)
    except ValueError as exc:
        raise RuntimeError("GEMINI_TIMEOUT_SECONDS precisa ser um número inteiro.") from exc


def _get_max_output_tokens() -> int:
    raw_tokens = os.getenv("GEMINI_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS))
    try:
        return int(raw_tokens)
    except ValueError as exc:
        raise RuntimeError("GEMINI_MAX_OUTPUT_TOKENS precisa ser um número inteiro.") from exc


def _check_gemini_dns() -> None:
    try:
        socket.getaddrinfo(GEMINI_API_HOST, 443)
    except socket.gaierror as exc:
        raise RuntimeError(
            f"Não foi possível resolver o endereço {GEMINI_API_HOST}. "
            "Isso indica problema de DNS, internet, proxy ou firewall; "
            "não é erro nos CSVs nem no nome dos arquivos."
        ) from exc


def _model_names_from_env() -> list[str]:
    primary_model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME).strip()
    fallback_models = os.getenv(
        "GEMINI_FALLBACK_MODELS",
        ",".join(DEFAULT_FALLBACK_MODELS),
    )
    candidates = [primary_model]
    candidates.extend(model.strip() for model in fallback_models.split(",") if model.strip())

    seen = set()
    unique_candidates = []
    for model_name in candidates:
        if model_name not in seen:
            seen.add(model_name)
            unique_candidates.append(model_name)

    return unique_candidates


def _is_model_unavailable_error(exc: Exception) -> bool:
    detail = str(exc).lower()
    return (
        "notfound" in type(exc).__name__.lower()
        or "404" in detail
        or "is no longer available" in detail
        or "is not found" in detail
        or "not supported for generatecontent" in detail
    )


def _build_runtime_error(exc: Exception) -> RuntimeError:
    detail = f"{type(exc).__name__}: {exc}"
    lowered_detail = detail.lower()

    if "read timed out" in lowered_detail or "timeout" in lowered_detail:
        return RuntimeError(
            "Tempo limite excedido ao chamar o Gemini. Isso costuma ser "
            "temporário na primeira chamada, por aquecimento da conexão, "
            "latência da API ou instabilidade de rede. Tente gerar a análise "
            "novamente. Se acontecer com frequência, aumente "
            "GEMINI_TIMEOUT_SECONDS no .env. "
            f"Detalhe técnico: {detail}"
        )

    if "certificate_verify_failed" in lowered_detail or "self signed certificate" in lowered_detail:
        return RuntimeError(
            "Falha de certificado SSL ao chamar o Gemini. Sua rede provavelmente "
            "usa proxy/firewall com inspeção HTTPS e certificado corporativo. "
            "Se o certificado corporativo estiver instalado no Windows, rode "
            "`python -m pip install -r requirements.txt` e tente novamente. "
            "Se ainda falhar, teste em outra rede ou configure GEMINI_CA_BUNDLE "
            "no .env com o caminho do certificado raiz corporativo em formato .pem. "
            f"Detalhe técnico: {detail}"
        )

    if "10013" in detail or "permission denied" in lowered_detail:
        return RuntimeError(
            "O Windows bloqueou a conexão de saída para o Gemini. Isso costuma "
            "ser firewall, VPN, proxy corporativo ou IPv6 bloqueado. Tente "
            "rodar em outra rede ou liberar generativelanguage.googleapis.com:443. "
            f"Detalhe técnico: {detail}"
        )

    return RuntimeError(
        "Falha ao chamar o Gemini. Verifique sua internet, a chave "
        "GEMINI_API_KEY, o nome do modelo em GEMINI_MODEL e tente novamente. "
        f"Detalhe técnico: {detail}"
    )


def get_client() -> genai.GenerativeModel:
    _configure_system_certificates()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não encontrada no .env")
    if api_key == "sua_chave_aqui" or len(api_key) < 30:
        raise RuntimeError(
            "GEMINI_API_KEY parece ser placeholder ou está curta demais. "
            "Cole a chave real gerada no Google AI Studio."
        )

    genai.configure(
        api_key=api_key,
        transport=os.getenv("GEMINI_TRANSPORT", DEFAULT_TRANSPORT),
    )
    return genai.GenerativeModel(
        model_name=_model_names_from_env()[0],
        system_instruction=None,
    )


def generate_analysis(
    model: genai.GenerativeModel,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Concatena system + user e retorna o texto gerado."""
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    generation_config: Mapping[str, int] = {
        "max_output_tokens": _get_max_output_tokens(),
    }
    timeout_seconds = _get_timeout_seconds()
    request_options = {
        "timeout": timeout_seconds,
        "retry": google_retry.Retry(
            initial=1.0,
            multiplier=2.0,
            maximum=5.0,
            timeout=timeout_seconds,
        ),
    }

    if _is_enabled(os.getenv("GEMINI_CHECK_DNS"), default=False):
        _check_gemini_dns()

    unavailable_models = []
    for index, model_name in enumerate(_model_names_from_env()):
        current_model = model if index == 0 else genai.GenerativeModel(model_name)

        try:
            response = current_model.generate_content(
                full_prompt,
                generation_config=generation_config,
                request_options=request_options,
            )
            return response.text
        except Exception as exc:
            if _is_model_unavailable_error(exc):
                unavailable_models.append(f"{model_name}: {type(exc).__name__}")
                continue
            raise _build_runtime_error(exc) from exc

    raise RuntimeError(
        "Nenhum modelo Gemini configurado está disponível para esta chave. "
        f"Modelos tentados: {', '.join(unavailable_models)}. "
        "Atualize GEMINI_MODEL ou GEMINI_FALLBACK_MODELS no .env."
    )

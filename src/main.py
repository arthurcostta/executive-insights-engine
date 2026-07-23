"""Orquestra a análise executiva do Olist."""
from pathlib import Path

from data_loader import format_as_context, load_all_data
from gemini_client import generate_analysis, get_client
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


OUTPUT_PATH = Path(__file__).parent.parent / "output" / "analise_executiva.md"


def main() -> None:
    try:
        print("1/4 - Carregando dados dos CSVs...")
        data = load_all_data()
        contexto = format_as_context(data)

        print("2/4 - Montando prompt...")
        user_prompt = USER_PROMPT_TEMPLATE.format(contexto_dados=contexto)

        print("3/4 - Chamando Gemini (limite de timeout configurado no .env)...")
        model = get_client()
        analise = generate_analysis(model, SYSTEM_PROMPT, user_prompt)

        print("4/4 - Salvando análise...")
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        OUTPUT_PATH.write_text(analise, encoding="utf-8")

        print(f"\nAnálise gerada em: {OUTPUT_PATH}")
        print(f"  ({len(analise)} caracteres)")
    except Exception as exc:
        print(f"\nErro: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

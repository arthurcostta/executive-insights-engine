"""Carrega arquivos tabulares e retorna dados estruturados para análise."""
from io import BytesIO
from pathlib import Path
import re

import pandas as pd


DATA_DIR = Path(__file__).parent.parent / "data"

CSV_FILES = {
    "kpis_gerais": ("kpis_gerais.csv", "olist1.csv"),
    "vendas_por_mes": ("vendas_por_mes.csv", "olist2.csv"),
    "vendas_por_categoria": ("vendas_por_categoria.csv", "olist4.csv"),
    "performance_entrega": ("performance_entrega.csv", "olist3.csv"),
    "satisfacao_cliente": ("satisfacao_cliente.csv", "olist5.csv"),
}

MAX_ROWS_PER_TABLE = 120
MAX_UPLOAD_MB = 12
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _resolve_csv_path(table_name: str, filenames: tuple[str, ...]) -> Path:
    for filename in filenames:
        path = DATA_DIR / filename
        if path.exists():
            return path

    expected = " ou ".join(filenames)
    raise FileNotFoundError(
        f"Arquivo da tabela '{table_name}' não encontrado em {DATA_DIR}. "
        f"Crie/exporte um destes arquivos: {expected}."
    )


def load_all_data() -> dict:
    """Lê todos os CSVs e retorna um dict pronto pra alimentar o prompt."""
    data = {}
    for table_name, filenames in CSV_FILES.items():
        path = _resolve_csv_path(table_name, filenames)
        data[table_name] = pd.read_csv(path).to_dict(orient="records")

    return data


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(column).strip() for column in df.columns]
    return df.astype(object).where(pd.notna(df), None)


def _safe_table_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-zÀ-ÿ]+", "_", name).strip("_")
    return cleaned or "tabela"


def _read_csv(content: bytes) -> pd.DataFrame:
    return _clean_dataframe(pd.read_csv(BytesIO(content)))


def _read_excel(content: bytes) -> dict[str, pd.DataFrame]:
    sheets = pd.read_excel(BytesIO(content), sheet_name=None)
    return {sheet_name: _clean_dataframe(sheet) for sheet_name, sheet in sheets.items()}


def load_uploaded_files(files: list[tuple[str, bytes]]) -> tuple[dict, list[dict]]:
    """Lê CSV/XLSX/XLS enviados pela interface web."""
    if not files:
        raise ValueError("Envie pelo menos um arquivo CSV ou Excel.")

    data: dict[str, list[dict]] = {}
    metadata: list[dict] = []

    for filename, content in files:
        if not content:
            raise ValueError(f"O arquivo {filename} está vazio.")

        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > MAX_UPLOAD_MB:
            raise ValueError(
                f"O arquivo {filename} tem {file_size_mb:.1f}MB. "
                f"O limite atual é {MAX_UPLOAD_MB}MB por arquivo."
            )

        suffix = Path(filename).suffix.lower()
        base_name = _safe_table_name(Path(filename).stem)
        if suffix not in SUPPORTED_EXTENSIONS:
            accepted = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Formato não suportado em {filename}. Use {accepted}.")

        if suffix == ".csv":
            tables = {base_name: _read_csv(content)}
        else:
            excel_tables = _read_excel(content)
            tables = {
                _safe_table_name(f"{base_name}_{sheet_name}"): df
                for sheet_name, df in excel_tables.items()
            }

        for table_name, df in tables.items():
            records = df.to_dict(orient="records")
            data[table_name] = records
            metadata.append(
                {
                    "table_name": table_name,
                    "source_file": filename,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "truncated_for_prompt": len(records) > MAX_ROWS_PER_TABLE,
                }
            )

    return data, metadata


def format_as_context(data: dict, max_rows_per_table: int = MAX_ROWS_PER_TABLE) -> str:
    """Converte o dict num texto legível pra ir dentro do prompt."""
    parts = []
    for tabela, linhas in data.items():
        parts.append(f"\n### Tabela: {tabela}\n")
        if not linhas:
            parts.append("(vazia)\n")
            continue

        cols = list(linhas[0].keys())
        parts.append(" | ".join(cols))
        parts.append("\n" + " | ".join(["---"] * len(cols)) + "\n")

        rows_to_render = linhas[:max_rows_per_table]
        if len(linhas) > max_rows_per_table:
            parts.append(
                f"\nObservação: tabela com {len(linhas)} linhas; "
                f"amostra limitada às primeiras {max_rows_per_table}.\n"
            )

        for linha in rows_to_render:
            parts.append(" | ".join(str(v) for v in linha.values()) + "\n")

    return "".join(parts)

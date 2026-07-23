# Executive Insights Engine

> Turn any spreadsheet into an executive analysis in seconds — powered by AI.

An AI-powered tool that reads aggregated tabular data (CSV or Excel) and generates executive analysis in natural language — as if a senior consultant were briefing a CEO. Built as a demonstration of applied prompt engineering, not just LLM plumbing.

*Demonstrated on the public [Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (100k+ orders), but the tool works with any tabular data.*

**[Live demo](#) · [Video walkthrough](#)** *(links after deploy)*

**Languages:** [🇺🇸 English](#english) · [🇧🇷 Português](#português)

---

## English

### What it does

Upload one or more spreadsheets. The engine reads the tables, feeds them into Google's Gemini API with a carefully engineered system prompt, and returns a structured executive analysis: Executive Summary, Key Indicators, Findings, Risks, and Next Steps.

The value is not the code — it's the **prompt engineering**. The system prompt enforces the persona of a senior data consultant briefing a CEO, forbids fabricated numbers, requires cross-referencing between tables, and locks output structure. Same code + different prompt = different product.

### Stack

- **Backend:** Python 3.11 · FastAPI · Google Generative AI SDK · pandas
- **Frontend:** HTML / CSS / vanilla JavaScript
- **Deploy:** Render (free tier, `render.yaml` included)
- **Data pipeline:** Power BI dashboard → aggregated CSV export → engine

### How it works

1. Aggregate your data in Power BI (or any BI tool) into small summary tables (KPIs, breakdowns).
2. Export each summary as CSV or Excel.
3. Upload to the web panel — or run the CLI script for local batch runs.
4. Read the generated executive analysis.

### Running locally

**Web panel (recommended):**

```bash
pip install -r requirements.txt
# Create a .env file with GEMINI_API_KEY=your_key
python -m uvicorn api:app --reload --app-dir src --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001` in your browser.

**CLI script (for local batch analysis):**

```bash
python src/main.py
# Output written to output/analise_executiva.md
```

### Environment variables

```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-flash-latest       # default
GEMINI_FALLBACK_MODELS=gemini-3-flash-preview,gemini-pro-latest
GEMINI_TIMEOUT_SECONDS=90
GEMINI_TRANSPORT=rest                  # use if REST works better than gRPC
```

If you hit SSL issues on a corporate network, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

### Deploying

The repo includes `render.yaml` for one-click deploy on Render. Set `GEMINI_API_KEY` as a secret in the Render dashboard and connect the repo.

*Note: Render's free tier sleeps after inactivity. First request may take a few seconds to wake.*

### Design decisions

Reasoning is documented here because it's the part worth reading.

- **Aggregated data, not raw.** LLMs have limited context. Feeding 100k order lines is worse than feeding 30 rows of KPIs. The engine assumes you already did the aggregation upstream — that's the analyst's job, and the point.
- **System prompt isolated in `prompts.py`.** The consultant's behavior lives outside application logic. Tuning the persona doesn't require touching code.
- **Temperature 0.3.** Executive analysis rewards consistency, not creativity. Same data should return roughly the same conclusions across runs.
- **Structured output enforced by prompt.** Five fixed sections (Summary → Indicators → Findings → Risks → Next Steps). Without this constraint, the LLM drifts.
- **Explicit anti-hallucination rules.** The system prompt forbids invented numbers and generic recommendations. This catches ~90% of bad outputs.
- **In-memory uploads.** Uploaded files are never persisted. Simplifies privacy and free-tier deploy.

### Roadmap

- [ ] Support for direct database connections (skip the export step)
- [ ] Chat-style follow-up questions on top of generated analysis
- [ ] Multi-language output (currently PT-BR by default)

---

## Português

### O que faz

Faça upload de uma ou mais planilhas. A engine lê as tabelas, alimenta na Gemini API com um system prompt cuidadosamente construído, e retorna uma análise executiva estruturada: Resumo Executivo, Indicadores-Chave, Achados, Riscos e Próximos Passos.

O valor não está no código — está na **engenharia de prompt**. O system prompt força a persona de um consultor sênior apresentando pro CEO, proíbe números inventados, exige cruzamento entre tabelas e trava a estrutura do output. Mesmo código + prompt diferente = produto diferente.

### Stack

- **Backend:** Python 3.11 · FastAPI · Google Generative AI SDK · pandas
- **Frontend:** HTML / CSS / JavaScript vanilla
- **Deploy:** Render (plano gratuito, `render.yaml` incluído)
- **Pipeline de dados:** Dashboard Power BI → export CSV agregado → engine

### Como funciona

1. Agregue seus dados no Power BI (ou qualquer BI) em tabelas-resumo pequenas (KPIs, breakdowns).
2. Exporte cada resumo como CSV ou Excel.
3. Suba no painel web — ou rode o script CLI pra batch local.
4. Leia a análise executiva gerada.

### Rodando localmente

**Painel web (recomendado):**

```bash
pip install -r requirements.txt
# Crie um .env com GEMINI_API_KEY=sua_chave
python -m uvicorn api:app --reload --app-dir src --host 127.0.0.1 --port 8001
```

Abra `http://127.0.0.1:8001` no navegador.

**Script CLI (batch local):**

```bash
python src/main.py
# Output salvo em output/analise_executiva.md
```

### Variáveis de ambiente

```env
GEMINI_API_KEY=sua_chave
GEMINI_MODEL=gemini-flash-latest       # padrão
GEMINI_FALLBACK_MODELS=gemini-3-flash-preview,gemini-pro-latest
GEMINI_TIMEOUT_SECONDS=90
GEMINI_TRANSPORT=rest                  # use se REST funcionar melhor que gRPC
```

Problemas de SSL em rede corporativa? Veja [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

### Deploy

O repositório inclui `render.yaml` pra deploy no Render. Configure `GEMINI_API_KEY` como secret no painel do Render e conecte o repositório.

*Nota: o plano gratuito do Render adormece após inatividade. A primeira requisição pode demorar alguns segundos.*

### Decisões de projeto

O raciocínio está documentado aqui porque é a parte que vale ler.

- **Dados agregados, não raw.** LLM tem contexto limitado. Alimentar 100k linhas de pedidos é pior que alimentar 30 linhas de KPIs. A engine assume que a agregação foi feita antes — é papel do analista, e é o ponto.
- **System prompt isolado em `prompts.py`.** O comportamento do consultor vive fora da lógica da aplicação. Ajustar a persona não exige tocar em código.
- **Temperature 0.3.** Análise executiva quer consistência, não criatividade. Mesmos dados devem gerar conclusões similares entre execuções.
- **Estrutura obrigatória forçada pelo prompt.** Cinco seções fixas (Resumo → Indicadores → Achados → Riscos → Próximos Passos). Sem esta restrição, o LLM desvia.
- **Regras explícitas anti-alucinação.** O system prompt proíbe números inventados e recomendações genéricas. Isso pega ~90% dos outputs ruins.
- **Upload em memória.** Arquivos enviados não são persistidos. Simplifica privacidade e deploy no plano gratuito.

### Roadmap

- [ ] Suporte a conexão direta com banco de dados (pular o export)
- [ ] Perguntas em chat sobre a análise gerada
- [ ] Output multi-idioma (atualmente PT-BR por padrão)

---

**Personal project · [Arthur Costa](https://linkedin.com/in/arthur-santos-costaa)**

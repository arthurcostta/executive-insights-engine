const fileInput = document.querySelector("#fileInput");
const dropzone = document.querySelector("#dropzone");
const uploadForm = document.querySelector("#uploadForm");
const fileList = document.querySelector("#fileList");
const analyzeButton = document.querySelector("#analyzeButton");
const statusDot = document.querySelector("#statusDot");
const statusText = document.querySelector("#statusText");
const fileCount = document.querySelector("#fileCount");
const tableCount = document.querySelector("#tableCount");
const rowCount = document.querySelector("#rowCount");
const runState = document.querySelector("#runState");
const generatedAt = document.querySelector("#generatedAt");
const tableSummary = document.querySelector("#tableSummary");
const analysisOutput = document.querySelector("#analysisOutput");
const progressBar = document.querySelector("#progressBar");
const copyButton = document.querySelector("#copyButton");
const downloadButton = document.querySelector("#downloadButton");

let selectedFiles = [];
let latestAnalysis = "";

function setStatus(state, text) {
  statusDot.className = `status-dot ${state}`;
  statusText.textContent = text;
  runState.textContent =
    state === "running" ? "IA ativa" : state === "success" ? "Concluído" : state === "error" ? "Erro" : "Pronto";
  progressBar.classList.toggle("active", state === "running");
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function renderFiles() {
  analyzeButton.disabled = selectedFiles.length === 0;
  fileCount.textContent = selectedFiles.length;

  if (selectedFiles.length === 0) {
    fileList.innerHTML = "";
    return;
  }

  fileList.innerHTML = selectedFiles
    .map(
      (file, index) => `
        <div class="file-item">
          <div>
            <span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
            <small>${formatBytes(file.size)}</small>
          </div>
          <button class="remove-file" type="button" data-index="${index}" title="Remover arquivo">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      `,
    )
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(markdown) {
  const escaped = escapeHtml(markdown);
  const lines = escaped.split(/\r?\n/);
  let html = "";
  let inList = false;

  for (const line of lines) {
    const trimmedLine = line.trim();

    if (line.startsWith("## ")) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += `<h2>${line.slice(3)}</h2>`;
      continue;
    }

    if (trimmedLine === "---" || trimmedLine === "***") {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += "<hr />";
      continue;
    }

    if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${line.slice(2).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")}</li>`;
      continue;
    }

    if (inList) {
      html += "</ul>";
      inList = false;
    }

    if (line.trim()) {
      html += `<p>${line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")}</p>`;
    }
  }

  if (inList) html += "</ul>";
  return html;
}

function getActionableError(message) {
  const normalized = message.toLowerCase();

  if (normalized.includes("certificado") || normalized.includes("certificate_verify_failed")) {
    return {
      title: "A IA não conseguiu acessar o Gemini",
      body:
        "A rede está interceptando o certificado HTTPS usado na chamada da IA. O painel está funcionando, mas a análise generativa foi bloqueada antes de chegar ao Gemini.",
      actions: [
        "Rode python -m pip install -r requirements.txt e reinicie o servidor.",
        "Se estiver em rede corporativa, teste com hotspot do celular.",
        "Para corrigir na rede da empresa, configure GEMINI_CA_BUNDLE no .env com o certificado raiz corporativo em .pem.",
      ],
    };
  }

  if (normalized.includes("tempo limite") || normalized.includes("read timed out") || normalized.includes("timeout")) {
    return {
      title: "A IA demorou para responder",
      body:
        "A primeira chamada pode passar do limite por aquecimento da conexão, latência temporária da API ou instabilidade da rede. Como a execução seguinte funcionou, os arquivos e a chave parecem corretos.",
      actions: [
      "Clique em Gerar análise com IA novamente.",
      "Mantenha GEMINI_TIMEOUT_SECONDS=60 no .env.",
      "Use GEMINI_MODEL=gemini-3.5-flash-lite para uma resposta mais rápida.",
      ],
    };
  }

  if (normalized.includes("10013") || normalized.includes("permission denied")) {
    return {
      title: "Conexão da IA bloqueada pelo Windows",
      body:
        "A saída para a API do Gemini foi negada pelo sistema, firewall, VPN ou proxy.",
      actions: [
        "Libere generativelanguage.googleapis.com na porta 443.",
        "Teste com outra rede para confirmar que os dados e a chave estão corretos.",
      ],
    };
  }

  return {
    title: "Não foi possível gerar a análise com IA",
    body: message,
    actions: [
      "Verifique a chave GEMINI_API_KEY, a conexão e o modelo configurado no .env.",
      "Use GEMINI_MODEL=gemini-3.5-flash-lite para priorizar velocidade.",
      "Configure GEMINI_FALLBACK_MODELS com modelos alternativos separados por vírgula.",
    ],
  };
}

function renderErrorMessage(message) {
  const error = getActionableError(message);
  analysisOutput.className = "analysis-output";
  analysisOutput.innerHTML = `
    <div class="error-card">
      <h4>${escapeHtml(error.title)}</h4>
      <p>${escapeHtml(error.body)}</p>
      <ul>
        ${error.actions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}
      </ul>
    </div>
  `;
}

function renderTables(tables) {
  const totalRows = tables.reduce((sum, table) => sum + table.rows, 0);
  tableCount.textContent = formatNumber(tables.length);
  rowCount.textContent = formatNumber(totalRows);

  if (tables.length === 0) {
    tableSummary.className = "table-summary empty-state";
    tableSummary.textContent = "Nenhuma tabela carregada.";
    return;
  }

  tableSummary.className = "table-summary";
  tableSummary.innerHTML = tables
    .map((table) => {
      const columns = table.columns
        .slice(0, 8)
        .map((column) => `<span>${escapeHtml(column)}</span>`)
        .join("");
      const extraColumns = table.columns.length > 8 ? `<span>+${table.columns.length - 8}</span>` : "";
      const truncated = table.truncated_for_prompt ? "Amostra usada no prompt" : "Tabela completa no prompt";

      return `
        <div class="table-row">
          <strong>${escapeHtml(table.table_name)}</strong>
          <span>${formatNumber(table.rows)} linhas · ${formatNumber(table.columns.length)} colunas</span>
          <small>${escapeHtml(table.source_file)} · ${truncated}</small>
          <div class="columns">${columns}${extraColumns}</div>
        </div>
      `;
    })
    .join("");
}

function updateSelectedFiles(files) {
  const merged = [...selectedFiles, ...Array.from(files)];
  const unique = new Map(merged.map((file) => [`${file.name}-${file.size}-${file.lastModified}`, file]));
  selectedFiles = Array.from(unique.values());
  renderFiles();
}

fileInput.addEventListener("change", (event) => {
  updateSelectedFiles(event.target.files);
  fileInput.value = "";
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragover");
  updateSelectedFiles(event.dataTransfer.files);
});

fileList.addEventListener("click", (event) => {
  const removeButton = event.target.closest(".remove-file");
  if (!removeButton) return;
  selectedFiles.splice(Number(removeButton.dataset.index), 1);
  renderFiles();
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (selectedFiles.length === 0) return;

  const formData = new FormData();
  selectedFiles.forEach((file) => formData.append("files", file));

  analyzeButton.disabled = true;
  copyButton.disabled = true;
  downloadButton.disabled = true;
  setStatus("running", "Chamando IA");
  analysisOutput.className = "analysis-output empty-state";
  analysisOutput.textContent = "IA analisando os dados enviados.";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();
    if (!response.ok) {
      if (result.detail && typeof result.detail === "object") {
        if (Array.isArray(result.detail.tables)) {
          renderTables(result.detail.tables);
        }
        if (result.detail.generated_at) {
          generatedAt.textContent = new Intl.DateTimeFormat("pt-BR", {
            dateStyle: "short",
            timeStyle: "short",
          }).format(new Date(result.detail.generated_at));
        }
        throw new Error(result.detail.message || "Falha ao gerar análise.");
      }
      throw new Error(result.detail || "Falha ao gerar análise.");
    }

    latestAnalysis = result.analysis;
    renderTables(result.tables || []);
    generatedAt.textContent = new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(result.generated_at));
    analysisOutput.className = "analysis-output";
    analysisOutput.innerHTML = renderMarkdown(result.analysis);
    copyButton.disabled = false;
    downloadButton.disabled = false;
    setStatus("success", "Análise concluída");
  } catch (error) {
    latestAnalysis = "";
    renderErrorMessage(error.message);
    setStatus("error", "Falha na análise");
  } finally {
    analyzeButton.disabled = selectedFiles.length === 0;
  }
});

copyButton.addEventListener("click", async () => {
  if (!latestAnalysis) return;
  await navigator.clipboard.writeText(latestAnalysis);
  setStatus("success", "Análise copiada");
});

downloadButton.addEventListener("click", () => {
  if (!latestAnalysis) return;
  const blob = new Blob([latestAnalysis], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "analise-executiva.md";
  link.click();
  URL.revokeObjectURL(url);
});

renderFiles();

const STAGES = ["分析师团队", "研究团队", "交易团队", "风险管理", "投资组合决策"];

const state = {
  formOptions: null,
  providerOptionsByValue: new Map(),
  modelOptionsByProvider: new Map(),
  currentProvider: null,
  backendUrlTouched: false,
  eventSource: null,
  currentRun: null,
  modelMode: {
    quick: "select",
    deep: "select",
  },
  stageStatus: new Map(STAGES.map((stage) => [stage, "pending"])),
};

const el = {};

function $(id) {
  return document.getElementById(id);
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function optionValue(option) {
  if (option && typeof option === "object" && "value" in option) {
    return option.value;
  }
  return option;
}

function optionLabel(option) {
  if (option && typeof option === "object") {
    return option.label ?? String(option.value ?? "");
  }
  return String(option);
}

function normalizeOptionsPayload(payload) {
  const defaults = payload?.defaults ?? {};
  const options = payload?.options ?? payload ?? {};
  return { defaults, options };
}

function setStatus(message, kind = "muted") {
  el.formStatus.textContent = message;
  el.formStatus.dataset.kind = kind;
  el.formCard.dataset.status = kind;
}

function setResponseVisible(visible) {
  el.responseEmpty.hidden = visible;
  el.responsePanel.hidden = !visible;
}

function populateSelect(select, options, selectedValue) {
  select.innerHTML = "";

  for (const option of options) {
    const value = String(optionValue(option) ?? "");
    const label = optionLabel(option);
    const item = document.createElement("option");
    item.value = value;
    item.textContent = label;
    select.appendChild(item);
  }

  if (selectedValue !== undefined && selectedValue !== null && selectedValue !== "") {
    select.value = String(selectedValue);
  } else if (select.options.length > 0) {
    select.selectedIndex = 0;
  }
}

function renderAnalysts(options, selected) {
  const selectedSet = new Set(asArray(selected).map(String));
  el.analysts.innerHTML = "";

  for (const option of asArray(options)) {
    const value = String(optionValue(option) ?? "");
    const label = optionLabel(option);

    const wrapper = document.createElement("label");
    wrapper.className = "chip";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "analysts";
    checkbox.value = value;
    checkbox.checked = selectedSet.has(value);

    const text = document.createElement("span");
    text.textContent = label;

    wrapper.append(checkbox, text);
    el.analysts.appendChild(wrapper);
  }
}

function getModelOptions(provider, mode) {
  const providerOptions = state.modelOptionsByProvider.get(provider) ?? {};
  return asArray(providerOptions[mode]);
}

function shouldUseTextInput(options) {
  const values = asArray(options).map((option) => String(optionValue(option) ?? ""));
  return values.length === 0 || values.every((value) => value.trim() === "");
}

function modelElementIds(mode) {
  return {
    select: mode === "quick" ? el.quickSelect : el.deepSelect,
    custom: mode === "quick" ? el.quickCustom : el.deepCustom,
    help: mode === "quick" ? el.quickHelp : el.deepHelp,
    field: mode === "quick" ? el.quickField : el.deepField,
  };
}

function setModelField(mode, provider, selectedValue) {
  const options = getModelOptions(provider, mode);
  const ids = modelElementIds(mode);
  const useText = shouldUseTextInput(options);
  state.modelMode[mode] = useText ? "input" : "select";

  if (useText) {
    ids.select.hidden = true;
    ids.custom.hidden = false;
    ids.custom.value = selectedValue ?? "";
    ids.help.textContent = options.length
      ? "当前提供方需要手动输入模型 ID。"
      : "请输入后端期望接收的模型 ID。";
    ids.field.dataset.mode = "input";
    return;
  }

  populateSelect(ids.select, options, selectedValue);
  ids.select.hidden = false;
  ids.custom.hidden = true;
  ids.help.textContent = "从后端提供的模型选项中选择。";
  ids.field.dataset.mode = "select";
}

function getModelFieldValue(mode) {
  const ids = modelElementIds(mode);
  if (state.modelMode[mode] === "input") {
    return ids.custom.value.trim();
  }
  return ids.select.value.trim();
}

function setProviderVisibility(provider) {
  document.querySelectorAll("[data-provider-field]").forEach((field) => {
    field.hidden = field.dataset.providerField !== provider;
  });
}

function updateBackendUrlDefault(provider, defaults) {
  const providerOption = state.providerOptionsByValue.get(provider);
  const nextValue = providerOption?.backend_url ?? defaults.backend_url ?? "";
  const currentValue = el.backendUrl.value.trim();

  if (!state.backendUrlTouched || currentValue === "" || currentValue === (defaults.backend_url ?? "")) {
    el.backendUrl.value = nextValue ?? "";
  }
}

function applyProvider(provider, defaults) {
  state.currentProvider = provider;
  setProviderVisibility(provider);
  updateBackendUrlDefault(provider, defaults);

  const quickDefault = defaults.quick_think_llm ?? "";
  const deepDefault = defaults.deep_think_llm ?? "";
  setModelField("quick", provider, quickDefault);
  setModelField("deep", provider, deepDefault);

  el.googleThinkingLevel.value = defaults.google_thinking_level ?? "";
  el.openaiReasoningEffort.value = defaults.openai_reasoning_effort ?? "";
  el.anthropicEffort.value = defaults.anthropic_effort ?? "";
}

function collectPayload() {
  const analysts = Array.from(el.analysts.querySelectorAll("input[type=checkbox]:checked")).map(
    (checkbox) => checkbox.value
  );

  return {
    ticker: el.ticker.value.trim().toUpperCase(),
    analysis_date: el.analysisDate.value,
    output_language: el.outputLanguage.value,
    analysts,
    research_depth: Number(el.researchDepth.value),
    llm_provider: el.llmProvider.value,
    backend_url: el.backendUrl.value.trim() || null,
    quick_think_llm: getModelFieldValue("quick"),
    deep_think_llm: getModelFieldValue("deep"),
    google_thinking_level: el.googleThinkingLevel.hidden ? null : el.googleThinkingLevel.value || null,
    openai_reasoning_effort: el.openaiReasoningEffort.hidden
      ? null
      : el.openaiReasoningEffort.value || null,
    anthropic_effort: el.anthropicEffort.hidden ? null : el.anthropicEffort.value || null,
  };
}

function createOptionItem(label, value) {
  return {
    label,
    value,
  };
}

function renderStageProgress() {
  el.stageProgress.innerHTML = "";

  for (const stage of STAGES) {
    const item = document.createElement("li");
    const status = state.stageStatus.get(stage) ?? "pending";
    item.className = `stage-pill stage-pill--${status}`;
    item.innerHTML = `<span>${stage}</span><strong>${stageStatusLabel(status)}</strong>`;
    el.stageProgress.appendChild(item);
  }
}

function stageStatusLabel(status) {
  switch (status) {
    case "running":
      return "进行中";
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    default:
      return "等待中";
  }
}

function setStageStatus(step, status) {
  if (!step) {
    return;
  }
  state.stageStatus.set(step, status);
  renderStageProgress();
}

function appendTimelineEvent(eventName, payload) {
  const item = document.createElement("li");
  item.className = `timeline-item timeline-item--${eventName}`;
  item.innerHTML = `
    <div class="timeline-stamp">${payload.timestamp ?? ""}</div>
    <div class="timeline-body">
      <div class="timeline-title">${payload.step ?? eventName}</div>
      <p>${payload.message ?? ""}</p>
    </div>
  `;
  el.eventTimeline.prepend(item);
}

function resetRunState() {
  closeEventSource();
  state.currentRun = null;
  state.stageStatus = new Map(STAGES.map((stage) => [stage, "pending"]));
  renderStageProgress();
  el.eventTimeline.innerHTML = "";
  el.responseSubmissionId.textContent = "-";
  el.responseRunStatus.textContent = "-";
  el.responseCurrentStep.textContent = "-";
  el.responseSavedPath.textContent = "-";
  el.responseReportPath.textContent = "-";
  el.responsePayload.textContent = "";
  el.errorDetails.textContent = "";
  el.errorBlock.hidden = true;
}

function renderRunRecord(run) {
  state.currentRun = run;
  el.responseSubmissionId.textContent = run.run_id ?? "-";
  el.responseRunStatus.textContent = run.status ?? "-";
  el.responseCurrentStep.textContent = run.current_step ?? "-";
  el.responseSavedPath.textContent = run.run_dir ?? "-";
  el.responseReportPath.textContent = run.report_path ?? run.error_path ?? "-";
}

function updateRunStatus(status, currentStep) {
  el.responseRunStatus.textContent = status;
  el.responseCurrentStep.textContent = currentStep || "-";
}

function handleRunEvent(eventName, payload) {
  appendTimelineEvent(eventName, payload);

  if (payload.step) {
    el.responseCurrentStep.textContent = payload.step;
  }

  switch (eventName) {
    case "run_created":
      updateRunStatus("queued", payload.step);
      break;
    case "step_started":
      updateRunStatus("running", payload.step);
      setStageStatus(payload.step, "running");
      break;
    case "step_updated":
      updateRunStatus("running", payload.step);
      break;
    case "step_completed":
      setStageStatus(payload.step, "completed");
      updateRunStatus("running", payload.step);
      break;
    case "run_completed":
      updateRunStatus("completed", payload.step);
      el.responseReportPath.textContent = payload.report_path ?? "-";
      el.responsePayload.textContent = payload.markdown ?? "";
      STAGES.forEach((stage) => {
        if (state.stageStatus.get(stage) === "running") {
          setStageStatus(stage, "completed");
        }
      });
      closeEventSource();
      setStatus("分析完成，结果已保存到本地目录。");
      break;
    case "run_failed":
      updateRunStatus("failed", payload.step);
      el.responseReportPath.textContent = payload.error_path ?? "-";
      el.errorDetails.textContent = payload.traceback ?? payload.message ?? "";
      el.errorBlock.hidden = false;
      if (payload.step) {
        setStageStatus(payload.step, "failed");
      }
      closeEventSource();
      setStatus("运行失败，错误详情已保存到本地目录。", "error");
      break;
    default:
      break;
  }
}

function subscribeToRun(runId) {
  closeEventSource();
  const source = new EventSource(`/api/runs/${runId}/events`);
  state.eventSource = source;

  for (const eventName of ["run_created", "step_started", "step_updated", "step_completed", "run_completed", "run_failed"]) {
    source.addEventListener(eventName, (event) => {
      const payload = JSON.parse(event.data);
      handleRunEvent(eventName, payload);
    });
  }

  source.onerror = () => {
    if (el.responseRunStatus.textContent === "completed" || el.responseRunStatus.textContent === "failed") {
      closeEventSource();
      return;
    }
    setStatus("事件流连接异常，请稍后刷新页面查看状态。", "error");
  };
}

function closeEventSource() {
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
}

function setLoading(loading) {
  el.submitButton.disabled = loading;
  el.submitButton.textContent = loading ? "正在启动..." : "提交参数";
}

async function loadFormOptions() {
  setStatus("正在加载表单选项...");
  const response = await fetch("/api/form-options");
  if (!response.ok) {
    throw new Error(`加载表单选项失败（${response.status}）`);
  }

  const payload = normalizeOptionsPayload(await response.json());
  state.formOptions = payload;

  const defaults = payload.defaults ?? {};
  const options = payload.options ?? {};

  state.providerOptionsByValue = new Map(
    asArray(options.providers).map((provider) => [String(optionValue(provider) ?? ""), provider])
  );
  state.modelOptionsByProvider = new Map(Object.entries(options.model_options ?? {}));

  populateSelect(
    el.outputLanguage,
    asArray(options.output_languages).map((option) =>
      createOptionItem(optionLabel(option), String(optionValue(option) ?? ""))
    ),
    defaults.output_language
  );

  populateSelect(
    el.researchDepth,
    asArray(options.research_depths).map((option) =>
      createOptionItem(optionLabel(option), String(optionValue(option) ?? ""))
    ),
    defaults.research_depth
  );

  populateSelect(
    el.llmProvider,
    asArray(options.providers).map((provider) =>
      createOptionItem(optionLabel(provider), String(optionValue(provider) ?? ""))
    ),
    defaults.llm_provider
  );

  renderAnalysts(options.analysts, defaults.analysts);

  el.ticker.value = defaults.ticker ?? "";
  el.analysisDate.value = defaults.analysis_date ?? "";
  el.backendUrl.value = defaults.backend_url ?? "";
  el.backendUrl.dataset.default = defaults.backend_url ?? "";

  const provider = defaults.llm_provider ?? el.llmProvider.value;
  applyProvider(provider, defaults);
  setStatus("表单选项已加载。");
}

function syncProviderUI() {
  const provider = el.llmProvider.value;
  const defaults = state.formOptions?.defaults ?? {};
  applyProvider(provider, defaults);
}

function wireEvents() {
  el.llmProvider.addEventListener("change", syncProviderUI);

  el.backendUrl.addEventListener("input", () => {
    state.backendUrlTouched = true;
  });

  el.ticker.addEventListener("blur", () => {
    el.ticker.value = el.ticker.value.trim().toUpperCase();
  });

  el.submissionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.formOptions) {
      setStatus("表单选项尚未加载完成。", "error");
      return;
    }

    const payload = collectPayload();
    resetRunState();
    setResponseVisible(true);
    setLoading(true);
    setStatus("正在启动分析任务...");

    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const responseText = await response.text();
      if (!response.ok) {
        throw new Error(responseText || `启动失败（${response.status}）`);
      }

      const run = responseText ? JSON.parse(responseText) : {};
      renderRunRecord(run);
      subscribeToRun(run.run_id);
      setStatus("任务已创建，正在接收实时进度...");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "启动失败。", "error");
      setResponseVisible(false);
    } finally {
      setLoading(false);
    }
  });
}

function cacheElements() {
  el.formStatus = $("form-status");
  el.formCard = document.querySelector(".card");
  el.responseEmpty = $("response-empty");
  el.responsePanel = $("response-panel");
  el.responseSubmissionId = $("response-submission-id");
  el.responseRunStatus = $("response-run-status");
  el.responseCurrentStep = $("response-current-step");
  el.responseSavedPath = $("response-saved-path");
  el.responseReportPath = $("response-report-path");
  el.responsePayload = $("response-payload");
  el.submitButton = $("submit-button");
  el.submissionForm = $("submission-form");
  el.ticker = $("ticker");
  el.analysisDate = $("analysis_date");
  el.outputLanguage = $("output_language");
  el.researchDepth = $("research_depth");
  el.analysts = $("analysts");
  el.llmProvider = $("llm_provider");
  el.backendUrl = $("backend_url");
  el.quickSelect = $("quick_think_llm");
  el.quickCustom = $("quick_think_llm_custom");
  el.quickHelp = document.querySelector('[data-model-help="quick"]');
  el.quickField = document.querySelector('[data-model-field="quick"]');
  el.deepSelect = $("deep_think_llm");
  el.deepCustom = $("deep_think_llm_custom");
  el.deepHelp = document.querySelector('[data-model-help="deep"]');
  el.deepField = document.querySelector('[data-model-field="deep"]');
  el.googleThinkingLevel = $("google_thinking_level");
  el.openaiReasoningEffort = $("openai_reasoning_effort");
  el.anthropicEffort = $("anthropic_effort");
  el.stageProgress = $("stage-progress");
  el.eventTimeline = $("event-timeline");
  el.errorDetails = $("error-details");
  el.errorBlock = $("error-block");
}

function populateStaticChoices() {
  populateSelect(
    el.googleThinkingLevel,
    [
      createOptionItem("高", "high"),
      createOptionItem("最小", "minimal"),
    ],
    ""
  );

  populateSelect(
    el.openaiReasoningEffort,
    [
      createOptionItem("中等", "medium"),
      createOptionItem("高", "high"),
      createOptionItem("低", "low"),
    ],
    ""
  );

  populateSelect(
    el.anthropicEffort,
    [
      createOptionItem("高", "high"),
      createOptionItem("中等", "medium"),
      createOptionItem("低", "low"),
    ],
    ""
  );
}

async function main() {
  cacheElements();
  populateStaticChoices();
  renderStageProgress();
  wireEvents();

  try {
    await loadFormOptions();
    syncProviderUI();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "加载表单选项失败。", "error");
  }
}

document.addEventListener("DOMContentLoaded", main);

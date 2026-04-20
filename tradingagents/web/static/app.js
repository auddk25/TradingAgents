const STAGES = ["分析师团队", "研究团队", "交易团队", "风险管理", "投资组合决策"];

const state = {
  formOptions: null,
  providerOptionsByValue: new Map(),
  modelOptionsByProvider: new Map(),
  currentProvider: null,
  backendUrlTouched: false,
  eventSource: null,
  currentRun: null,
  modelTouched: {
    quick: false,
    deep: false,
  },
  modelMode: {
    main: "select",
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

function closeAllHelpPopovers() {
  for (const trigger of el.helpTriggers) {
    const targetId = trigger.dataset.helpFor;
    const popover = $(targetId ? `${targetId}_help` : "");
    if (!popover) {
      continue;
    }
    popover.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  }
}

function setHelpPopoverVisibility(trigger, visible) {
  const targetId = trigger.dataset.helpFor;
  const popover = $(targetId ? `${targetId}_help` : "");
  if (!popover || !popover.textContent.trim()) {
    return;
  }
  popover.hidden = !visible;
  trigger.setAttribute("aria-expanded", visible ? "true" : "false");
}

function normalizeOptionsPayload(payload) {
  const defaults = payload?.defaults ?? {};
  const options = payload?.options ?? payload ?? {};
  return { defaults, options, field_help: payload?.field_help ?? {} };
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
    if (select.value !== String(selectedValue) && select.options.length > 0) {
      select.selectedIndex = 0;
    }
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
    select:
      mode === "main"
        ? el.mainSelect
        : mode === "quick"
          ? el.quickSelect
          : el.deepSelect,
    custom:
      mode === "main"
        ? el.mainCustom
        : mode === "quick"
          ? el.quickCustom
          : el.deepCustom,
    help:
      mode === "main"
        ? el.mainHelp
        : mode === "quick"
          ? el.quickHelp
          : el.deepHelp,
    modeHint:
      mode === "main"
        ? el.mainModeHint
        : mode === "quick"
          ? el.quickModeHint
          : el.deepModeHint,
    field:
      mode === "main"
        ? el.mainField
        : mode === "quick"
          ? el.quickField
          : el.deepField,
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
    ids.modeHint.textContent = "当前提供方需要手动输入模型 ID。";
    ids.field.dataset.mode = "input";
    return;
  }

  populateSelect(ids.select, options, selectedValue);
  ids.select.hidden = false;
  ids.custom.hidden = true;
  ids.modeHint.textContent = "从后端提供的模型选项中选择。";
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
  state.modelTouched.quick = false;
  state.modelTouched.deep = false;
  setProviderVisibility(provider);
  updateBackendUrlDefault(provider, defaults);

  const mainDefault = defaults.main_model ?? defaults.quick_think_llm ?? "";
  const quickDefault = defaults.quick_think_llm ?? "";
  const deepDefault = defaults.deep_think_llm ?? "";
  setModelField("main", provider, mainDefault);
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
  el.responseResultHint.textContent = "";
  el.responseErrorPath.textContent = "-";
  el.responseErrorHint.textContent = "";
  el.errorCard.hidden = true;
}

function renderRunRecord(run) {
  state.currentRun = run;
  el.responseSubmissionId.textContent = run.run_id ?? "-";
  el.responseRunStatus.textContent = run.status ?? "-";
  el.responseCurrentStep.textContent = run.current_step ?? "-";
  el.responseSavedPath.textContent = run.run_dir ?? "-";
  el.responseReportPath.textContent = run.report_path ?? "-";
  el.responseErrorPath.textContent = run.error_path ?? "-";
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
      el.responseResultHint.textContent = "完整结果请查看结果文件路径。";
      el.errorCard.hidden = true;
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
      el.responseErrorPath.textContent = payload.error_path ?? "-";
      el.responseErrorHint.textContent = "完整错误请查看错误文件路径。";
      el.errorCard.hidden = false;
      if (payload.step) {
        setStageStatus(payload.step, "failed");
      }
      closeEventSource();
      setStatus("运行失败，错误文件已保存到本地目录。", "error");
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

  populateSelect(
    el.mainSelect,
    asArray(options.model_options?.[defaults.llm_provider ?? "openai"]?.main).map((option) =>
      createOptionItem(optionLabel(option), String(optionValue(option) ?? ""))
    ),
    defaults.main_model ?? defaults.quick_think_llm
  );

  renderAnalysts(options.analysts, defaults.analysts);

  el.ticker.value = defaults.ticker ?? "";
  el.analysisDate.value = defaults.analysis_date ?? "";
  el.backendUrl.value = defaults.backend_url ?? "";
  el.backendUrl.dataset.default = defaults.backend_url ?? "";
  applyFieldHelp(payload.field_help ?? {});

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

  const syncAdvancedModels = () => {
    const provider = el.llmProvider.value;
    const mainValue = getModelFieldValue("main");
    if (!state.modelTouched.quick) {
      setModelField("quick", provider, mainValue);
    }
    if (!state.modelTouched.deep) {
      setModelField("deep", provider, mainValue);
    }
  };

  el.mainSelect.addEventListener("change", syncAdvancedModels);
  el.mainSelect.addEventListener("input", syncAdvancedModels);
  el.mainCustom.addEventListener("input", syncAdvancedModels);
  el.mainCustom.addEventListener("change", syncAdvancedModels);

  el.quickSelect.addEventListener("change", () => {
    state.modelTouched.quick = true;
  });
  el.quickCustom.addEventListener("input", () => {
    state.modelTouched.quick = true;
  });
  el.quickCustom.addEventListener("change", () => {
    state.modelTouched.quick = true;
  });
  el.deepSelect.addEventListener("change", () => {
    state.modelTouched.deep = true;
  });
  el.deepCustom.addEventListener("input", () => {
    state.modelTouched.deep = true;
  });
  el.deepCustom.addEventListener("change", () => {
    state.modelTouched.deep = true;
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

  for (const trigger of el.helpTriggers) {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();

      const isOpen = trigger.getAttribute("aria-expanded") === "true";
      closeAllHelpPopovers();
      if (!isOpen) {
        setHelpPopoverVisibility(trigger, true);
      }
    });

    trigger.addEventListener("mouseenter", () => {
      closeAllHelpPopovers();
      setHelpPopoverVisibility(trigger, true);
    });

    trigger.addEventListener("focus", () => {
      closeAllHelpPopovers();
      setHelpPopoverVisibility(trigger, true);
    });
  }

  document.addEventListener("click", (event) => {
    if (
      event.target instanceof Element &&
      (event.target.closest(".field-help") || event.target.closest(".field-help-popover"))
    ) {
      return;
    }
    closeAllHelpPopovers();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllHelpPopovers();
    }
  });

  document.addEventListener("pointerover", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    if (event.target.closest(".field-help")) {
      return;
    }

    if (event.target.closest(".field-help-popover")) {
      return;
    }

    closeAllHelpPopovers();
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
  el.submitButton = $("submit-button");
  el.submissionForm = $("submission-form");
  el.ticker = $("ticker");
  el.analysisDate = $("analysis_date");
  el.outputLanguage = $("output_language");
  el.researchDepth = $("research_depth");
  el.analysts = $("analysts");
  el.llmProvider = $("llm_provider");
  el.backendUrl = $("backend_url");
  el.advancedOptions = document.querySelector(".advanced-panel");
  el.mainSelect = $("main_model");
  el.mainCustom = $("main_model_custom");
  el.mainHelp = $("main_model_help");
  el.mainModeHint = $("main_model_mode_hint");
  el.mainField = document.querySelector('[data-model-field="main"]');
  el.quickSelect = $("quick_think_llm");
  el.quickCustom = $("quick_think_llm_custom");
  el.quickHelp = $("quick_think_llm_help");
  el.quickModeHint = $("quick_think_llm_mode_hint");
  el.quickField = document.querySelector('[data-model-field="quick"]');
  el.deepSelect = $("deep_think_llm");
  el.deepCustom = $("deep_think_llm_custom");
  el.deepHelp = $("deep_think_llm_help");
  el.deepModeHint = $("deep_think_llm_mode_hint");
  el.deepField = document.querySelector('[data-model-field="deep"]');
  el.googleThinkingLevel = $("google_thinking_level");
  el.openaiReasoningEffort = $("openai_reasoning_effort");
  el.anthropicEffort = $("anthropic_effort");
  el.researchDepthHelp = $("research_depth_help");
  el.googleThinkingLevelHelp = $("google_thinking_level_help");
  el.openaiReasoningEffortHelp = $("openai_reasoning_effort_help");
  el.anthropicEffortHelp = $("anthropic_effort_help");
  el.stageProgress = $("stage-progress");
  el.eventTimeline = $("event-timeline");
  el.responseResultHint = $("response-result-hint");
  el.responseErrorPath = $("response-error-path");
  el.responseErrorHint = $("response-error-hint");
  el.errorCard = $("error-card");
  el.helpTriggers = Array.from(document.querySelectorAll(".field-help-trigger"));
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

function applyFieldHelp(fieldHelp) {
  const helpMap = {
    research_depth: el.researchDepthHelp,
    main_model: el.mainHelp,
    quick_think_llm: el.quickHelp,
    deep_think_llm: el.deepHelp,
    google_thinking_level: el.googleThinkingLevelHelp,
    openai_reasoning_effort: el.openaiReasoningEffortHelp,
    anthropic_effort: el.anthropicEffortHelp,
  };

  for (const [fieldName, target] of Object.entries(helpMap)) {
    const text = fieldHelp[fieldName] ?? "";
    target.textContent = text;
    target.hidden = true;
  }

  for (const trigger of el.helpTriggers) {
    const fieldName = trigger.dataset.helpFor;
    const hasText = Boolean(fieldName && (fieldHelp[fieldName] ?? "").trim());
    trigger.hidden = !hasText;
    trigger.setAttribute("aria-expanded", "false");
  }
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

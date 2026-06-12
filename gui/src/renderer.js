const state = {
  tablebaseDir: null,
  tablebases: [],
  selected: null,
};

const els = {
  chooseDatabaseBtn: document.getElementById("chooseDatabaseBtn"),
  databaseSelect: document.getElementById("databaseSelect"),
  databasePath: document.getElementById("databasePath"),
  boardSize: document.getElementById("boardSize"),
  fileSize: document.getElementById("fileSize"),
  updatedAt: document.getElementById("updatedAt"),
  status: document.getElementById("status"),
  emptyState: document.getElementById("emptyState"),
  explorerFrame: document.getElementById("explorerFrame"),
};

function formatBytes(bytes) {
  if (!bytes) {
    return "-";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatDate(timestamp) {
  if (!timestamp) {
    return "-";
  }
  return new Date(timestamp).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function setStatus(message, kind = "neutral") {
  els.status.textContent = message;
  els.status.dataset.kind = kind;
}

function tablebaseLabel(tablebase) {
  return `${tablebase.m} x ${tablebase.n}  -  ${formatBytes(tablebase.sizeBytes)}`;
}

function renderDatabaseList() {
  els.databaseSelect.innerHTML = "";

  if (!state.tablebases.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No tablebases in default folder";
    els.databaseSelect.appendChild(option);
    return;
  }

  for (const tablebase of state.tablebases) {
    const option = document.createElement("option");
    option.value = tablebase.tablebasePath;
    option.textContent = tablebaseLabel(tablebase);
    els.databaseSelect.appendChild(option);
  }

  if (state.selected) {
    els.databaseSelect.value = state.selected.tablebasePath;
  }
}

function renderSelected() {
  const tablebase = state.selected;
  if (!tablebase) {
    els.databasePath.textContent = "No database selected";
    els.boardSize.textContent = "-";
    els.fileSize.textContent = "-";
    els.updatedAt.textContent = "-";
    return;
  }

  els.databasePath.textContent = tablebase.tablebasePath;
  els.boardSize.textContent = `${tablebase.m} x ${tablebase.n}`;
  els.fileSize.textContent = formatBytes(tablebase.sizeBytes);
  els.updatedAt.textContent = formatDate(tablebase.updatedAt);
}

async function loadExplorer(tablebase) {
  state.selected = tablebase;
  state.tablebaseDir = tablebase.tablebaseDir;
  renderDatabaseList();
  renderSelected();

  const sizeHint =
    tablebase.sizeBytes > 20 * 1024 * 1024
      ? "Large database — loading may take 1–3 minutes."
      : "Loading database…";
  setStatus(`${sizeHint} (${tablebase.m} x ${tablebase.n})`);

  const { url } = await window.colApp.startGui({
    m: tablebase.m,
    n: tablebase.n,
    tablebaseDir: tablebase.tablebaseDir,
  });

  els.explorerFrame.src = url;
  els.explorerFrame.classList.add("visible");
  els.emptyState.classList.add("hidden");
  setStatus(`Loaded ${tablebase.m} x ${tablebase.n}`, "ok");
}

async function chooseDatabase() {
  const tablebase = await window.colApp.chooseTablebaseFile();
  if (!tablebase) {
    return;
  }

  const payload = await window.colApp.listTablebases(tablebase.tablebaseDir);
  state.tablebaseDir = tablebase.tablebaseDir;
  state.tablebases = payload.tablebases;

  const selected =
    state.tablebases.find((item) => item.tablebasePath === tablebase.tablebasePath) || tablebase;
  await loadExplorer(selected);
}

els.chooseDatabaseBtn.addEventListener("click", () => {
  chooseDatabase().catch((error) => setStatus(error.message, "error"));
});

els.databaseSelect.addEventListener("change", () => {
  const selected = state.tablebases.find(
    (tablebase) => tablebase.tablebasePath === els.databaseSelect.value,
  );
  if (selected) {
    loadExplorer(selected).catch((error) => setStatus(error.message, "error"));
  }
});

window.colApp.onGuiStatus((payload) => {
  if (payload.status === "loading") {
    setStatus(`Loading tablebase for ${payload.m} x ${payload.n}…`);
  } else if (payload.status === "stopped") {
    setStatus("Explorer stopped.", "error");
  }
});

window.colApp.onGuiLog((line) => {
  const text = line.trim();
  if (text) {
    setStatus(text);
  }
});

async function boot() {
  const initial = await window.colApp.initialState();
  state.tablebaseDir = initial.tablebaseDir;
  state.tablebases = initial.tablebases;
  state.selected = state.tablebases[0] || null;
  renderDatabaseList();

  if (state.selected) {
    await loadExplorer(state.selected);
  } else {
    renderSelected();
    setStatus("Choose a tablebase file.");
  }
}

boot().catch((error) => setStatus(error.message, "error"));

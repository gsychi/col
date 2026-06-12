const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const net = require("net");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const PYTHON_DIR = path.join(ROOT, "python");
const GUI_PATH = path.join(PYTHON_DIR, "gui_server.py");
const SOLVER_PATH = path.join(ROOT, "col-solve");
const DEFAULT_TABLEBASE_DIR = path.join(ROOT, "data", "tablebases");
const TABLEBASE_NAME_RE = /^(\d+)x(\d+)_(sym|nosym)\.pkl$/;

let mainWindow = null;
let guiProcess = null;
let solverProcess = null;
let guiUrl = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1120,
    height: 760,
    minWidth: 860,
    minHeight: 560,
    title: "Col Tablebase",
    backgroundColor: "#f6f6f4",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer.html"));
  mainWindow.maximize();
}

function send(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

function parseTablebaseFile(filePath) {
  const match = TABLEBASE_NAME_RE.exec(path.basename(filePath));
  if (!match) {
    throw new Error("Tablebase filename must look like 5x7_sym.pkl");
  }
  return {
    m: Number(match[1]),
    n: Number(match[2]),
    symmetry: match[3],
    tablebaseDir: path.dirname(filePath),
    tablebasePath: filePath,
  };
}

function listTablebases(tablebaseDir) {
  if (!fs.existsSync(tablebaseDir)) {
    return [];
  }
  return fs
    .readdirSync(tablebaseDir)
    .filter((name) => TABLEBASE_NAME_RE.test(name))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map((name) => {
      const fullPath = path.join(tablebaseDir, name);
      const parsed = parseTablebaseFile(fullPath);
      const stat = fs.statSync(fullPath);
      return {
        ...parsed,
        sizeBytes: stat.size,
        updatedAt: stat.mtimeMs,
      };
    });
}

function solverArgs({ m, n, tablebaseDir, threads, progress, noTablebase }) {
  const args = ["--m", String(m), "--n", String(n)];
  if (threads) {
    args.push("--threads", String(threads));
  }
  if (tablebaseDir) {
    args.push("--tablebase-dir", tablebaseDir);
  }
  if (progress) {
    args.push("--progress");
  }
  if (noTablebase) {
    args.push("--no-tablebase");
  }
  return args;
}

function killProcess(child) {
  if (!child || child.killed) {
    return;
  }
  child.kill("SIGTERM");
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

/** Poll until the Python GUI server is accepting TCP connections. */
function waitForPort(host, port, timeoutMs = 600000) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const attempt = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`GUI server did not start within ${Math.round(timeoutMs / 1000)}s`));
        return;
      }
      const socket = net.connect({ host, port }, () => {
        socket.end();
        resolve();
      });
      socket.on("error", () => {
        socket.destroy();
        setTimeout(attempt, 300);
      });
    };
    attempt();
  });
}

function startGui({ m, n, tablebaseDir }) {
  return new Promise(async (resolve, reject) => {
    killProcess(guiProcess);
    guiProcess = null;
    guiUrl = null;

    const port = await freePort();
    const host = "127.0.0.1";
    const args = [
      "-u",
      GUI_PATH,
      "--m",
      String(m),
      "--n",
      String(n),
      "--host",
      host,
      "--port",
      String(port),
      "--tablebase-dir",
      tablebaseDir || DEFAULT_TABLEBASE_DIR,
    ];
    send("gui-status", { status: "loading", m, n });
    const child = spawn("python3", args, {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: PYTHON_DIR },
    });
    guiProcess = child;

    let settled = false;
    let announcedUrl = null;

    const finish = async (url) => {
      if (settled) {
        return;
      }
      try {
        const parsed = new URL(url);
        await waitForPort(parsed.hostname, Number(parsed.port));
        settled = true;
        guiUrl = url;
        send("gui-status", { status: "running", url });
        resolve({ url });
      } catch (error) {
        settled = true;
        reject(error);
      }
    };

    child.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      send("gui-log", text);
      const match = /Col tablebase GUI:\s+(http:\/\/\S+)/.exec(text);
      if (match) {
        announcedUrl = match[1];
        finish(announcedUrl).catch((error) => {
          if (!settled) {
            settled = true;
            reject(error);
          }
        });
      }
    });

    child.stderr.on("data", (chunk) => {
      send("gui-log", chunk.toString());
    });

    child.on("error", (error) => {
      if (!settled) {
        settled = true;
        reject(error);
      }
    });

    child.on("exit", (code, signal) => {
      send("gui-status", { status: "stopped", code, signal });
      if (!settled) {
        settled = true;
        reject(new Error(`GUI server exited before startup (${code ?? signal})`));
      }
    });
  });
}

function parseSolverLine(line) {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }
  const stateMatch = /states searched:\s+(\d+)(?:\s+\|\s+memo:\s+(\d+))?(?:\s+\|\s+([0-9.]+)\/s)?(?:\s+\|\s+([0-9.]+)s)?/.exec(trimmed);
  if (stateMatch) {
    return {
      type: "progress",
      states: Number(stateMatch[1]),
      memo: stateMatch[2] ? Number(stateMatch[2]) : null,
      rate: stateMatch[3] ? Number(stateMatch[3]) : null,
      elapsed: stateMatch[4] ? Number(stateMatch[4]) : null,
      raw: trimmed,
    };
  }

  const savedMatch = /tablebase saved:\s+(.+)\s+\(([0-9.]+)\s+MB\)/.exec(trimmed);
  if (savedMatch) {
    return { type: "saved", path: savedMatch[1], sizeMb: Number(savedMatch[2]), raw: trimmed };
  }

  const resultMatch = /^(\d+)\s+x\s+(\d+):\s+(P[12])\s+wins$/.exec(trimmed);
  if (resultMatch) {
    return {
      type: "result",
      m: Number(resultMatch[1]),
      n: Number(resultMatch[2]),
      winner: resultMatch[3],
      raw: trimmed,
    };
  }

  return { type: "line", raw: trimmed };
}

function runSolver(options) {
  if (solverProcess) {
    throw new Error("Solver is already running");
  }

  const args = solverArgs(options);
  const child = spawn(SOLVER_PATH, args, { cwd: ROOT });
  solverProcess = child;
  send("solver-status", { status: "running", args });

  const handleChunk = (chunk) => {
    const normalized = chunk.toString().replace(/\r/g, "\n");
    for (const line of normalized.split("\n")) {
      const parsed = parseSolverLine(line);
      if (parsed) {
        send("solver-output", parsed);
      }
    }
  };

  child.stdout.on("data", handleChunk);
  child.stderr.on("data", handleChunk);

  child.on("error", (error) => {
    send("solver-status", { status: "error", message: error.message });
    solverProcess = null;
  });

  child.on("exit", (code, signal) => {
    send("solver-status", { status: "stopped", code, signal });
    solverProcess = null;
  });

  return { ok: true, args };
}

ipcMain.handle("app:initial-state", () => ({
  root: ROOT,
  tablebaseDir: DEFAULT_TABLEBASE_DIR,
  tablebases: listTablebases(DEFAULT_TABLEBASE_DIR),
  guiUrl,
}));

ipcMain.handle("tablebase:choose-file", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Choose Col Tablebase",
    defaultPath: DEFAULT_TABLEBASE_DIR,
    properties: ["openFile"],
    filters: [{ name: "Col tablebase", extensions: ["pkl"] }],
  });
  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return parseTablebaseFile(result.filePaths[0]);
});

ipcMain.handle("tablebase:choose-dir", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Choose Tablebase Directory",
    defaultPath: DEFAULT_TABLEBASE_DIR,
    properties: ["openDirectory", "createDirectory"],
  });
  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  const tablebaseDir = result.filePaths[0];
  return { tablebaseDir, tablebases: listTablebases(tablebaseDir) };
});

ipcMain.handle("tablebase:list", (_event, tablebaseDir) => ({
  tablebaseDir,
  tablebases: listTablebases(tablebaseDir),
}));

ipcMain.handle("gui:start", (_event, options) => startGui(options));

ipcMain.handle("solver:start", (_event, options) => runSolver(options));

ipcMain.handle("solver:stop", () => {
  killProcess(solverProcess);
  solverProcess = null;
  return { ok: true };
});

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  killProcess(guiProcess);
  killProcess(solverProcess);
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  killProcess(guiProcess);
  killProcess(solverProcess);
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

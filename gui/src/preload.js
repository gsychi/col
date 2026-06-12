const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("colApp", {
  initialState: () => ipcRenderer.invoke("app:initial-state"),
  chooseTablebaseFile: () => ipcRenderer.invoke("tablebase:choose-file"),
  chooseTablebaseDir: () => ipcRenderer.invoke("tablebase:choose-dir"),
  listTablebases: (tablebaseDir) => ipcRenderer.invoke("tablebase:list", tablebaseDir),
  startGui: (options) => ipcRenderer.invoke("gui:start", options),
  startSolver: (options) => ipcRenderer.invoke("solver:start", options),
  stopSolver: () => ipcRenderer.invoke("solver:stop"),
  onGuiStatus: (handler) => ipcRenderer.on("gui-status", (_event, payload) => handler(payload)),
  onGuiLog: (handler) => ipcRenderer.on("gui-log", (_event, payload) => handler(payload)),
  onSolverStatus: (handler) => ipcRenderer.on("solver-status", (_event, payload) => handler(payload)),
  onSolverOutput: (handler) => ipcRenderer.on("solver-output", (_event, payload) => handler(payload)),
});

import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("interviewPilotDesktop", {
  getSettings: () => ipcRenderer.invoke("settings:get"),
  setSettings: (patch: Record<string, unknown>) => ipcRenderer.invoke("settings:set", patch),
  notify: (title: string, body: string) => ipcRenderer.invoke("notify", title, body),
  openExternal: (url: string) => ipcRenderer.invoke("open-external", url),
  onShortcut: (cb: (action: string) => void) => {
    const listener = (_: Electron.IpcRendererEvent, action: string) => cb(action);
    ipcRenderer.on("shortcut", listener);
    return () => ipcRenderer.removeListener("shortcut", listener);
  },
});

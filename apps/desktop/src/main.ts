import { app, BrowserWindow, Tray, Menu, nativeImage, globalShortcut, ipcMain, Notification, shell } from "electron";
import path from "node:path";
import Store from "electron-store";

const store = new Store<{
  alwaysOnTop: boolean;
  compactMode: boolean;
  webUrl: string;
}>({
  defaults: {
    alwaysOnTop: false,
    compactMode: false,
    webUrl: process.env.INTERVIEWPILOT_WEB_URL || "http://localhost:5173",
  },
});

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;

const isDev = !app.isPackaged;

function createWindow() {
  const compact = store.get("compactMode");
  mainWindow = new BrowserWindow({
    width: compact ? 420 : 1280,
    height: compact ? 720 : 860,
    minWidth: 380,
    minHeight: 560,
    title: "InterviewPilot AI",
    alwaysOnTop: store.get("alwaysOnTop"),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  const url = store.get("webUrl");
  void mainWindow.loadURL(url);

  mainWindow.once("ready-to-show", () => mainWindow?.show());

  mainWindow.on("close", (e) => {
    if (!(app as typeof app & { isQuitting?: boolean }).isQuitting) {
      e.preventDefault();
      mainWindow?.hide();
    }
  });
}

function createTray() {
  const image = nativeImage.createEmpty();
  tray = new Tray(image);
  tray.setToolTip("InterviewPilot AI");
  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Open InterviewPilot AI",
      click: () => {
        mainWindow?.show();
        mainWindow?.focus();
      },
    },
    {
      label: "Start / Stop Session shortcut: Ctrl+Shift+S",
      enabled: false,
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        (app as typeof app & { isQuitting?: boolean }).isQuitting = true;
        app.quit();
      },
    },
  ]);
  tray.setContextMenu(contextMenu);
  tray.on("double-click", () => mainWindow?.show());
}

function registerShortcuts() {
  globalShortcut.register("CommandOrControl+Shift+S", () => {
    mainWindow?.webContents.send("shortcut", "startStopSession");
    mainWindow?.show();
  });
  globalShortcut.register("CommandOrControl+Shift+P", () => {
    mainWindow?.webContents.send("shortcut", "pauseResume");
  });
  globalShortcut.register("CommandOrControl+Shift+A", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
  globalShortcut.register("CommandOrControl+Shift+C", () => {
    mainWindow?.webContents.send("shortcut", "copyLatestAnswer");
  });
  globalShortcut.register("CommandOrControl+Shift+D", () => {
    void mainWindow?.loadURL(`${store.get("webUrl").replace(/\/$/, "")}/dashboard`);
    mainWindow?.show();
  });
}

app.whenReady().then(() => {
  createWindow();
  createTray();
  registerShortcuts();

  ipcMain.handle("settings:get", () => ({
    alwaysOnTop: store.get("alwaysOnTop"),
    compactMode: store.get("compactMode"),
    webUrl: store.get("webUrl"),
  }));

  ipcMain.handle("settings:set", (_e, patch: Partial<{ alwaysOnTop: boolean; compactMode: boolean }>) => {
    if (typeof patch.alwaysOnTop === "boolean") {
      store.set("alwaysOnTop", patch.alwaysOnTop);
      mainWindow?.setAlwaysOnTop(patch.alwaysOnTop);
    }
    if (typeof patch.compactMode === "boolean") {
      store.set("compactMode", patch.compactMode);
      if (patch.compactMode) mainWindow?.setSize(420, 720);
      else mainWindow?.setSize(1280, 860);
    }
    return store.store;
  });

  ipcMain.handle("notify", (_e, title: string, body: string) => {
    if (Notification.isSupported()) {
      new Notification({ title, body }).show();
    }
  });

  ipcMain.handle("open-external", (_e, url: string) => shell.openExternal(url));

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
    else mainWindow?.show();
  });
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    // keep tray alive on Windows — do not quit
  }
});

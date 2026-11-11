import { del, get, set } from "idb-keyval";
import type { Snapshot } from "../types";
import { migrate, SNAPSHOT_FILE } from "./snapshot";

export type StorageMode = "local" | "folder" | "sharepoint";
export const STORAGE_MODE_KEY = "cmms-eaton:storage-mode";

export const STORAGE_MODES: { mode: StorageMode; label: string; description: string }[] = [
  {
    mode: "local",
    label: "This device",
    description: "Data is kept in this browser only. Use Backup to move it to another device.",
  },
  {
    mode: "folder",
    label: "Shared folder",
    description:
      "Data file in a folder on this PC, for example the SharePoint library synced with OneDrive. Everyone with the folder sees the same data. Needs Edge or Chrome on a desktop.",
  },
  {
    mode: "sharepoint",
    label: "SharePoint online",
    description: "Direct connection to the Eaton SharePoint library through Microsoft Graph. Prepared for later; needs an app registration from IT.",
  },
];

export interface StorageAdapter {
  readonly mode: StorageMode;
  load(): Promise<Snapshot | null>;
  save(snapshot: Snapshot): Promise<void>;
  /** A newer snapshot written by someone else, or null. */
  pollExternal?(): Promise<Snapshot | null>;
}

const LOCAL_KEY = "cmms-eaton:snapshot";

export class LocalAdapter implements StorageAdapter {
  readonly mode: StorageMode = "local";

  async load(): Promise<Snapshot | null> {
    const raw = await get<unknown>(LOCAL_KEY);
    return raw ? migrate(raw) : null;
  }

  async save(snapshot: Snapshot): Promise<void> {
    await set(LOCAL_KEY, snapshot);
  }
}

// File System Access API: not in the default TypeScript DOM typings.
declare global {
  interface Window {
    showDirectoryPicker?: (options?: { id?: string; mode?: "read" | "readwrite"; startIn?: string }) => Promise<FileSystemDirectoryHandle>;
  }
  interface FileSystemHandle {
    queryPermission?: (descriptor?: { mode?: "read" | "readwrite" }) => Promise<PermissionState>;
    requestPermission?: (descriptor?: { mode?: "read" | "readwrite" }) => Promise<PermissionState>;
  }
}

const HANDLE_KEY = "cmms-eaton:folder-handle";

export class FolderAdapter implements StorageAdapter {
  readonly mode: StorageMode = "folder";
  private handle: FileSystemDirectoryHandle | null = null;
  private lastModified = 0;

  static supported(): boolean {
    return typeof window !== "undefined" && typeof window.showDirectoryPicker === "function";
  }

  get folderName(): string | null {
    return this.handle?.name ?? null;
  }

  get connected(): boolean {
    return this.handle !== null;
  }

  /** Must run from a user gesture (button click). */
  async connect(): Promise<string> {
    if (!window.showDirectoryPicker) throw new Error("This browser cannot open folders. Use Edge or Chrome on a desktop.");
    const handle = await window.showDirectoryPicker({ id: "cmms-eaton", mode: "readwrite" });
    await set(HANDLE_KEY, handle);
    this.handle = handle;
    this.lastModified = 0;
    return handle.name;
  }

  /** Try to pick up the folder chosen earlier. "prompt" means the user must click Reconnect. */
  async restore(): Promise<"granted" | "prompt" | "none"> {
    const handle = await get<FileSystemDirectoryHandle>(HANDLE_KEY);
    if (!handle) return "none";
    const state = handle.queryPermission ? await handle.queryPermission({ mode: "readwrite" }) : "granted";
    if (state === "granted") {
      this.handle = handle;
      return "granted";
    }
    this.handle = null;
    return "prompt";
  }

  /** Must run from a user gesture. */
  async reconnect(): Promise<boolean> {
    const handle = await get<FileSystemDirectoryHandle>(HANDLE_KEY);
    if (!handle) return false;
    const state = handle.requestPermission ? await handle.requestPermission({ mode: "readwrite" }) : "granted";
    if (state !== "granted") return false;
    this.handle = handle;
    return true;
  }

  async disconnect(): Promise<void> {
    await del(HANDLE_KEY);
    this.handle = null;
  }

  async storedFolderName(): Promise<string | null> {
    const handle = await get<FileSystemDirectoryHandle>(HANDLE_KEY);
    return handle?.name ?? null;
  }

  private requireHandle(): FileSystemDirectoryHandle {
    if (!this.handle) throw new Error("Shared folder is not connected");
    return this.handle;
  }

  private async fileHandle(create: boolean): Promise<FileSystemFileHandle | null> {
    try {
      return await this.requireHandle().getFileHandle(SNAPSHOT_FILE, { create });
    } catch (err) {
      if (err instanceof DOMException && err.name === "NotFoundError") return null;
      throw err;
    }
  }

  async load(): Promise<Snapshot | null> {
    const fh = await this.fileHandle(false);
    if (!fh) return null;
    const file = await fh.getFile();
    this.lastModified = file.lastModified;
    const text = await file.text();
    return text.trim() ? migrate(JSON.parse(text)) : null;
  }

  async save(snapshot: Snapshot): Promise<void> {
    const fh = await this.fileHandle(true);
    if (!fh) throw new Error("Could not create the data file");
    const writable = await fh.createWritable();
    await writable.write(JSON.stringify(snapshot));
    await writable.close();
    const file = await fh.getFile();
    this.lastModified = file.lastModified;
  }

  async pollExternal(): Promise<Snapshot | null> {
    if (!this.handle) return null;
    const fh = await this.fileHandle(false);
    if (!fh) return null;
    const file = await fh.getFile();
    if (file.lastModified <= this.lastModified) return null;
    this.lastModified = file.lastModified;
    const text = await file.text();
    return text.trim() ? migrate(JSON.parse(text)) : null;
  }
}

/**
 * Placeholder for the planned direct SharePoint connection (Microsoft Graph).
 * The settings screen collects the site URL, library path, tenant and client id;
 * the actual calls are documented in docs/SHAREPOINT.md and will be added once
 * IT provides an app registration.
 */
export class SharePointAdapter implements StorageAdapter {
  readonly mode: StorageMode = "sharepoint";

  async load(): Promise<Snapshot | null> {
    throw new Error("SharePoint online is not connected yet. Use 'Shared folder' with the OneDrive-synced library for now.");
  }

  async save(): Promise<void> {
    throw new Error("SharePoint online is not connected yet.");
  }
}

export function readStoredMode(): StorageMode {
  try {
    const v = localStorage.getItem(STORAGE_MODE_KEY);
    if (v === "local" || v === "folder" || v === "sharepoint") return v;
  } catch {
    /* storage blocked */
  }
  return "local";
}

export function writeStoredMode(mode: StorageMode): void {
  try {
    localStorage.setItem(STORAGE_MODE_KEY, mode);
  } catch {
    /* storage blocked */
  }
}

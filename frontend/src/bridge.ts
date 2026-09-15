/*
  Мост между UI (TypeScript) и бэкендом (Python).

  Внутри вебвью pywebview кладёт методы Python в window.pywebview.api. Этот
  модуль прячет их за удобным интерфейсом. Если pywebview нет (запуск фронта в
  браузере через `npm run dev`) — подставляется заглушка с данными в памяти,
  чтобы смотреть и править вид без Python. Стук в заглушке ничего не шлёт.
*/

import type { AppState, FwknopStatus, Result, Settings, Stanza, Vars } from "./types";

export interface FwkogApi {
  state(): Promise<AppState>;
  createVault(password: string): Promise<Result>;
  unlock(password: string, rememberHours: number): Promise<Result>;
  unlockRemembered(): Promise<Result>;
  lock(): Promise<Result>;
  changePassword(oldPassword: string, newPassword: string): Promise<Result>;

  listStanzas(): Promise<Stanza[]>;
  saveStanza(originalName: string, name: string, vars: Vars): Promise<Result>;
  removeStanza(name: string): Promise<Result>;
  knock(name: string): Promise<Result>;

  fwknopStatus(): Promise<FwknopStatus>;
  getSettings(): Promise<Settings>;
  setFwknopPath(path: string): Promise<FwknopStatus>;
  setRememberHours(hours: number): Promise<Result>;
  pickFwknop(): Promise<FwknopStatus>;

  importFwknoprc(path?: string): Promise<Result>;
  pickAndImportFwknoprc(): Promise<Result>;
  exportVault(password: string): Promise<Result>;
  importVault(password: string): Promise<Result>;
}

/** Реальный мост — зовёт методы Python по их именам (snake_case). */
class RealApi implements FwkogApi {
  private get api(): any {
    return (window as any).pywebview.api;
  }
  state() { return this.api.state(); }
  createVault(password: string) { return this.api.create_vault(password); }
  unlock(password: string, rememberHours: number) { return this.api.unlock(password, rememberHours); }
  unlockRemembered() { return this.api.unlock_remembered(); }
  lock() { return this.api.lock(); }
  changePassword(oldPassword: string, newPassword: string) {
    return this.api.change_password(oldPassword, newPassword);
  }

  listStanzas() { return this.api.list_stanzas(); }
  saveStanza(originalName: string, name: string, vars: Vars) {
    return this.api.save_stanza(originalName, name, vars);
  }
  removeStanza(name: string) { return this.api.remove_stanza(name); }
  knock(name: string) { return this.api.knock(name); }

  fwknopStatus() { return this.api.fwknop_status(); }
  getSettings() { return this.api.get_settings(); }
  setFwknopPath(path: string) { return this.api.set_fwknop_path(path); }
  setRememberHours(hours: number) { return this.api.set_remember_hours(hours); }
  pickFwknop() { return this.api.pick_fwknop(); }

  importFwknoprc(path = "") { return this.api.import_fwknoprc(path); }
  pickAndImportFwknoprc() { return this.api.pick_and_import_fwknoprc(); }
  exportVault(password: string) { return this.api.export_vault(password); }
  importVault(password: string) { return this.api.import_vault(password); }
}

/** Заглушка для правки вида в браузере: одна стойка-пример, стук не отправляется. */
class MockApi implements FwkogApi {
  private password = "";
  private demo = location.search.includes("demo");
  private stanzas: Stanza[] = [
    {
      name: "Пример",
      vars: { SPA_SERVER: "203.0.113.10", SPA_SERVER_PORT: "62201", ACCESS: "tcp/22",
              ALLOW_IP: "resolve", FW_TIMEOUT: "60", USE_HMAC: "Y" },
      remaining: 0,
    },
  ];

  async state(): Promise<AppState> {
    return { version: "dev", exists: this.demo || this.password !== "", unlocked: false, can_remember: false };
  }
  async createVault(password: string): Promise<Result> { this.password = password; return { ok: true }; }
  async unlock(): Promise<Result> { return { ok: true }; }
  async unlockRemembered(): Promise<Result> {
    // ?demo в адресе — открыть список сразу, чтобы смотреть вид без ввода пароля.
    return this.demo ? { ok: true } : { ok: false, error: "нет" };
  }
  async lock(): Promise<Result> { return { ok: true }; }
  async changePassword(): Promise<Result> { return { ok: true }; }

  async listStanzas(): Promise<Stanza[]> { return this.stanzas.map((s) => ({ ...s })); }
  async saveStanza(originalName: string, name: string, vars: Vars): Promise<Result> {
    const i = this.stanzas.findIndex((s) => s.name === originalName);
    const item: Stanza = { name, vars, remaining: 0 };
    if (i >= 0) this.stanzas[i] = item;
    else this.stanzas.push(item);
    return { ok: true };
  }
  async removeStanza(name: string): Promise<Result> {
    this.stanzas = this.stanzas.filter((s) => s.name !== name);
    return { ok: true };
  }
  async knock(name: string): Promise<Result> {
    const s = this.stanzas.find((x) => x.name === name);
    const window_ = Number(s?.vars.FW_TIMEOUT ?? 0);
    if (s) s.remaining = window_;
    return { ok: true, window: window_ };
  }

  async fwknopStatus(): Promise<FwknopStatus> {
    return { ok: false, error: "В браузере клиент fwknop не запускается." };
  }
  async getSettings(): Promise<Settings> {
    return { fwknop_path: "", remember_hours: 0, can_remember: false };
  }
  async setFwknopPath(): Promise<FwknopStatus> { return this.fwknopStatus(); }
  async setRememberHours(): Promise<Result> { return { ok: true }; }
  async pickFwknop(): Promise<FwknopStatus> { return this.fwknopStatus(); }

  async importFwknoprc(): Promise<Result> { return { ok: false, error: "недоступно в браузере" }; }
  async pickAndImportFwknoprc(): Promise<Result> { return this.importFwknoprc(); }
  async exportVault(): Promise<Result> { return this.importFwknoprc(); }
  async importVault(): Promise<Result> { return this.importFwknoprc(); }
}

/** Выбрать реализацию: pywebview (приложение) или заглушка (браузер). */
export function getApi(): FwkogApi {
  const api = (window as any).pywebview?.api;
  if (api && typeof api.state === "function") return new RealApi();
  return new MockApi();
}

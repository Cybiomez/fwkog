/*
  Сборка интерфейса и переходы между экранами.

  Экранов два: замок (создать или ввести мастер-пароль) и список стоек.
  Поверх списка открываются окна правки стойки и настроек.
*/

import { getApi } from "./bridge";
import type { FwkogApi } from "./bridge";
import { clear, el } from "./dom";
import * as icons from "./icons";
import { StanzaCard, updateCardTimer } from "./components/StanzaCard";
import { EditModal } from "./components/EditModal";
import { LockScreen } from "./components/LockScreen";
import { SettingsModal } from "./components/SettingsModal";
import { showToast } from "./components/toast";
import { toggleTheme, currentTheme, applyTheme } from "./theme";
import type { AppState, Stanza, Vars } from "./types";

export class App {
  private api: FwkogApi = getApi();
  private state: AppState = { version: "", exists: false, unlocked: false, can_remember: false };
  private stanzas: Stanza[] = [];
  private ticker: number | undefined;

  constructor(private root: HTMLElement) {}

  /** Точка входа: решаем, какой экран показать. */
  async start(): Promise<void> {
    applyTheme(currentTheme());
    this.state = await this.api.state();

    if (!this.state.exists) {
      this.renderLock("create");
      return;
    }
    // Пароль мог быть запомнен — тогда список открывается сразу.
    const remembered = await this.api.unlockRemembered();
    if (remembered.ok) {
      await this.renderList();
      return;
    }
    this.renderLock("unlock");
  }

  // --- экран замка ---

  private renderLock(mode: "create" | "unlock"): void {
    this.stopTicker();
    clear(this.root);
    this.root.append(
      LockScreen(mode, this.state.can_remember, {
        onCreate: async (password) => {
          const result = await this.api.createVault(password);
          if (!result.ok) return result.error ?? "не получилось";
          await this.api.unlock(password, 0);
          await this.renderList();
          return null;
        },
        onUnlock: async (password, rememberHours) => {
          const result = await this.api.unlock(password, rememberHours);
          if (!result.ok) return result.error ?? "не получилось";
          await this.renderList();
          return null;
        },
      })
    );
  }

  // --- экран списка ---

  private async renderList(): Promise<void> {
    this.stanzas = await this.api.listStanzas();
    clear(this.root);

    const list = el("div", { class: "list" });
    if (this.stanzas.length === 0) {
      list.append(
        el("div", {
          class: "empty",
          text: "Стоек пока нет. Добавьте первую или перенесите из ~/.fwknoprc в настройках.",
        })
      );
    } else {
      for (const stanza of this.stanzas) {
        list.append(
          StanzaCard(stanza, {
            onKnock: (name) => void this.knock(name),
            onEdit: (name) => this.openEdit(name),
          })
        );
      }
    }

    this.root.append(
      el("div", { class: "header" }, [
        el("div", { class: "header__title", text: "FWKOG" }),
        el("div", { class: "header__spacer" }),
        this.iconButton(currentTheme() === "dark" ? icons.sun : icons.moon, "Тема", (btn) => {
          const theme = toggleTheme();
          btn.innerHTML = theme === "dark" ? icons.sun : icons.moon;
        }),
        this.iconButton(icons.gear, "Настройки", () => void this.openSettings()),
        this.iconButton(icons.lock, "Закрыть хранилище", () => void this.lock()),
      ]),
      list,
      el("div", { class: "footer" }, [
        el("button", {
          class: "btn-pill",
          html: icons.plus,
          attrs: { type: "button" },
          on: { click: () => this.openEdit(null) },
        }, [el("span", { text: "Добавить стойку" })]),
      ])
    );

    this.startTicker();
  }

  private iconButton(
    svg: string,
    title: string,
    onClick: (btn: HTMLElement) => void
  ): HTMLElement {
    const btn = el("button", {
      class: "btn-icon",
      html: svg,
      attrs: { type: "button", title },
    });
    btn.addEventListener("click", () => onClick(btn));
    return btn;
  }

  // --- действия ---

  /** Стук: отправляем SPA-пакет и заводим обратный отсчёт окна доступа. */
  private async knock(name: string): Promise<void> {
    const result = await this.api.knock(name);
    if (!result.ok) {
      showToast(this.root, result.error ?? "не получилось", "error");
      return;
    }
    const window_ = Number(result.window ?? 0);
    const stanza = this.stanzas.find((s) => s.name === name);
    if (stanza) stanza.remaining = window_;
    updateCardTimer(this.root, name, window_);
    showToast(
      this.root,
      window_
        ? `Пакет отправлен: ${name}. Окно ${window_} с.`
        : `Пакет отправлен: ${name}. Длительность окна задаёт сервер.`
    );
  }

  private async lock(): Promise<void> {
    await this.api.lock();
    this.state = await this.api.state();
    this.renderLock("unlock");
  }

  private openEdit(name: string | null): void {
    const stanza = name ? this.stanzas.find((s) => s.name === name) ?? null : null;
    const close = (): void => overlay.remove();

    const overlay = EditModal(stanza, {
      onSave: async (originalName: string, newName: string, vars: Vars) => {
        const result = await this.api.saveStanza(originalName, newName, vars);
        if (!result.ok) return result.error ?? "не получилось";
        close();
        await this.renderList();
        return null;
      },
      onRemove: async (target: string) => {
        const result = await this.api.removeStanza(target);
        if (!result.ok) return result.error ?? "не получилось";
        close();
        await this.renderList();
        return null;
      },
      onClose: close,
    });
    this.root.append(overlay);
  }

  private async openSettings(): Promise<void> {
    const [settings, status] = await Promise.all([this.api.getSettings(), this.api.fwknopStatus()]);
    const close = (): void => overlay.remove();

    const overlay = SettingsModal(this.api, settings, status, {
      onClose: close,
      onChanged: () => void this.renderListKeepingModal(overlay),
      notify: (text) => showToast(this.root, text),
    });
    this.root.append(overlay);
  }

  /** Перерисовать список, не закрывая открытое окно (импорт из настроек). */
  private async renderListKeepingModal(overlay: HTMLElement): Promise<void> {
    await this.renderList();
    this.root.append(overlay);
  }

  // --- обратный отсчёт ---

  private startTicker(): void {
    this.stopTicker();
    this.ticker = window.setInterval(() => {
      let anyOpen = false;
      for (const stanza of this.stanzas) {
        if (stanza.remaining > 0) {
          stanza.remaining -= 1;
          updateCardTimer(this.root, stanza.name, stanza.remaining);
          anyOpen = true;
        }
      }
      if (!anyOpen) this.stopTicker();
    }, 1000);
  }

  private stopTicker(): void {
    if (this.ticker !== undefined) {
      window.clearInterval(this.ticker);
      this.ticker = undefined;
    }
  }
}

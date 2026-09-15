/*
  Настройки: где лежит клиент fwknop, запоминание мастер-пароля, перенос
  стоек и смена мастер-пароля.

  Перенос — осознанный шаг: стойки уезжают отдельным зашифрованным файлом со
  своим паролем, а не «прицепом» к приложению.
*/

import { el } from "../dom";
import type { FwkogApi } from "../bridge";
import type { FwknopStatus, Settings } from "../types";

export interface SettingsHandlers {
  onClose(): void;
  onChanged(): void; // список стоек мог измениться (импорт) — перерисовать
  notify(text: string): void;
}

export function SettingsModal(
  api: FwkogApi,
  settings: Settings,
  status: FwknopStatus,
  handlers: SettingsHandlers
): HTMLElement {
  const error = el("div", { class: "modal__error" });

  // --- клиент fwknop ---
  const statusLine = el("div", { class: "settings__status" });
  function showStatus(value: FwknopStatus): void {
    statusLine.classList.toggle("settings__status--bad", !value.ok);
    statusLine.textContent = value.ok
      ? `${value.version} — ${value.path}`
      : value.error ?? "клиент не найден";
  }
  showStatus(status);

  const pathBox = el("input", {
    attrs: { type: "text", value: settings.fwknop_path, placeholder: "пусто — искать автоматически" },
  }) as HTMLInputElement;

  const pickBtn = el("button", {
    class: "btn-pill",
    text: "Выбрать…",
    attrs: { type: "button" },
    on: {
      click: async () => {
        const result = await api.pickFwknop();
        if (result.ok && result.path) pathBox.value = result.path;
        showStatus(result);
      },
    },
  });
  const checkBtn = el("button", {
    class: "btn-pill",
    text: "Проверить",
    attrs: { type: "button" },
    on: {
      click: async () => {
        showStatus(await api.setFwknopPath(pathBox.value.trim()));
      },
    },
  });

  // --- запоминание пароля ---
  const rememberSelect = el("select") as HTMLSelectElement;
  for (const [value, text] of [
    ["0", "Спрашивать каждый раз"],
    ["24", "Помнить сутки"],
    ["168", "Помнить неделю"],
  ] as [string, string][]) {
    rememberSelect.append(el("option", { text, attrs: { value } }));
  }
  rememberSelect.value = String(settings.remember_hours ?? 0);
  rememberSelect.disabled = !settings.can_remember;
  const rememberHint = el("div", {
    class: "settings__hint",
    text: settings.can_remember
      ? "Запомненный пароль хранится средствами Windows и только для этой учётной записи."
      : "На этой системе запоминание недоступно — пароль спрашивается при каждом запуске.",
  });
  rememberSelect.addEventListener("change", async () => {
    const hours = Number(rememberSelect.value);
    settings.remember_hours = hours;
    await api.setRememberHours(hours);
    handlers.notify(hours ? "Пароль будет запомнен." : "Пароль забыт, будем спрашивать.");
  });

  // --- перенос ---
  const transferPassword = el("input", {
    attrs: { type: "password", placeholder: "пароль файла переноса" },
  }) as HTMLInputElement;

  async function report(action: Promise<any>, done: (r: any) => string): Promise<void> {
    error.textContent = "";
    const result = await action;
    if (!result.ok) {
      if (result.error !== "отменено") error.textContent = result.error ?? "не получилось";
      return;
    }
    handlers.notify(done(result));
    handlers.onChanged();
  }

  const importRcBtn = el("button", {
    class: "btn-pill",
    text: "Из ~/.fwknoprc",
    attrs: { type: "button", title: "Забрать стойки из штатного файла клиента fwknop" },
    on: {
      click: () =>
        report(api.importFwknoprc(), (r) => `Перенесено стоек: ${r.added}, обновлено: ${r.replaced}.`),
    },
  });
  const importRcFileBtn = el("button", {
    class: "btn-pill",
    text: "Из файла .fwknoprc…",
    attrs: { type: "button" },
    on: {
      click: () =>
        report(api.pickAndImportFwknoprc(), (r) => `Перенесено стоек: ${r.added}, обновлено: ${r.replaced}.`),
    },
  });
  const importVaultBtn = el("button", {
    class: "btn-pill",
    text: "Из файла FWKOG…",
    attrs: { type: "button" },
    on: {
      click: () =>
        report(api.importVault(transferPassword.value), (r) => `Перенесено стоек: ${r.added}, обновлено: ${r.replaced}.`),
    },
  });
  const exportBtn = el("button", {
    class: "btn-pill",
    text: "Выгрузить в файл…",
    attrs: { type: "button" },
    on: {
      click: () => report(api.exportVault(transferPassword.value), (r) => `Стойки выгружены: ${r.path}`),
    },
  });

  // --- смена мастер-пароля ---
  const oldBox = el("input", { attrs: { type: "password", placeholder: "текущий пароль" } }) as HTMLInputElement;
  const newBox = el("input", { attrs: { type: "password", placeholder: "новый пароль" } }) as HTMLInputElement;
  const changeBtn = el("button", {
    class: "btn-pill",
    text: "Сменить пароль",
    attrs: { type: "button" },
    on: {
      click: async () => {
        error.textContent = "";
        const result = await api.changePassword(oldBox.value, newBox.value);
        if (!result.ok) {
          error.textContent = result.error ?? "не получилось";
          return;
        }
        oldBox.value = newBox.value = "";
        handlers.notify("Мастер-пароль изменён.");
      },
    },
  });

  const modal = el("div", { class: "modal" }, [
    el("h2", { class: "modal__title", text: "Настройки" }),

    el("div", { class: "modal__section", text: "Клиент fwknop" }),
    statusLine,
    el("label", { class: "field" }, [
      el("span", { class: "field__label", text: "Путь к fwknop" }),
      pathBox,
    ]),
    el("div", { class: "settings__buttons" }, [pickBtn, checkBtn]),

    el("div", { class: "modal__section", text: "Мастер-пароль" }),
    el("label", { class: "field" }, [
      el("span", { class: "field__label", text: "Запоминать пароль" }),
      rememberSelect,
    ]),
    rememberHint,
    el("div", { class: "settings__buttons" }, [oldBox, newBox, changeBtn]),

    el("div", { class: "modal__section", text: "Перенос стоек" }),
    el("label", { class: "field" }, [
      el("span", { class: "field__label", text: "Пароль файла переноса" }),
      transferPassword,
      el("span", {
        class: "field__hint",
        text: "Файл экспорта шифруется отдельным паролем — им же открывается при импорте.",
      }),
    ]),
    el("div", { class: "settings__buttons" }, [exportBtn, importVaultBtn]),
    el("div", { class: "settings__buttons" }, [importRcBtn, importRcFileBtn]),

    error,
    el("div", { class: "modal__actions" }, [
      el("button", {
        class: "btn-pill",
        text: "Закрыть",
        attrs: { type: "button" },
        on: { click: handlers.onClose },
      }),
    ]),
  ]);

  return el("div", { class: "overlay", on: { click: (e) => {
    if (e.target === e.currentTarget) handlers.onClose();
  } } }, [modal]);
}

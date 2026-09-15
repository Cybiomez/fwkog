/*
  Экран замка: создание мастер-пароля при первом запуске и ввод при обычном.

  Мастер-пароль нигде не хранится — им шифруется файл со стойками. Забыли
  пароль — стойки не восстановить, о чём экран честно предупреждает.
*/

import { el } from "../dom";
import * as icons from "../icons";

export interface LockHandlers {
  onCreate(password: string): Promise<string | null>;
  onUnlock(password: string, rememberHours: number): Promise<string | null>;
}

export function LockScreen(
  mode: "create" | "unlock",
  canRemember: boolean,
  handlers: LockHandlers
): HTMLElement {
  const isCreate = mode === "create";

  const passwordBox = el("input", {
    attrs: { type: "password", placeholder: "Мастер-пароль", autofocus: "autofocus" },
  }) as HTMLInputElement;
  const repeatBox = el("input", {
    attrs: { type: "password", placeholder: "Повторите пароль" },
  }) as HTMLInputElement;

  const remember = el("input", { attrs: { type: "checkbox" } }) as HTMLInputElement;
  const rememberRow = el("label", { class: "lock__remember" }, [
    remember,
    el("span", { text: "Запомнить на сутки" }),
  ]);

  const error = el("div", { class: "modal__error" });

  async function submit(): Promise<void> {
    error.textContent = "";
    const password = passwordBox.value;
    if (!password) {
      error.textContent = "Введите пароль.";
      return;
    }
    if (isCreate && password !== repeatBox.value) {
      error.textContent = "Пароли не совпадают.";
      return;
    }
    const message = isCreate
      ? await handlers.onCreate(password)
      : await handlers.onUnlock(password, remember.checked ? 24 : 0);
    if (message) {
      error.textContent = message;
      passwordBox.select();
    }
  }

  for (const box of [passwordBox, repeatBox]) {
    box.addEventListener("keydown", (e) => {
      if ((e as KeyboardEvent).key === "Enter") void submit();
    });
  }

  const children: (Node | string)[] = [
    el("div", { class: "lock__icon", html: icons.lock }),
    el("div", { class: "lock__title", text: isCreate ? "Придумайте мастер-пароль" : "FWKOG" }),
    el("div", {
      class: "lock__hint",
      text: isCreate
        ? "Им шифруется файл с настройками стоек. Пароль нигде не хранится: если его забыть, стойки придётся заводить заново."
        : "Введите мастер-пароль, чтобы открыть список стоек.",
    }),
    passwordBox,
  ];
  if (isCreate) children.push(repeatBox);
  if (!isCreate && canRemember) children.push(rememberRow);
  children.push(
    error,
    el("button", {
      class: "btn-pill btn-pill--accent lock__submit",
      text: isCreate ? "Создать" : "Открыть",
      attrs: { type: "button" },
      on: { click: () => void submit() },
    })
  );

  const screen = el("div", { class: "lock" }, [el("div", { class: "lock__box" }, children)]);
  setTimeout(() => passwordBox.focus(), 0);
  return screen;
}

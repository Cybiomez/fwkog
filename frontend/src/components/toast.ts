/*
  Всплывающая подсказка внизу окна: «пакет отправлен», текст ошибки клиента.
  Сообщение об ошибке живёт дольше и снимается кликом — вывод fwknop бывает в
  несколько строк, его нужно успеть прочитать.
*/

import { el } from "../dom";

export function showToast(root: HTMLElement, text: string, kind: "info" | "error" = "info"): void {
  root.querySelector(".toast")?.remove();

  const node = el("div", {
    class: `toast toast--${kind}`,
    text,
    on: { click: () => node.remove() },
  });
  root.append(node);

  const life = kind === "error" ? 12000 : 3000;
  setTimeout(() => node.remove(), life);
}

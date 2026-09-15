/*
  Карточка одной стойки в главном списке.

  Слева — точка состояния: горит, пока идёт окно доступа. По центру имя и
  строка «сервер · доступ». Справа — обратный отсчёт окна и кнопка «Стук».
  Клик по телу карточки открывает редактирование.
*/

import { el } from "../dom";
import * as icons from "../icons";
import type { Stanza } from "../types";

/** Обратный отсчёт: показываем секунды, чтобы было видно, сколько осталось точно. */
export function formatLeft(seconds: number): string {
  return `${seconds} с`;
}

/** Вторая строка карточки: куда стучим и что открываем. */
function subtitle(stanza: Stanza): string {
  const server = stanza.vars.SPA_SERVER || "—";
  const access = stanza.vars.ACCESS || "—";
  const nat = stanza.vars.NAT_ACCESS ? ` · NAT ${stanza.vars.NAT_ACCESS}` : "";
  return `${server} · ${access}${nat}`;
}

export interface CardHandlers {
  onKnock(name: string): void;
  onEdit(name: string): void;
}

export function StanzaCard(stanza: Stanza, handlers: CardHandlers): HTMLElement {
  const open = stanza.remaining > 0;

  // Отсчёт обновляется на месте (см. updateCardTimer) — перерисовывать всю
  // карточку раз в секунду незачем.
  const timer = el("div", {
    class: "card__timer",
    text: open ? formatLeft(stanza.remaining) : "",
    attrs: {
      "data-timer": stanza.name,
      title: "Осталось от окна доступа: из настройки стойки или умолчания сервера",
    },
  });

  const knockBtn = el("button", {
    class: "btn-pill btn-pill--accent card__knock",
    html: icons.knock,
    attrs: { type: "button", title: "Отправить SPA-пакет" },
    on: {
      click: (e) => {
        e.stopPropagation();
        handlers.onKnock(stanza.name);
      },
    },
  });
  knockBtn.append(el("span", { text: "Стук" }));

  return el(
    "div",
    {
      class: `card${open ? " card--open" : ""}`,
      on: { click: () => handlers.onEdit(stanza.name) },
    },
    [
      el("div", { class: "card__status" }),
      el("div", { class: "card__body" }, [
        el("div", { class: "card__name", text: stanza.name }),
        el("div", { class: "card__sub", text: subtitle(stanza) }),
      ]),
      el("div", { class: "card__actions" }, [timer, knockBtn]),
    ]
  );
}

/** Обновить отсчёт в уже отрисованной карточке (раз в секунду). */
export function updateCardTimer(root: HTMLElement, name: string, remaining: number): void {
  const timer = root.querySelector<HTMLElement>(`[data-timer="${CSS.escape(name)}"]`);
  if (!timer) return;
  timer.textContent = remaining > 0 ? formatLeft(remaining) : "";
  timer.closest(".card")?.classList.toggle("card--open", remaining > 0);
}

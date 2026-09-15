/*
  Окно добавления и правки стойки.

  Поля названы по-человечески, но под каждым подписана переменная fwknop, в
  которую оно кладётся: так видно, что приложение ничего не выдумывает поверх
  клиента, и знание fwknop остаётся применимым.

  Переменные, для которых отдельных полей нет (GPG, прокси, смещение времени и
  прочая экзотика), правятся текстом в блоке «Прочие переменные» — в том же
  виде, что в .fwknoprc. Так поддержан весь набор, без стены из сорока полей.
*/

import { el } from "../dom";
import type { Stanza, Vars } from "../types";

/** Переменные, под которые есть отдельные поля формы. Всё остальное уходит в «прочие». */
const FORM_VARS = [
  "SPA_SERVER",
  "SPA_SERVER_PORT",
  "SPA_SERVER_PROTO",
  "ACCESS",
  "ALLOW_IP",
  "FW_TIMEOUT",
  "KEY",
  "KEY_BASE64",
  "HMAC_KEY",
  "HMAC_KEY_BASE64",
  "USE_HMAC",
  "HMAC_DIGEST_TYPE",
  "NAT_ACCESS",
];

export interface EditHandlers {
  onSave(originalName: string, name: string, vars: Vars): Promise<string | null>;
  onRemove(name: string): Promise<string | null>;
  onClose(): void;
}

/** Поле формы: подпись, значение и пояснение с именем переменной fwknop. */
function field(label: string, hint: string, input: HTMLElement): HTMLElement {
  return el("label", { class: "field" }, [
    el("span", { class: "field__label", text: label }),
    input,
    el("span", { class: "field__hint", text: hint }),
  ]);
}

function input(value: string, placeholder = "", type = "text"): HTMLInputElement {
  return el("input", { attrs: { type, value, placeholder } }) as HTMLInputElement;
}

function select(options: [string, string][], value: string): HTMLSelectElement {
  const node = el("select") as HTMLSelectElement;
  for (const [key, text] of options) {
    node.append(el("option", { text, attrs: { value: key } }));
  }
  node.value = value;
  return node;
}

/** Поле секрета: текст скрыт, рядом кнопка «показать». */
function secretField(label: string, hint: string, value: string): [HTMLElement, HTMLInputElement] {
  const box = input(value, "", "password");
  const eye = el("button", {
    class: "btn-eye",
    text: "показать",
    attrs: { type: "button" },
    on: {
      click: () => {
        const shown = box.type === "text";
        box.type = shown ? "password" : "text";
        eye.textContent = shown ? "показать" : "скрыть";
      },
    },
  });
  return [field(label, hint, el("div", { class: "field__with-btn" }, [box, eye])), box];
}

/** «Прочие переменные» -> текст, как в .fwknoprc. */
function otherVarsText(vars: Vars): string {
  return Object.entries(vars)
    .filter(([key]) => !FORM_VARS.includes(key))
    .map(([key, value]) => `${key} ${value}`)
    .join("\n");
}

/** Текст «прочих переменных» обратно в пары. Строки без значения пропускаем. */
function parseOtherVars(text: string): Vars {
  const vars: Vars = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const match = trimmed.match(/^([A-Za-z][A-Za-z0-9_]*)\s+(.+)$/);
    if (match) vars[match[1].toUpperCase()] = match[2].trim();
  }
  return vars;
}

export function EditModal(stanza: Stanza | null, handlers: EditHandlers): HTMLElement {
  const vars: Vars = stanza ? { ...stanza.vars } : {};
  const isNew = stanza === null;

  const nameBox = input(stanza?.name ?? "", "Например: Сервер дома");
  const serverBox = input(vars.SPA_SERVER ?? "", "адрес или имя хоста");
  const portBox = input(vars.SPA_SERVER_PORT ?? "", "62201");
  const protoBox = select(
    [
      ["", "udp (по умолчанию)"],
      ["udp", "udp"],
      ["tcp", "tcp"],
    ],
    vars.SPA_SERVER_PROTO ?? ""
  );
  const accessBox = input(vars.ACCESS ?? "", "tcp/22");
  const timeoutBox = input(vars.FW_TIMEOUT ?? "", "например 60", "number");

  // ALLOW_IP: либо ключевое слово, либо конкретный адрес в отдельном поле.
  const allowValue = vars.ALLOW_IP ?? "";
  const allowKind = allowValue === "" || allowValue.toLowerCase() === "resolve"
    ? "resolve"
    : allowValue.toLowerCase() === "source"
      ? "source"
      : "ip";
  const allowSelect = select(
    [
      ["resolve", "Узнать мой внешний адрес (resolve)"],
      ["source", "Взять адрес из пакета (source)"],
      ["ip", "Указать адрес вручную"],
    ],
    allowKind
  );
  const allowIpBox = input(allowKind === "ip" ? allowValue : "", "203.0.113.10");
  const allowIpField = field("Адрес, которому открыть доступ", "ALLOW_IP", allowIpBox);
  allowIpField.hidden = allowKind !== "ip";
  allowSelect.addEventListener("change", () => {
    allowIpField.hidden = allowSelect.value !== "ip";
  });

  // Ключи. fwknop принимает и base64 (как выдаёт --key-gen), и обычную строку.
  const keyIsBase64 = vars.KEY_BASE64 !== undefined || vars.KEY === undefined;
  const keyKind = select(
    [
      ["base64", "base64 (KEY_BASE64)"],
      ["text", "строка-пароль (KEY)"],
    ],
    keyIsBase64 ? "base64" : "text"
  );
  const [keyField, keyBox] = secretField(
    "Ключ шифрования",
    "KEY_BASE64 или KEY — тот же ключ, что в access.conf сервера",
    vars.KEY_BASE64 ?? vars.KEY ?? ""
  );

  const useHmac = (vars.USE_HMAC ?? "Y").toUpperCase() !== "N";
  const hmacToggle = el("input", {
    attrs: { type: "checkbox", ...(useHmac ? { checked: "checked" } : {}) },
  }) as HTMLInputElement;
  const hmacIsBase64 = vars.HMAC_KEY_BASE64 !== undefined || vars.HMAC_KEY === undefined;
  const hmacKind = select(
    [
      ["base64", "base64 (HMAC_KEY_BASE64)"],
      ["text", "строка-пароль (HMAC_KEY)"],
    ],
    hmacIsBase64 ? "base64" : "text"
  );
  const [hmacField, hmacBox] = secretField(
    "Ключ HMAC",
    "HMAC_KEY_BASE64 или HMAC_KEY — должен отличаться от ключа шифрования",
    vars.HMAC_KEY_BASE64 ?? vars.HMAC_KEY ?? ""
  );
  const hmacDigest = select(
    [
      ["", "sha256 (по умолчанию)"],
      ["sha1", "sha1"],
      ["sha256", "sha256"],
      ["sha384", "sha384"],
      ["sha512", "sha512"],
    ],
    vars.HMAC_DIGEST_TYPE ?? ""
  );
  const hmacBlock = el("div", {}, [
    hmacField,
    field("Тип HMAC", "HMAC_DIGEST_TYPE", hmacDigest),
    field("Вид ключа HMAC", "как записан ключ", hmacKind),
  ]);
  hmacBlock.hidden = !useHmac;
  hmacToggle.addEventListener("change", () => {
    hmacBlock.hidden = !hmacToggle.checked;
  });

  const natBox = input(vars.NAT_ACCESS ?? "", "192.168.1.55,88");

  const otherBox = el("textarea", {
    class: "textbox",
    attrs: { spellcheck: "false", placeholder: "DIGEST_TYPE sha256" },
  }) as HTMLTextAreaElement;
  otherBox.value = otherVarsText(vars);

  const error = el("div", { class: "modal__error" });

  // --- сборка значений формы обратно в переменные fwknop ---
  function collect(): Vars {
    const result: Vars = parseOtherVars(otherBox.value);

    result.SPA_SERVER = serverBox.value.trim();
    result.ACCESS = accessBox.value.trim();
    if (portBox.value.trim()) result.SPA_SERVER_PORT = portBox.value.trim();
    if (protoBox.value) result.SPA_SERVER_PROTO = protoBox.value;
    if (timeoutBox.value.trim()) result.FW_TIMEOUT = timeoutBox.value.trim();
    if (natBox.value.trim()) result.NAT_ACCESS = natBox.value.trim();

    result.ALLOW_IP = allowSelect.value === "ip" ? allowIpBox.value.trim() : allowSelect.value;

    const key = keyBox.value.trim();
    if (key) result[keyKind.value === "base64" ? "KEY_BASE64" : "KEY"] = key;

    if (hmacToggle.checked) {
      result.USE_HMAC = "Y";
      const hmac = hmacBox.value.trim();
      if (hmac) result[hmacKind.value === "base64" ? "HMAC_KEY_BASE64" : "HMAC_KEY"] = hmac;
      if (hmacDigest.value) result.HMAC_DIGEST_TYPE = hmacDigest.value;
    } else {
      result.USE_HMAC = "N";
    }
    return result;
  }

  const saveBtn = el("button", {
    class: "btn-pill btn-pill--accent",
    text: "Сохранить",
    attrs: { type: "button" },
    on: {
      click: async () => {
        error.textContent = "";
        const message = await handlers.onSave(stanza?.name ?? "", nameBox.value.trim(), collect());
        if (message) error.textContent = message;
      },
    },
  });

  const actions: (Node | string)[] = [];
  if (!isNew) {
    actions.push(
      el("button", {
        class: "btn-pill btn-pill--danger",
        text: "Удалить",
        attrs: { type: "button" },
        on: {
          click: async () => {
            const message = await handlers.onRemove(stanza!.name);
            if (message) error.textContent = message;
          },
        },
      })
    );
  }
  actions.push(
    el("div", { class: "modal__actions-right" }, [
      el("button", {
        class: "btn-pill",
        text: "Отмена",
        attrs: { type: "button" },
        on: { click: handlers.onClose },
      }),
      saveBtn,
    ])
  );

  const modal = el("div", { class: "modal" }, [
    el("h2", { class: "modal__title", text: isNew ? "Новая стойка" : "Правка стойки" }),

    field("Имя", "как стойка называется в списке (и в .fwknoprc)", nameBox),
    field("Сервер", "SPA_SERVER — куда отправляем пакет", serverBox),
    el("div", { class: "row2" }, [
      field("Порт", "SPA_SERVER_PORT", portBox),
      field("Протокол", "SPA_SERVER_PROTO", protoBox),
    ]),
    field("Доступ", "ACCESS — что открыть, например tcp/22", accessBox),
    field("Чей адрес открывать", "ALLOW_IP", allowSelect),
    allowIpField,
    field("Окно доступа, сек", "FW_TIMEOUT — сервер может срезать до своего потолка", timeoutBox),

    el("div", { class: "modal__section", text: "Ключи" }),
    keyField,
    field("Вид ключа", "как записан ключ", keyKind),
    el("label", { class: "modal__row" }, [
      el("span", { text: "Подписывать HMAC (USE_HMAC)" }),
      hmacToggle,
    ]),
    hmacBlock,

    el("div", { class: "modal__section", text: "Дополнительно" }),
    field("Проброс NAT", "NAT_ACCESS — например 192.168.1.55,88", natBox),
    field("Прочие переменные", "по строке на переменную, как в .fwknoprc", otherBox),

    error,
    el("div", { class: "modal__actions modal__actions--split" }, actions),
  ]);

  return el("div", { class: "overlay", on: { click: (e) => {
    if (e.target === e.currentTarget) handlers.onClose();
  } } }, [modal]);
}

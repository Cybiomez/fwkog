/*
  Типы, общие для интерфейса.

  Стойка (stanza) — это то же самое, что стойка в .fwknoprc клиента fwknop:
  имя и набор переменных. Своих полей FWKOG не придумывает, поэтому vars —
  просто словарь «имя переменной -> значение».
*/

/** Переменные стойки в терминах fwknop: SPA_SERVER, ACCESS, KEY_BASE64 и т.д. */
export type Vars = Record<string, string>;

/** Стойка в списке: имя, переменные и остаток окна доступа в секундах. */
export interface Stanza {
  name: string;
  vars: Vars;
  remaining: number;
}

/** Единый вид ответа бэкенда: либо ok, либо текст ошибки. */
export interface Result {
  ok: boolean;
  error?: string;
  [key: string]: unknown;
}

/** Что показывать при запуске. */
export interface AppState {
  version: string;
  exists: boolean;    // хранилище уже заведено
  unlocked: boolean;  // и уже открыто
  can_remember: boolean; // ОС умеет запоминать мастер-пароль
}

export interface Settings {
  fwknop_path: string;
  remember_hours: number;
  can_remember: boolean;
}

/** Ответ на проверку клиента fwknop. */
export interface FwknopStatus extends Result {
  path?: string;
  version?: string;
}

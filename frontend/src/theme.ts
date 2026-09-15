/*
  Управление темой (светлая/тёмная). Тема хранится в localStorage, а на <html>
  ставится атрибут data-theme — по нему tokens.scss подставляет нужные цвета.
*/

export type Theme = "light" | "dark";

const KEY = "fwkog-theme";

/** Текущая тема: сохранённая, иначе — системная (prefers-color-scheme). */
export function currentTheme(): Theme {
  const saved = localStorage.getItem(KEY);
  if (saved === "light" || saved === "dark") return saved;
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

/** Применить тему к документу (без сохранения). */
export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

/** Сохранить и применить тему. */
export function setTheme(theme: Theme): void {
  localStorage.setItem(KEY, theme);
  applyTheme(theme);
}

/** Переключить тему на противоположную, вернуть новую. */
export function toggleTheme(): Theme {
  const next: Theme = currentTheme() === "dark" ? "light" : "dark";
  setTheme(next);
  return next;
}

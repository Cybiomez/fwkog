/*
  Крохотный помощник для создания DOM-элементов без строк innerHTML
  (безопаснее и читаемее). Используется всеми компонентами.
*/

type Opts = {
  class?: string;
  text?: string;
  html?: string;
  attrs?: Record<string, string>;
  on?: Partial<Record<keyof HTMLElementEventMap, (e: Event) => void>>;
};

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  opts: Opts = {},
  children: (Node | string)[] = []
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text !== undefined) node.textContent = opts.text;
  if (opts.html !== undefined) node.innerHTML = opts.html;
  if (opts.attrs) {
    for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  }
  if (opts.on) {
    for (const [event, handler] of Object.entries(opts.on)) {
      node.addEventListener(event, handler as EventListener);
    }
  }
  for (const child of children) node.append(child);
  return node;
}

/** Убрать всё содержимое элемента. */
export function clear(node: HTMLElement): void {
  node.textContent = "";
}

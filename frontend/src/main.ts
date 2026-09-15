/*
  Запуск интерфейса.

  В приложении методы Python появляются в window.pywebview.api не сразу —
  ждём события pywebviewready. В браузере (npm run dev) события не будет,
  поэтому стартуем по таймауту: там мост подставит заглушку.
*/

import { App } from "./App";
import "./styles/main.scss";

function start(): void {
  const root = document.getElementById("app");
  if (root) void new App(root).start();
}

let started = false;
function startOnce(): void {
  if (started) return;
  started = true;
  start();
}

window.addEventListener("pywebviewready", startOnce);
setTimeout(startOnce, 300); // браузер без pywebview

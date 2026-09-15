import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Собираем UI в один самодостаточный index.html: стили и скрипт встроены
// внутрь. Так окно вебвью открывает файл напрямую (file://) без отдельных
// запросов за ассетами — модульные скрипты по file:// браузерные движки
// блокируют, а встроенный код работает везде.
export default defineConfig({
  root: ".",
  base: "./",
  plugins: [viteSingleFile()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
  },
});

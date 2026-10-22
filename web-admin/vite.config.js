import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

function normalizeBasePath(value, fallback) {
  const text = String(value || "").trim() || fallback;
  if (!text.startsWith("/")) {
    return `/${text.replace(/^\/+/, "").replace(/\/+$/, "")}/`;
  }
  return text.endsWith("/") ? text : `${text}/`;
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const fallbackBase = command === "build" ? "/admin/" : "/";

  return {
    base: normalizeBasePath(env.VITE_PUBLIC_BASE_PATH, fallbackBase),
    plugins: [vue()],
    server: {
      host: "127.0.0.1",
      port: 5173,
    },
  };
});

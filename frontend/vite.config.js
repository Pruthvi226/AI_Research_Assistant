import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    base: process.env.PUBLIC_URL || "/",
    define: {
      "process.env.REACT_APP_API_URL": JSON.stringify(
        env.REACT_APP_API_URL || "",
      ),
      "process.env.NODE_ENV": JSON.stringify(
        mode === "test"
          ? "test"
          : mode === "development"
            ? "development"
            : "production",
      ),
    },
    server: { proxy: { "/api": "http://localhost:5000" } },
    build: {
      outDir: process.env.BUILD_PATH || "build",
      emptyOutDir: true,
      sourcemap: false,
    },
    test: { globals: true, environment: "node", include: ["src/**/*.test.js"] },
  };
});

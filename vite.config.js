import path from "node:path";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

const root = path.resolve(__dirname, "static");

export default defineConfig({
    plugins: [tailwindcss()],
    root,
    base: "/static/",
    build: {
        outDir: path.resolve(root, "dist"),
        emptyOutDir: true,
        manifest: true,
        rollupOptions: {
            input: {
                main: path.resolve(root, "src/main.js"),
            },
        },
    },
    server: {
        host: "0.0.0.0",
        port: 5173,
        strictPort: true,
        cors: true,
        hmr: {
            host: "localhost",
        },
    },
});

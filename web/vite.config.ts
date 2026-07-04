import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import serveStatic from 'serve-static';
import { defineConfig, normalizePath } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';
import tsconfigPaths from 'vite-tsconfig-paths';

const rootDir = fileURLToPath(new URL('.', import.meta.url));
const spiderDir = normalizePath(path.resolve(rootDir, '../spider'));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tsconfigPaths(),
    viteStaticCopy({
      targets: [
        {
          src: `${spiderDir}/data`,
          dest: '.',
        },
        {
          src: `${spiderDir}/img`,
          dest: '.',
        },
      ],
    }),
    {
      name: 'multi-public-dirs',
      configureServer(server) {
        // 添加其他目录为静态资源
        server.middlewares.use('/data', serveStatic(path.resolve(spiderDir, 'data'), { etag: true }));
        server.middlewares.use('/img', serveStatic(path.resolve(spiderDir, 'img'), { etag: true }));
      },
    },
  ],
});

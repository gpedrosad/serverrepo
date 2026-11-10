// Retro76: sitio estático. Se compila en la ThinkPad (scripts/web/build-site.sh) y el resultado
// (web/dist/) lo sirve web/server.py junto con las APIs. Ver docs/features/18-web-astro.md.
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://retro76.cl',
  outDir: '../dist',
  publicDir: './public',          // vacío: imágenes y footer los sirve server.py desde web/assets
  trailingSlash: 'never',
  build: {
    format: 'file',                // /top -> dist/top.html
    inlineStylesheets: 'always',   // el CSS va dentro del HTML: una petición menos
  },
  compressHTML: true,
  devToolbar: { enabled: false },
});

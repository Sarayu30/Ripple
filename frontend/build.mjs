import { build } from 'esbuild';
import { copyFile } from 'node:fs/promises';

for (const name of ['manrope', 'dm-sans']) {
  await copyFile(`node_modules/@fontsource-variable/${name}/files/${name}-latin-wght-normal.woff2`, `app/static/ripple-${name}.woff2`);
  await copyFile(`node_modules/@fontsource-variable/${name}/LICENSE`, `app/static/ripple-${name}-LICENSE.txt`);
}

await build({
  entryPoints: ['frontend/experience.jsx'],
  bundle: true,
  minify: true,
  format: 'iife',
  target: ['es2020'],
  outfile: 'app/static/experience-react.js',
  jsx: 'automatic',
  define: { 'process.env.NODE_ENV': '"production"' },
  legalComments: 'linked',
  external: ['/static/*'],
  logLevel: 'info',
});

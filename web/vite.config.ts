import { defineConfig } from 'vite';

export default defineConfig({
  base: '/master-timeline-chabad/',
  publicDir: '../public',  // serve events.json + stories/ from sibling public/
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});

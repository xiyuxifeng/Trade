import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

function manualChunks(id: string) {
  const normalizedId = id.toString().replaceAll('\\', '/');

  const featureChunks: Array<[RegExp, string]> = [
    [/\/src\/pages\/market\//, 'page-market'],
    [/\/src\/pages\/alerts\//, 'page-alerts'],
    [/\/src\/pages\/jobs\//, 'page-jobs'],
    [/\/src\/pages\/profiles\//, 'page-profiles'],
    [/\/src\/pages\/strategies\//, 'page-strategies'],
    [/\/src\/pages\/backtest\//, 'page-backtest'],
    [/\/src\/pages\/persona\//, 'page-persona'],
    [/\/src\/pages\/artifacts\//, 'page-artifacts'],
    [/\/src\/pages\/system\//, 'page-system'],
    [/\/src\/features\/market-workspace\//, 'feature-market-workspace'],
    [/\/src\/features\/market-browser\//, 'feature-market-browser'],
    [/\/src\/features\/market-datasets\//, 'feature-market-datasets'],
    [/\/src\/features\/alerts\//, 'feature-alerts'],
    [/\/src\/features\/jobs\//, 'feature-jobs'],
    [/\/src\/features\/profiles\//, 'feature-profiles'],
    [/\/src\/features\/strategies\//, 'feature-strategies'],
    [/\/src\/features\/backtests\//, 'feature-backtests'],
    [/\/src\/features\/persona\//, 'feature-persona'],
    [/\/src\/features\/system-status\//, 'feature-system-status'],
    [/\/src\/features\/dashboard\//, 'feature-dashboard'],
  ];
  for (const [pattern, chunkName] of featureChunks) {
    if (pattern.test(normalizedId)) {
      return chunkName;
    }
  }

  if (!id.includes('node_modules')) {
    return undefined;
  }

  if (normalizedId.includes('/node_modules/react/') || normalizedId.includes('/node_modules/react-dom/')) {
    return 'react-vendor';
  }
  if (normalizedId.includes('/node_modules/react-router-dom/') || normalizedId.includes('/node_modules/react-router/')) {
    return 'router-vendor';
  }
  if (normalizedId.includes('/node_modules/@tanstack/react-query/')) {
    return 'query-vendor';
  }
  if (normalizedId.includes('/node_modules/react-hook-form/') || normalizedId.includes('/node_modules/@hookform/resolvers/') || normalizedId.includes('/node_modules/zod/')) {
    return 'forms-vendor';
  }
  if (normalizedId.includes('/node_modules/dayjs/')) {
    return 'time-vendor';
  }
  if (normalizedId.includes('/node_modules/lucide-react/')) {
    return 'icons-vendor';
  }
  if (normalizedId.includes('/node_modules/@testing-library/')) {
    return 'testing-vendor';
  }

  const match = normalizedId.split('node_modules/')[1]?.split('/')[0];
  return match ? `vendor-${match.replace('@', '').replace('/', '-')}` : 'vendor';
}

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});

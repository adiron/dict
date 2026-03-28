import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    sveltekit(),
    {
      name: 'db-watcher',
      configureServer(server) {
        server.watcher.add('data/.reload');
        server.watcher.on('change', (path) => {
          if (!path.endsWith('.reload')) return;
          console.log('[db-watcher] database reloaded, restarting...');
          server.restart();
        });
      },
    },
  ],
});

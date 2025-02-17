import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'
import adapter from '@sveltejs/adapter-node'
import type { Config } from '@sveltejs/kit'
import path from 'path'

const config: Config = {
  kit: {
    adapter: adapter(),
    alias: {
      $lib: path.resolve('./src/lib'),
      '@': path.resolve('./src'),
      '@components': path.resolve('./src/lib/components')
    }
  },
  preprocess: vitePreprocess()
}

export default config 
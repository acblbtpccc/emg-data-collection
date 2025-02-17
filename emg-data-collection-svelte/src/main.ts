import './app.pcss'
import App from './App.svelte'
import { mount } from 'svelte'

mount(App, {
  target: document.getElementById('app')!
})

export default App

<script lang="ts">
  import { Toaster } from "$lib/components/ui/sonner";
  import ControlPanel from "$lib/components/ControlPanel.svelte";
  import ChartGrid from "$lib/components/ChartGrid.svelte";
  import StatusPanel from "$lib/components/StatusPanel.svelte";
  import { io } from "socket.io-client";

  const rootSocket = io('http://localhost:5173', {
    path: '/socket.io',
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 200
  });

  const statusSocket = io('http://localhost:5173/sensor_status', {
    path: '/socket.io',
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 200
  });

  const dataSocket = io('http://localhost:5173/sensor_data', {
    path: '/socket.io',
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 200
  });

  $: {
    statusSocket.on('connect', () => console.log('sensor_status connected'));
    dataSocket.on('connect', () => console.log('sensor_data connected'));
  }
</script>

<Toaster />
<main class="container mx-auto p-4 space-y-4">
  <h1 class="text-2xl font-bold text-center mb-4">MyoTrainer Data Collection Control Panel</h1>
  <ControlPanel socket={statusSocket} />
  <ChartGrid socket={dataSocket} />
  <StatusPanel socket={statusSocket} />
</main>

<style>
  :global(body) {
    padding: 20px;
    margin: 0;
    box-sizing: border-box;
    min-width: 1400px;
  }
</style>

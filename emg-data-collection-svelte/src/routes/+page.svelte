<script lang="ts">
  import { onMount } from 'svelte';
  import ControlPanel from '$lib/components/ControlPanel.svelte';
  import ChartGrid from '$lib/components/ChartGrid.svelte';
  import StatusPanel from '$lib/components/StatusPanel.svelte';
  import { initializeSocket } from '$lib/utils/socket';
  
  let socket: any;
  
  onMount(() => {
    socket = initializeSocket();
    return () => {
      socket.disconnect();
    };
  });
</script>

<div class="container mx-auto p-4 min-w-[1400px]">
  <h1 class="text-3xl font-bold text-center mb-6">
    MyoTrainer Data Collection Control Panel
  </h1>

  <div class="space-y-6">
    <ControlPanel {socket} />
    <ChartGrid {socket} />
    <StatusPanel {socket} />
  </div>
</div> 
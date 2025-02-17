<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Label } from "$lib/components/ui/label";
  import { toast } from "svelte-sonner";
  import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
  } from "$lib/components/ui/select";
  import { Switch } from "$lib/components/ui/switch";
  import { io } from "socket.io-client";


  export let socket: any;
  let isSocketConnected = false;

  let subjectName = '';
  let action = '';
  let pattern = '';

  $: {
    if (subjectName) localStorage.setItem('subjectName', subjectName);
    if (action) localStorage.setItem('action', action);
    if (pattern) localStorage.setItem('pattern', pattern);
  }

  onMount(() => {
    subjectName = localStorage.getItem('subjectName') || '';
    action = localStorage.getItem('action') || '';
    pattern = localStorage.getItem('pattern') || '';

    // To do: connected sensor number status not work yet, 2025-02-17, 11:11
    socket = io("/sensor_status", {
      reconnection: true,
      reconnectionAttempts: 5,
      transports: ["websocket"]
    });

    socket.on("connect", () => {
      isSocketConnected = true;
      console.log("WebSocket connected successfully");
      toast.success('Sensor Connected');
    });

    socket.on("status_update", (data) => {
      console.log("Receive status update:", data);
      connectedSensors = data.connected;
      neededSensors = data.needed;
      areSensorsRunning = data.connected >= data.needed;
    });

    socket.on("connect_error", (err) => {
      console.error("Connect error:", err);
      toast.error('Disconnected');
    });
  });

  onDestroy(() => {
    if (socket) socket.close();
  });

  // basic test variables
  let clickCount = 0;
  let buttonWorks = false;

  // basic test function
  function basicTest() {
    console.log('Basic test clicked');
    clickCount++;
    buttonWorks = true;
  }

  async function testBackend() {
    const testResponse = await fetch('/api/test', {
      method: 'GET',
      headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      console.log('Test response:', testResponse);
  }

  let isSensorsStarting = false;
  let areSensorsRunning = false;

  async function startSensors() {
    isSensorsStarting = true;
    try {
      const response = await fetch('/api/start_sensors');
      if (!response.ok) throw new Error(await response.text());

      areSensorsRunning = true;
      toast.success("Sensors started");
    } catch (error) {
      console.error('Starting sensors failed:', error);
      toast.error(`Starting sensors failed:`);
    } finally {
      isSensorsStarting = false;
    }
  }

  let isCollecting = false;
  let isStarting = false;
  let isStopping = false;

  // 添加倒计时相关状态
  let countdownInput = 3;
  let isCountingDown = false;
  let countdownTime = 0;

  // 修改原收集启动函数
  async function handleStartCollection() {
    if (!subjectName || !action || !pattern) {
      toast.warning("Please fill all info");
      return;
    }

    isStarting = true;
    try {
      // start collection
      const response = await fetch(
        `/api/start_collection?subject=${subjectName}&action=${action}&pattern=${pattern}`
      );
      if (!response.ok) throw new Error(await response.text());

      // start countdown
      isCollecting = true;
      isCountingDown = true;
      countdownTime = countdownInput;

      speak('Start in');
      await new Promise(r => setTimeout(r, 800));

      countdownTime = countdownInput;
      speak(countdownTime.toString());

      const timer = setInterval(() => {
        countdownTime -= 1;
        if (countdownTime > 0) {
          speak(countdownTime.toString());
        } else {
          clearInterval(timer);
          isCountingDown = false;
          speak('Finish!');
          handleStopCollection();
        }
      }, 1000);

      toast.success("Started");
    } catch (error) {
      console.error('Start failed:', error);
      toast.error(`Start failed: ${error.message}`);
    } finally {
      isStarting = false;
    }
  }

  async function handleStopCollection() {
    isStopping = true;
    try {
      const response = await fetch('/api/stop_collection');
      if (!response.ok) throw new Error(await response.text());

      isCollecting = false;
      toast.success("Data collection stopped");
    } catch (error) {
      console.error('Stopping failed:', error);
      toast.error(`Stopping failed: ${error.message}`);
    } finally {
      isStopping = false;
    }
  }

  console.log('Button component:', Button);

  function handleSvelteButton() {
    console.log('Svelte button clicked');
  }

  type ButtonEvent = MouseEvent & { currentTarget: EventTarget & HTMLButtonElement };

  let switchValue = false;
  let selectValue = "";

  onMount(() => {
    console.log('Button component loaded:', Button);
  });

  function handleButtonClick() {
    console.log('Button clicked');
    try {
      handleStartCollection();
    } catch (error) {
      console.error('Error in button click:', error);
    }
  }

  let connectedSensors = 0;
  let neededSensors = 8;

  console.log('Connected sensors:', connectedSensors);
  console.log('Needed sensors:', neededSensors);


  onMount(async () => {
    socket?.emit('request_status');

    socket?.on('status_update', (data) => {
      connectedSensors = data.connected;
      neededSensors = data.needed;
      localStorage.setItem('sensor_status', JSON.stringify(data));
    });

    // restore from local storage
    const cached = localStorage.getItem('sensor_status');
    if (cached) {
      const data = JSON.parse(cached);
      connectedSensors = data.connected;
      neededSensors = data.needed;
    }
  });

  socket?.on('connect_error', (err) => {
    console.error('Status connection error:', err);
  });

  socket?.on('disconnect', () => {
    console.log('Disconnected from server');
    connectedSensors = 0;
    neededSensors = 8;
    localStorage.removeItem('sensor_status');
    toast.error('Disconnected from server');
  });

  // connection status changes
  $: if (socket?.connected) {
    toast.success('Sensor Connected');
  }

  $: if (socket && !socket.connected) {
    toast.error('Disconnected from server');
  }

  let synth: SpeechSynthesis;
  let voices: SpeechSynthesisVoice[];

  onMount(() => {
    synth = window.speechSynthesis;
    // voice loading
    const updateVoices = () => {
      voices = synth.getVoices().filter(v => v.lang === 'en-US');
    };
    synth.onvoiceschanged = updateVoices;
    updateVoices();
  });

  function speak(text: string) {
    if (!synth || !voices.length) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voices.find(v => v.name.includes('Google')) || voices[0];
    utterance.rate = 1.2; // voice rate
    utterance.pitch = 1.2; // voice tone
    synth.speak(utterance);
  }


</script>

<Card>
  <CardHeader>
    <CardTitle>Control Panel (Debug Mode)</CardTitle>
  </CardHeader>
  <CardContent>

    <div class="grid grid-cols-3 gap-4 mb-4">
      <div class="space-y-2">
        <Label for="subjectName">Subject Name</Label>
        <Input id="subjectName" bind:value={subjectName} />
      </div>
      <div class="space-y-2">
        <Label for="action">Action</Label>
        <Input id="action" bind:value={action} />
      </div>
      <div class="space-y-2">
        <Label for="pattern">Movement Pattern</Label>
        <Input id="pattern" bind:value={pattern} />
      </div>
      <div class="space-y-2">
        <Label>Sensor Status</Label>
        <div class="flex items-center gap-2 p-2 border rounded-md bg-muted/50">
          <div class="flex-1">
            <span class="text-sm font-medium">{connectedSensors}/{neededSensors} Connected</span>
            <div class="h-2 bg-gray-200 rounded-full">
              <div
                class="h-full bg-green-500 rounded-full transition-all duration-500"
                style={`width: ${(connectedSensors/neededSensors)*100}%`}
              ></div>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-4 space-y-2">
        <Label for="countdown">Countdown (Seconds)</Label>
        <Input
          id="countdown"
          type="number"
          bind:value={countdownInput}
          min="1"
          max="300"
          disabled={isCollecting || isCountingDown}
        />
      </div>

    </div>

    <div class="flex gap-4 mt-6">
      <Button
        variant={areSensorsRunning ? "secondary" : "default"}
        onclick={startSensors}
        disabled={areSensorsRunning || isSensorsStarting}
      >
        {#if isSensorsStarting}
          Starting ({connectedSensors}/{neededSensors})...
        {:else if areSensorsRunning}
          Sensors Started
        {:else}
          Start Sensors
        {/if}
      </Button>

      <Button
        variant={isCollecting ? "secondary" : "default"}
        onclick={handleStartCollection}
        disabled={isCollecting || isStarting || isStopping}
      >
        {#if isStarting}
          Starting...
        {:else if isCountingDown}
          <span class="blinking">Countdown: {countdownTime}s</span>
        {:else if isCollecting}
          Collecting...
        {:else}
          Start Collection
        {/if}
      </Button>

      <Button
        variant="destructive"
        onclick={handleStopCollection}
        disabled={!isCollecting || isStopping}
      >
        {isStopping ? 'Stopping...' : 'Stop Collection'}
      </Button>
    </div>

  </CardContent>
</Card>

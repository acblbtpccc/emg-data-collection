<!-- author: boluo -->
 <!-- 2024-12-25 15:13 -->
<!-- x label have problem, but can stablely collect for more than 1 hour -->
<script lang="ts">
  import { onMount } from 'svelte';
  import * as echarts from 'echarts';
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card";
  import { throttle } from 'lodash-es';
  import type { Socket } from 'socket.io-client';

  export let socket: Socket;

  const MUSCLE_GROUPS = ['Biceps', 'Deltoids', 'Latiss', 'Trapezius'];
  let charts = {};
  let emgValues = {};

  const MAC_TO_MUSCLE ={
    'E4:65:B8:14:BA:9A': { id: '01', name: 'L_Biceps', group: 'Biceps' },
    'D4:8A:FC:C5:8B:B2': { id: '02', name: 'R_Biceps', group: 'Biceps' },
    'E4:65:B8:14:79:5E': { id: '03', name: 'L_Deltoid', group: 'Deltoids' },
    'D4:8A:FC:C5:A5:CA': { id: '04', name: 'R_Deltoid', group: 'Deltoids' },
    'D4:8A:FC:C4:B0:C6': { id: '05', name: 'L_Latiss', group: 'Latiss' },
    'D4:8A:FC:C5:AB:32': { id: '06', name: 'R_Latiss', group: 'Latiss' },
    'D4:8A:FC:C5:9E:12': { id: '07', name: 'L_Trapezius', group: 'Trapezius' },
    'D4:8A:FC:C5:06:7E': { id: '08', name: 'R_Trapezius', group: 'Trapezius' },
    'EEF3BA12-3B30-2C9B-2969-BC28E44D5524': { id: '01', name: 'L_Biceps', group: 'Biceps' },
    '47379FCE-9307-45EB-A7A2-06FBE7FCF125': { id: '02', name: 'R_Biceps', group: 'Biceps' },
    '96B35F9D-E06E-E5FB-79A3-030CC55A4545': { id: '03', name: 'L_Deltoid', group: 'Deltoids' },
    '133D0F9C-2147-626D-53D9-769BB86AA1F2': { id: '04', name: 'R_Deltoid', group: 'Deltoids' },
    'A3A4C3F9-8554-F3CA-D3E0-CCFAB0AD544E': { id: '05', name: 'L_Latiss', group: 'Latiss' },
    '8FDD7C6A-C5E4-3D7C-7B51-C3A2F2C184D4': { id: '06', name: 'R_Latiss', group: 'Latiss' },
    '0D1B85BC-6814-3153-6A91-F0DC0D987177': { id: '07', name: 'L_Trapezius', group: 'Trapezius' },
    '2A659F4D-D6AE-CC59-BFC8-EDD0C0C1220C': { id: '08', name: 'R_Trapezius', group: 'Trapezius' }
  };

  const MAX_QUEUE_SIZE = 100;
  const MAX_TIME_DIFF = 10000; // 10秒
  const UPDATE_INTERVAL = 16; // 约60fps
  let lastUpdateTime = 0;

  function createChartOptions() {
    return {
      animation: false,
      progressive: 0,
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          params = params[0];
          const date = new Date(params.value[0]);
          return `${date.toLocaleTimeString()} : ${params.value[1]}`;
        },
        axisPointer: {
          animation: false,
          type: 'line'
        }
      },
      // tooltip: {
      //   show: false,  // test if tooltip is needed
      //   trigger: 'none'
      // },
      grid: {
        left: '20%',
        right: '5%',
        top: '10%',
        bottom: '20%'
      },
      xAxis: {
        type: 'time',
        splitLine: { show: true },
        axisLabel: {
          show: true,
          formatter: (value) => {
            return new Date(value).toLocaleTimeString();
          },
          rotate: 30,
          margin: 15,
          align: 'center',
          // hideOverlap: true
        },
        // interval: 5000,
        // splitNumber: 10,
        axisPointer: {
          show: true,
          snap: true,
          label: {
            formatter: function(params) {
              return echarts.format.formatTime('hh:mm:ss', params.value);
            }
          }
        }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 4000,
        splitLine: { show: false }
      },
      series: []
    };
  }

  const throttledUpdateCharts = throttle(() => {
    const now = Date.now();
    if (now - lastUpdateTime < UPDATE_INTERVAL) return;
    lastUpdateTime = now;

    const groupedSeries = {};
    Object.entries(emgValues).forEach(([mac, values]) => {
      const muscleInfo = MAC_TO_MUSCLE[mac] || {
        id: '01',
        name: 'Unknown_' + mac,
        group: 'Biceps'
      };

      const group = muscleInfo.group;
      if (!groupedSeries[group]) {
        groupedSeries[group] = {
          legendData: [],
          series: []
        };
      }

      const color = muscleInfo.name.startsWith('L_')
      ? '#3498db'  // left mulscle
      : '#e74c3c'; // right mulscle
      groupedSeries[group].legendData.push(`${muscleInfo.name} (ID: ${muscleInfo.id})`);
      groupedSeries[group].series.push({
        name: `${muscleInfo.name} (ID: ${muscleInfo.id})`,
        type: 'line',
        data: values,
        sampling: 'lttb',
        lineStyle: {
          width: 3
        },
        animation: false,
        smooth: false,
        symbol: 'none',
        itemStyle: { color }
      });
    });

    requestAnimationFrame(() => {
      const currentTime = Date.now();
      const minTime = currentTime - MAX_TIME_DIFF;

      console.log('Chart update time range:', {
        minTime,
        minTimeFormatted: new Date(minTime).toLocaleTimeString(),
        currentTime,
        currentTimeFormatted: new Date(currentTime).toLocaleTimeString()
      });

      Object.entries(groupedSeries).forEach(([group, data]) => {
        const chart = charts[group];
        try {
          const formattedData = data.series.map(series => ({
            ...series,
            data: series.data.map(item => {
              const timestamp = typeof item[0] === 'object' ? item[0].getTime() : Number(item[0]);
              return [timestamp, item[1]];
            })
          }));

          chart?.setOption({
            legend: { data: data.legendData },
            series: formattedData,
            xAxis: {
              // type: 'time',
              // sampling: 'lttb',
              // smooth: false,
              // animation: false,
              min: minTime,
              max: currentTime,
              splitLine: { show: true },
              axisLabel: {
                show: true,
                formatter: function(value) {
                  return echarts.format.formatTime('hh:mm:ss', value);
                },
                rotate: 30,
                margin: 15,
                align: 'right'
              },
              // minInterval: 1000,
              // maxInterval: 2000,
              // Interval: 3000,
              // splitNumber: 5
            }
          }, {
            silent: true,
            notMerge: false,
            lazyUpdate: true,
            // replaceMerge: ['series', 'xAxis'],
            // replaceMerge: ['series'],
            // replaceMerge: ['xAxis']
          });
        } catch (error) {
          console.warn('Chart update error:', error);
        }
      });
    });
  }, 50, { leading: true, trailing: true });

  function handleEmgData(data) {
    console.log('Raw timestamp from data:', data.timestamp);
    const timestamp = new Date(data.timestamp).getTime();
    console.log('Converted timestamp:', timestamp);
    console.log('Formatted time:', new Date(timestamp).toLocaleTimeString());

    if (!emgValues[data.mac]) {
      emgValues[data.mac] = [];
    }

    const queue = emgValues[data.mac];
    queue.push([timestamp, data.value]);

    if (queue.length > MAX_QUEUE_SIZE) {
      queue.shift();
    }

    throttledUpdateCharts();
  }

  onMount(() => {
    if (!socket) {
      console.error('Socket is not initialized');
      return;
    }

    MUSCLE_GROUPS.forEach(group => {
      const chart = echarts.init(document.getElementById(`chart${group}`));
      chart.setOption(createChartOptions());
      charts[group] = chart;
    });

    socket.on('sensor_data', handleEmgData);

    // 监听连接状态
    socket.on('connect', () => {
      console.log('Connected to WebSocket server');
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from WebSocket server');
    });

    return () => {
      Object.values(charts).forEach(chart => chart?.dispose());
      socket?.off('sensor_data', handleEmgData);
      socket?.off('connect');
      socket?.off('disconnect');
      throttledUpdateCharts.cancel();
    };
  });
</script>

<Card>
  <CardHeader>
    <CardTitle>Visualization</CardTitle>
  </CardHeader>
  <CardContent>
    <div class="grid grid-cols-4 gap-4 h-[300px]">
      {#each MUSCLE_GROUPS as group}
        <div id="chart{group}" class="w-full h-full"></div>
      {/each}
    </div>
  </CardContent>
</Card>
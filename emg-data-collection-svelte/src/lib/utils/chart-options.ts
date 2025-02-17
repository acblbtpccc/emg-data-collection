export function createChartOptions() {
  return {
    grid: {
      top: 30,
      right: 8,
      bottom: 24,
      left: 36
    },
    xAxis: {
      type: 'time',
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [{
      type: 'line',
      showSymbol: false,
      data: []
    }]
  };
} 
<script lang="ts">
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card";
  import { Alert, AlertDescription } from "$lib/components/ui/alert";

  let bufferedAmount = 0;
  let latestEmgData = [];

  // function updateBufferedAmount() {
  //   // WebSocket buffer
  // }
</script>

<Card>
  <CardHeader>
    <CardTitle>Status</CardTitle>
  </CardHeader>
  <CardContent class="space-y-4">
    <Alert>
      <AlertDescription>
        WebSocket Buffer: {bufferedAmount} bytes
      </AlertDescription>
    </Alert>

    <div class="space-y-2">
      <h3 class="text-lg font-semibold">Latest EMG Data</h3>
      <ul class="space-y-2">
        {#each latestEmgData as data}
          <li class="p-2 bg-secondary rounded">
            {JSON.stringify(data)}
          </li>
        {/each}
      </ul>
    </div>
  </CardContent>
</Card>
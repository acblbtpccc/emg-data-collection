# Part I: frontend

### Core Modules: 
  - svelte
  - echarts
  - websocket
  - ...

## Frontend Folder
```bash
cd emg-data-collection-svelte
```

## Install fnm (faster version alternative to nvm)

```bash
curl -fsSL https://fnm.vercel.app/install | bash
```

## Use node 18

```bash
fnm use 18
fnm default 18
```

## Install pnpm

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
source /root/.bashrc
```

## Run Frontend

```bash
pnpm install
pnpm dev
```

# Part II: Backend 
## Core Modules: 
  - bleak(BLE)
  - asyncio
  - flask
  - ...

## Main Program: 
  - collect_data_web_fixtime_svelte.py(entry, web)
  - bleak_central_mac.py(BLE, data emit)
  - collect_data_all.py(file writing)

## Install Dependencies: 


```bash
1. create conda environment
conda activate emg-data-collection

2. install python libraries

pip install -r requirements.txt

flask
pyserial
websockets
numpy
yacs
flask_socketio
ntplib
requests
bleak
flask_cors

3. install opencv with conda(for AVC1)
conda install opencv 

```

## Run Backend

```bash
python collect_data_web_fixtime_svelte.py
```

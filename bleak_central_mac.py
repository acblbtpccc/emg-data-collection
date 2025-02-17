import asyncio
import json
import ntplib
import time
from datetime import datetime, timezone, timedelta
import threading
import requests
from bleak import BleakClient, BleakScanner
import os
from threading import Lock

# Debug parameters
debug_logging = True
running_mode = "up-to-host"
needed_client_numbers = 8

vec_myo_ware_shields_lock = threading.Lock()
shield_list_number = 0
data_received_lock = threading.Lock()
data_received = [False] * 10

last_memory_check = 0
peripheral_interval = 10
interval = 100

got_connect_config = False
enable_connection_params = False

vec_myo_ware_shields = []
vec_myo_ware_clients = []

# UUIDs for the MyoWare service and characteristic
myo_ware_service_uuid = "ec3af789-2154-49f4-a9fc-bc6c88e9e930"
myo_ware_characteristic_uuid = "f3a56edf-8f1e-4533-93bf-5601b2e91308"

# JSON document for storing notifications
on_notify_call_buffer = {}
notify_buffer_lock = threading.Lock()  # Lock for accessing on_notify_call_buffer
serial_pre_values = [0] * 10

host = "cdn.1f2.net"
port = 80
config_path = "/emg_central_connect_config.json"

class ConnectionParams:
    def __init__(self):
        self.min_interval = None
        self.max_interval = None
        self.latency = None
        self.timeout = None
        self.scan_interval = None
        self.scan_window = None

connection_params = ConnectionParams()

# 更新NTP服务器配置（区分协议类型）
NTP_SERVERS = [
    # 标准NTP协议服务器（UDP 123端口）
    {"host": "ntp.aliyun.com", "type": "ntp"},
    {"host": "ntp1.tencent.com", "type": "ntp"},
    {"host": "time.amazonaws.com", "type": "ntp"},
    # HTTP时间API服务
    {"host": "worldtimeapi.org/api/timezone/Asia/Shanghai", "type": "http"},
    {"host": "api.timezonedb.com/v2.1/get-time-zone", "type": "http"}
]

async def get_ntp_time():
    client = ntplib.NTPClient()

    for server in NTP_SERVERS:
        for attempt in range(2):  # 每个服务器尝试2次
            try:
                if server["type"] == "ntp":
                    # 处理标准NTP协议
                    response = client.request(
                        server["host"],
                        port=123,  # 显式指定NTP端口
                        version=3,
                        timeout=3
                    )
                    return response.tx_time
                else:
                    # 处理HTTP时间API
                    response = requests.get(
                        f"http://{server['host']}",
                        timeout=3,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        print(f"Using {server['type']} server: {server['host']}")
                        return datetime.fromisoformat(data['datetime']).timestamp()

            except Exception as e:
                error_detail = f"{type(e).__name__}: {str(e)}"
                print(f"Error from {server['host']} (attempt {attempt+1}): {error_detail}")
                await asyncio.sleep(0.5)

    # 所有服务器失败时使用本地时间
    print("WARNING: All time servers failed, using local system time")
    return datetime.now().timestamp()

ntp_time = 0
boot_time_millis = 0



# def print_memory_usage():
#     import psutil
#     memory_info = psutil.virtual_memory()
#     print(f"Free memory: {memory_info.available} bytes")

# def get_formatted_date_time(elapsed_millis):
#     raw_time = ntp_time + elapsed_millis / 1000
#     hong_kong_time = datetime.fromtimestamp(raw_time, tz=timezone(timedelta(hours=8)))
#     timestamp = hong_kong_time.strftime('%Y-%m-%d %H:%M:%S')
#     milliseconds = elapsed_millis % 1000
#     return f"{timestamp}.{milliseconds:03d}"


status_lock = Lock()
# 添加全局状态存储
class SensorStatus:
    def __init__(self):
        self.connected = 0
        self.needed = 8
        self.last_updated = time.time()

sensor_status = SensorStatus()

# update sensor number status
def update_sensor_status(connected, needed):
    sensor_status.connected = connected
    sensor_status.needed = needed
    sensor_status.last_updated = time.time()
    # 实时推送
    socketio.emit('status_update', {
        'connected': connected,
        'needed': needed
    }, namespace='/sensor_status')

# push status update every second
def background_status_push():
    while True:
        socketio.sleep(1)  # 每秒推送一次
        socketio.emit('status_update', {
            'connected': sensor_status.connected,
            'needed': sensor_status.needed
        }, namespace='/sensor_status')

def create_notify_callback(client, emg_queue, stop_event):
    async def notify_callback(sender, data):
        global boot_time_millis
        current_millis = int(time.time() * 1000)
        elapsed_millis = current_millis - boot_time_millis

        try:
            # services = await client.get_services()
            # for service in services:
            #     print(f"Service: {service.uuid}")
            #     for characteristic in service.characteristics:
            #         print(f"  Characteristic: {characteristic.uuid}")

            address = client.address
            # for macos
            # address = sender.obj.peripheral().identifier().UUIDString()
        except AttributeError:
            print("Error: Could not retrieve the device address from the sender object.")
            return

        if running_mode == "up-to-host":
            # Add data to JSON document
            with notify_buffer_lock:
                peripheral = on_notify_call_buffer.setdefault(address, {})
                values_array = peripheral.setdefault("values", [])

                for i in range(len(data) // 2):
                    value = int.from_bytes(data[i*2:i*2+2], byteorder='big')
                    timestamp_millis = current_millis - (len(data) // 2 - 1 - i) * peripheral_interval
                    timestamp = datetime.fromtimestamp(timestamp_millis / 1000.0).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    values_array.append({"timestamp": timestamp, "value": value})
                    if not stop_event.is_set():
                        emg_queue.put((timestamp, address, value))

                # Only emit the last data point of the packet
                socketio.emit('sensor_data', {
                    'timestamp': timestamp,
                    'mac': address,
                    'value': value
                }, namespace='/sensor_data')

                # print('timestamp:', timestamp, 'mac:', address, 'value:', value)
                # print(json.dumps(on_notify_call_buffer))

                # Clear the document for the next notification
                on_notify_call_buffer.clear()
        # elif running_mode == "standalone":
        #     address_index = next((i for i, a in enumerate(vec_myo_ware_shields) if a == address), None)
        #     if address_index is None:
        #         print("Address not found in vector")
        #         return

        #     for i in range(len(data) // 2):
        #         serial_pre_values[i] = int.from_bytes(data[i*2:i*2+2], byteorder='big')

        #     with data_received_lock:
        #         data_received[address_index] = True

        #     all_received = all(data_received[:len(vec_myo_ware_shields)])

        #     if all_received:
        #         if debug_logging:
        #             print(f"Received all peripheral data: {serial_pre_values}")

        #         # Reset data_received array for the next batch
        #         with data_received_lock:
        #             for i in range(len(vec_myo_ware_shields)):
        #                 data_received[i] = False
    return notify_callback

async def on_advertised_device(device, advertisement_data):
    print(f"Detected device: {device.address} with RSSI: {device.rssi}")
    print(f"Advertisement Data: {advertisement_data}")

    if myo_ware_service_uuid in [str(uuid) for uuid in advertisement_data.service_uuids]:
        if debug_logging:
            print(f"Found MyoWare Wireless Shield: {device.address}")

        with vec_myo_ware_shields_lock:
            if device.address not in vec_myo_ware_shields:
                vec_myo_ware_shields.append(device.address)
                global shield_list_number
                shield_list_number += 1
                print(f"ShieldListNumber: {shield_list_number}")
            else:
                if debug_logging:
                    print(f"Duplicate Shield found: {device.address}")

# async def fetch_connection_params():
#     global got_connect_config, running_mode, enable_connection_params, needed_client_numbers

#     connect_config_attempts = 0
#     while not got_connect_config and connect_config_attempts <= 5:
#         try:
#             response = requests.get(f"http://{host}:{port}{config_path}")
#             if response.status_code == 200:
#                 connect_config_json = response.json()

#                 running_mode = connect_config_json["runningMode"]
#                 enable_connection_params = connect_config_json["enableconnectionParams"]
#                 needed_client_numbers = connect_config_json["NeededClientNumbers"]

#                 connection_params.min_interval = connect_config_json["minInterval"]
#                 connection_params.max_interval = connect_config_json["maxInterval"]
#                 connection_params.latency = connect_config_json["latency"]
#                 connection_params.timeout = connect_config_json["timeout"]
#                 connection_params.scan_interval = connect_config_json["scanInterval"]
#                 connection_params.scan_window = connect_config_json["scanWindow"]

#                 got_connect_config = True
#                 return True
#         except Exception as e:
#             print(f"Error fetching connection parameters: {e}")
#             connect_config_attempts += 1
#             await asyncio.sleep(1)
#     return False

async def on_disconnected(client):
    global vec_myo_ware_clients
    if client in vec_myo_ware_clients:
        vec_myo_ware_clients.remove(client)
        print(f"❌ Disconnected from {client.address} (剩余连接数: {len(vec_myo_ware_clients)-1}/{needed_client_numbers})")
        update_sensor_status(len(vec_myo_ware_clients), needed_client_numbers)
    while True:
        print(f"Device {client.address} disconnected")

async def connect_to_shields(emg_queue, stop_event):
    global vec_myo_ware_clients, needed_client_numbers
    needed_client_numbers = len(vec_myo_ware_shields)

    while len(vec_myo_ware_clients) < needed_client_numbers:
        for address in vec_myo_ware_shields:
            if address in [client.address for client in vec_myo_ware_clients]:
                continue
            print(f"Current trying to connect address: {address}")
            shield_connected = False
            shield_connected_try_times = 0

            while not shield_connected and shield_connected_try_times < 10:
                try:
                    client = BleakClient(address)
                    await client.connect()
                    shield_connected = client.is_connected
                    if shield_connected:
                        vec_myo_ware_clients.append(client)
                        print(f"✅ Connected to {address} (Current numbers: {len(vec_myo_ware_clients)+1}/{needed_client_numbers})")
                        update_sensor_status(len(vec_myo_ware_clients), needed_client_numbers)
                        break
                except Exception as e:
                    print(f"Error connecting to {address}: {e}")

                shield_connected_try_times += 1
                await asyncio.sleep(0.2)

            if not shield_connected:
                print(f"Trials to connect to the shield exceed 10 times, give up connect.")

            if shield_connected:
                try:
                    notify_callback = create_notify_callback(client, emg_queue, stop_event)
                    await client.start_notify(myo_ware_characteristic_uuid, notify_callback)
                    print("Subscribed to notifications")
                except Exception as e:
                    print(f"Error subscribing to notifications: {e}")

    return True

async def monitor_connections(check_interval=30):
    global vec_myo_ware_clients

    while True:
        await asyncio.sleep(check_interval)
        for client in vec_myo_ware_clients:
            if not client.is_connected:
                update_sensor_status(len(vec_myo_ware_clients), needed_client_numbers)
                print('Stopping the program due to a sensor disconnection!', client.address)
                tasks = [client.disconnect() for client in vec_myo_ware_clients if client.is_connected] # disconnect all client
                await asyncio.gather(*tasks)
                os._exit(1)
            else:
                print("all client still connected")

async def main(socketio_instance, emg_queue, stop_event):
    global ntp_time, boot_time_millis, socketio
    socketio = socketio_instance  # Use the passed SocketIO instance



    # Fetch NTP time
    ntp_time = await get_ntp_time()
    boot_time_millis = int(time.time() * 1000)
    print(f"NTP time obtained: {datetime.fromtimestamp(ntp_time)}")

    # Fetch ConnectionParams from the URL
    # if await fetch_connection_params():
    #     print("Connection parameters fetched successfully.")
    # else:
    #     print("Failed to fetch connection parameters.")

    # Start scanning for MyoWare Wireless Shields
    if debug_logging:
        print(f"Scanning for MyoWare Wireless Shields: {myo_ware_service_uuid}")

    scanner = BleakScanner(detection_callback=on_advertised_device)
    await scanner.start()
    await asyncio.sleep(8)
    await scanner.stop()

    print("Scan done!")
    print(f"Found {len(vec_myo_ware_shields)} MyoWare Wireless Shields")
    if len(vec_myo_ware_shields)!= needed_client_numbers:
        print('sensor didnot found complete!!!!!!!!!')
        os._exit(1)

    if not vec_myo_ware_shields:
        print("No MyoWare Wireless Shields found!")
        return

    connection_success = await connect_to_shields(emg_queue, stop_event)
    socketio.start_background_task(background_status_push)
    if connection_success:
        await asyncio.create_task(monitor_connections())

    while True:
        await asyncio.sleep(10)

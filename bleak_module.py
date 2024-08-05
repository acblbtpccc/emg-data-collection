# # bleak_module.py
# import asyncio
# import threading
# import time
# import logging
# from datetime import datetime
# from bleak import BleakClient, BleakScanner, BleakGATTCharacteristic
# from queue import Queue

# MYOWARE_SERVICE_UUID = "ec3af789-2154-49f4-a9fc-bc6c88e9e930"
# MYOWARE_CHARACTERISTIC_UUID = "f3a56edf-8f1e-4533-93bf-5601b2e91308"
# READ_INTERVAL_MS = 100  # 设定外围设备的读取间隔时间为100毫秒

# # 配置日志记录
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class BleakHandler:
#     def __init__(self):
#         self.devices = []
#         self.clients = []
#         self.data_queue = Queue()
#         self.device_address_map = {}
#         self.loop = asyncio.new_event_loop()
#         self.thread = threading.Thread(target=self.start_loop, args=(self.loop,))
#         self.thread.start()

#     def start_loop(self, loop):
#         asyncio.set_event_loop(loop)
#         loop.run_forever()

#     def stop_loop(self):
#         self.loop.call_soon_threadsafe(self.loop.stop)
#         self.thread.join()

#     def scan_callback(self, device, advertisement_data):
#         logger.info(f"Discovered device: {device.address}, Name: {device.name}, RSSI: {device.rssi}")
#         if MYOWARE_SERVICE_UUID in device.metadata.get("uuids", []):
#             self.devices.append(device)

#     async def scan_devices(self):
#         logger.info("Scanning for devices...")
#         scanner = BleakScanner()
#         scanner.register_detection_callback(self.scan_callback)
#         await scanner.start()
#         await asyncio.sleep(20)  # 扫描5秒
#         await scanner.stop()
#         logger.info(f"Found {len(self.devices)} devices with MyoWare service.")

#     async def connect_device(self, device):
#         logger.info(f"Connecting to device {device.address}...")
#         client = BleakClient(device)
#         await client.connect()
#         self.device_address_map[client] = device.address  # 保存设备的 MAC 地址
#         await client.start_notify(
#             MYOWARE_CHARACTERISTIC_UUID,
#             self.notify_callback
#         )
#         self.clients.append(client)
#         logger.info(f"Connected to device {device.address}.")

#     def notify_callback(self, sender: BleakGATTCharacteristic, data: bytearray):
#         client = sender.client  # 获取 client 对象
#         address = self.device_address_map.get(client, "Unknown")  # 获取设备的 MAC 地址
#         current_millis = int(time.time() * 1000)  # 当前时间戳（毫秒）
#         total_data_points = len(data) // 2

#         values = []
#         for i in range(total_data_points):
#             value = int.from_bytes(data[i*2:i*2+2], byteorder='big')
#             adjusted_elapsed_millis = current_millis - (total_data_points - 1 - i) * READ_INTERVAL_MS
#             timestamp = datetime.fromtimestamp(adjusted_elapsed_millis / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
#             values.append({"timestamp": timestamp, "value": value})

#         self.data_queue.put({address: {"values": values}})

#     def start_scan_and_connect(self):
#         asyncio.run_coroutine_threadsafe(self.scan_and_connect(), self.loop)

#     async def scan_and_connect(self):
#         await self.scan_devices()
#         for device in self.devices:
#             await self.connect_device(device)

#     def get_data(self):
#         data = []
#         while not self.data_queue.empty():
#             data.append(self.data_queue.get())
#         return data

# bleak_handler = BleakHandler()
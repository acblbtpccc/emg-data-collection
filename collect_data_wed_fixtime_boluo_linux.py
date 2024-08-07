from flask import Flask, request, render_template, jsonify
import json
import time
import logging
import threading
import queue
import asyncio
import subprocess
import datetime
import os  # Added import for os
from flask_socketio import SocketIO, emit
from collect_data_all import prepare_output_dir, collect_depthandrgb, collect_emg, parse_args, save_depthandrgb_web, save_emg_web
from config import parse_args, parse_args_sensors, DEPTH_DIR, RGB_DIR, EMG_DIR, DATA_DIR
from camera_utils import init_camera, set_datamode, set_resolution, set_mapper, set_range
from DCAM710.API.Vzense_api_710_aiot_modified import *
from serial.serialutil import SerialException
from collect_logger import logger
import bleak_central_mac  # Import the module
logging.getLogger('werkzeug').setLevel(logging.INFO)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

threads = []
emg_queue = queue.Queue()
camera = None

# Flag to indicate if data collection is running
is_collecting = {"depth_and_rgb": False, "emg": False}
# Events to signal threads to stop
stop_events = {"depth_and_rgb": threading.Event(), "emg": threading.Event()}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_sensors')
def start_sensors():
    global threads
    global camera

    def list_usb_devices():
        try:
            result = subprocess.run(['lsusb'], capture_output=True, text=True, check=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred: {e}")

    def test_device_access(busnum, devnum):
        device_path = f"/dev/bus/usb/{busnum:03}/{devnum:03}"
        try:
            with open(device_path, 'rb') as device_file:
                print(f"Successfully opened {device_path} for reading.")
                # read some data to test usb
                data = device_file.read(1000)
                print(f"Read data: {data}")
        except PermissionError:
            print(f"Permission denied: Could not open {device_path}.")
        except FileNotFoundError:
            print(f"Device not found: {device_path}.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def start_depth(cfg):
        # init camera
        camera = init_camera()
        logger.info(f"init_camera")

        # set mode: Output both Depth and RGB frames in 30fps
        set_datamode(camera, mode='PsDepthAndRGB_30')

        # set RGB resoultion: (640, 280), (1280, 720), (640, 360)
        set_resolution(camera, resol='PsRGB_Resolution_640_480')  

        # mapping RGB image to depth camera space
        # set_mapper(camera, mapper='r2d') 

        # set depth range: near, mid, far
        set_range(camera, range='far')

        return camera

    # start depth camera
    cfg, _ = parse_args_sensors()
    camera = start_depth(cfg)
    time.sleep(1)

    read_try_times = 100
    while read_try_times > 0:
        depth_ret, _ = camera.Ps2_ReadNextFrame()
        if depth_ret != 0:
            print("Ps2_ReadNextFrame failed:", depth_ret, read_try_times)
        if depth_ret == 0:
            print("Ps2_ReadNextFrame successful")
            break
        read_try_times -= 1
        time.sleep(1)

    if depth_ret != 0:
        print("Depth camera not connected.")
        return jsonify({"status": "Depth No Data Read Out"}), 500

    stop_events["emg"].set()
    asyncio.run(bleak_central_mac.main(socketio, emg_queue, stop_events["emg"])) # Pass the SocketIO instance
    
    return jsonify({"status": "Sensors started successfully"}), 200


@app.route('/start_collection')
def start_collection():
    logger.info(f"start collection")
    global threads
    global camera
    
    subject = request.args.get('subject')
    action = request.args.get('action')
    pattern = request.args.get('pattern')
    
    if not subject or not action or not pattern:
        return jsonify({"status": "Missing subject or action or Description"}), 400
    
    cfg, _ = parse_args(subject, action)
    cfg = prepare_output_dir(cfg)

    current_sec = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    label_path = os.path.join(cfg.label_dir, current_sec + '.txt')

    # Write the label value to the label_path.txt file
    with open(label_path, 'w') as f:
        f.write(pattern)

    if not is_collecting["depth_and_rgb"]:
        is_collecting["depth_and_rgb"] = True
        stop_events["depth_and_rgb"].clear()
        thread1 = threading.Thread(target=save_depthandrgb_web, args=(cfg, camera, stop_events["depth_and_rgb"], current_sec))
        thread1.start()
        threads.append(thread1)
        logger.info(f"save_depth_rgb thread collection")
        
    if not is_collecting["emg"]:
        is_collecting["emg"] = True
        stop_events["emg"].clear()
        thread2 = threading.Thread(target=save_emg_web, args=(cfg, stop_events["emg"], current_sec, emg_queue))
        thread2.start()
        threads.append(thread2)
        logger.info(f"save_emg_web thread collection")
    
    return jsonify({"status": "Data collection started"})

def trigger_stop_collection():
    global is_collecting

    stop_events["depth_and_rgb"].set()
    stop_events["emg"].set()

    for thread in threads:
        if thread.is_alive():
            thread.join()

    is_collecting = {"depth_and_rgb": False, "emg": False}

    threads.clear()

@app.route('/stop_collection')
def stop_collection():
    global is_collecting

    stop_events["depth_and_rgb"].set()
    stop_events["emg"].set()

    for thread in threads:
        if thread.is_alive():
            thread.join()

    is_collecting = {"depth_and_rgb": False, "emg": False}

    threads.clear() 
    return jsonify({"status": "Data collection stopped"})

@app.route('/countdown')
def countdown():
    return render_template('countdown.html')
    
async def disconnect_all_clients():
    for client in bleak_central_mac.vec_myo_ware_clients:
        try:
            await client.disconnect()
            print(f"Disconnected from {client.address}")
        except Exception as e:
            print(f"Error disconnecting from {client.address}: {e}")

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Start socketio in the main thread
        socketio.run(app, host='0.0.0.0', port=5002, debug=False)
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
        for event in stop_events.values():
            event.set()
        for thread in threads:
            thread.join()
        loop.run_until_complete(disconnect_all_clients())
        loop.close()
# # collect_data_wed_fixtime.py
# from flask import Flask, request, render_template, jsonify
# import json
# import logging
# import threading
# import queue
# from bleak_central_mac import on_notify_call_buffer, vec_myo_ware_shields, vec_myo_ware_clients, main as bleak_main
# import asyncio
# import subprocess
# import datetime
# from flask_socketio import SocketIO, emit
# from collect_data_all import prepare_output_dir, collect_depthandrgb, collect_emg, parse_args, save_depthandrgb_web, save_emg_web
# from config import parse_args, parse_args_sensors, DEPTH_DIR, RGB_DIR, EMG_DIR, DATA_DIR
# from camera_utils import init_camera, set_datamode, set_resolution, set_mapper, set_range
# from DCAM710.API.Vzense_api_710_aiot_modified import *
# from serial.serialutil import SerialException
# from collect_logger import logger
# logging.getLogger('werkzeug').setLevel(logging.INFO)


# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'secret!'
# socketio = SocketIO(app)

# threads = []
# emg_queue = queue.Queue()

# # Flag to indicate if data collection is running
# is_collecting = {"depth_and_rgb": False, "emg": False}
# # Events to signal threads to stop
# stop_events = {"depth_and_rgb": threading.Event(), "emg": threading.Event()}


# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/start_sensors')
# def start_sensors():
#     global threads
#     global camera

#     def list_usb_devices():
#         try:
#             result = subprocess.run(['lsusb'], capture_output=True, text=True, check=True)
#             print(result.stdout)
#         except subprocess.CalledProcessError as e:
#             print(f"Error occurred: {e}")

#     def test_device_access(busnum, devnum):
#         device_path = f"/dev/bus/usb/{busnum:03}/{devnum:03}"
#         try:
#             with open(device_path, 'rb') as device_file:
#                 print(f"Successfully opened {device_path} for reading.")
#                 # read some data to test usb
#                 data = device_file.read(1000)
#                 print(f"Read data: {data}")
#         except PermissionError:
#             print(f"Permission denied: Could not open {device_path}.")
#         except FileNotFoundError:
#             print(f"Device not found: {device_path}.")
#         except Exception as e:
#             print(f"An error occurred: {e}")

#     def start_depth(cfg):
#         # init camera
#         camera = init_camera()
#         logger.info(f"init_camera")

#         # set mode: Output both Depth and RGB frames in 30fps
#         set_datamode(camera, mode='PsDepthAndRGB_30')

#         # set RGB resoultion: (640, 280), (1280, 720), (640, 360)
#         set_resolution(camera, resol='PsRGB_Resolution_640_480')  

#         # mapping RGB image to depth camera space
#         # set_mapper(camera, mapper='r2d') 

#         # set depth range: near, mid, far
#         set_range(camera, range='far')

#         return camera

#     # start depth camera
#     cfg, _ = parse_args_sensors()
#     # camera = start_depth(cfg)
#     # time.sleep(1)

#     # read_try_times = 100
#     # while read_try_times > 0:
#     #     depth_ret, _ = camera.Ps2_ReadNextFrame()
#     #     if depth_ret != 0:
#     #         print("Ps2_ReadNextFrame failed:", depth_ret, read_try_times)
#     #     if depth_ret == 0:
#     #         print("Ps2_ReadNextFrame successful")
#     #         break
#     #     read_try_times -= 1
#     #     time.sleep(1)

#     # if depth_ret != 0:
#     #     print("Depth camera not connected.")
#     #     return jsonify({"status": "Depth No Data Read Out"}), 500

#     asyncio.run(bleak_main())
    
#     return jsonify({"status": "Sensors started successfully"}), 200


# @app.route('/start_visual_emg')
# def start_visual_emg():
#     global on_notify_call_buffer

#     while True:
#         try:
#             for address, data in on_notify_call_buffer.items():
#                 values = data['values']
#                 for entry in values:
#                     timestamp = entry['timestamp']
#                     value = entry['value']
#                     emg_queue.put((timestamp, address, value))
#                     socketio.emit('emg_data', {'timestamp': timestamp, 'mac': address, 'value': value})
#                     logger.info(f"EMG data sent to client: {timestamp}, {address}, {value}")
#         except Exception as e:
#             logger.error(f"Exception occurred while reading from serial port: {e}")
    
#     return jsonify({"status": "Start Visualization"}), 200

# @app.route('/start_collection')
# def start_collection():
#     logger.info(f"start collection")
#     global threads
    
#     subject = request.args.get('subject')
#     action = request.args.get('action')
#     pattern = request.args.get('pattern')
    
#     if not subject or not action or not pattern:
#         return jsonify({"status": "Missing subject or action or Description"}), 400
    
#     cfg, _ = parse_args(subject, action)
#     cfg = prepare_output_dir(cfg)

#     current_sec = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
#     label_path = os.path.join(cfg.label_dir, current_sec + '.txt')

#     # Write the label value to the label_path.txt file
#     with open(label_path, 'w') as f:
#         f.write(pattern)

#     # if not is_collecting["depth_and_rgb"]:
#     #     is_collecting["depth_and_rgb"] = True
#     #     stop_events["depth_and_rgb"].clear()
#     #     thread1 = threading.Thread(target=save_depthandrgb_web, args=(cfg, camera, stop_events["depth_and_rgb"], current_sec))
#     #     thread1.start()
#     #     threads.append(thread1)
#     #     logger.info(f"save_depth_rgb thread collection")
        
#     if not is_collecting["emg"]:
#         is_collecting["emg"] = True
#         stop_events["emg"].clear()
#         thread2 = threading.Thread(target=save_emg_web, args=(cfg, stop_events["emg"], current_sec, emg_queue))
#         thread2.start()
#         threads.append(thread2)
#         logger.info(f"save_emg_web thread collection")
    
#     return jsonify({"status": "Data collection started"})

# def trigger_stop_collection():
#     global is_collecting

#     stop_events["depth_and_rgb"].set()
#     stop_events["emg"].set()

#     for thread in threads:
#         if thread.is_alive():
#             thread.join()

#     is_collecting = {"depth_and_rgb": False, "emg": False}

#     threads.clear()

# @app.route('/stop_collection')
# def stop_collection():
#     global is_collecting

#     stop_events["depth_and_rgb"].set()
#     stop_events["emg"].set()

#     for thread in threads:
#         if thread.is_alive():
#             thread.join()

#     is_collecting = {"depth_and_rgb": False, "emg": False}

#     threads.clear() 
#     return jsonify({"status": "Data collection stopped"})

# @app.route('/countdown')
# def countdown():
#     return render_template('countdown.html')
    
# if __name__ == '__main__':
#     socketio.run(app, host='0.0.0.0', port=5002, debug=False)

# # #collect_data_web.py
# # from flask import Flask, request, render_template, jsonify
# # import json
# # import logging
# # import threading
# # import serial
# # import time
# # from collect_data_all import prepare_output_dir, collect_depthandrgb, collect_emg, parse_args, save_depthandrgb_web, save_emg_web
# # from config import parse_args, parse_args_sensors, DEPTH_DIR, RGB_DIR, EMG_DIR, DATA_DIR
# # from camera_utils import init_camera, set_datamode, set_resolution, set_mapper, set_range
# # from DCAM710.API.Vzense_api_710_aiot_modified import *
# # from serial.serialutil import SerialException
# # import subprocess
# # import datetime
# # from flask_socketio import SocketIO, emit
# # import queue

# # app = Flask(__name__)
# # app.config['SECRET_KEY'] = 'secret!'
# # socketio = SocketIO(app)
# # # Set the log level to WARNING to suppress INFO messages
# # from collect_logger import logger
# # logging.getLogger('werkzeug').setLevel(logging.WARNING)


# # threads = []
# # # emg_data = []
# # emg_queue = queue.Queue()
# # emg_lock = threading.Lock()
# # emg_serial = None

# # # Flag to indicate if data collection is running
# # is_collecting = {"depth_and_rgb": False, "emg": False}
# # # Events to signal threads to stop
# # stop_events = {"depth_and_rgb": threading.Event(), "emg": threading.Event()}


# # @app.route('/')
# # def index():
# #     return render_template('index.html')

# # @app.route('/start_sensors')
# # def start_sensors():
# #     global threads
# #     global camera
# #     global emg_serial
# #     # try:   
# #     def list_usb_devices():
# #         try:
# #             result = subprocess.run(['lsusb'], capture_output=True, text=True, check=True)
# #             print(result.stdout)
# #         except subprocess.CalledProcessError as e:
# #             print(f"Error occurred: {e}")

# #     def test_device_access(busnum, devnum):
# #         device_path = f"/dev/bus/usb/{busnum:03}/{devnum:03}"
# #         try:
# #             with open(device_path, 'rb') as device_file:
# #                 print(f"Successfully opened {device_path} for reading.")
# #                 # read some data to test usb
# #                 data = device_file.read(1000)
# #                 print(f"Read data: {data}")
# #         except PermissionError:
# #             print(f"Permission denied: Could not open {device_path}.")
# #         except FileNotFoundError:
# #             print(f"Device not found: {device_path}.")
# #         except Exception as e:
# #             print(f"An error occurred: {e}")

# #     def start_depth(cfg):
# #         # init camera
# #         camera = init_camera()
# #         logger.info(f"init_camera")

# #         # set mode: Output both Depth and RGB frames in 30fps
# #         set_datamode(camera, mode='PsDepthAndRGB_30')

# #         # set RGB resoultion: (640, 280), (1280, 720), (640, 360)
# #         set_resolution(camera, resol='PsRGB_Resolution_640_480')  

# #         # mapping RGB image to depth camera space
# #         # set_mapper(camera, mapper='r2d') 

# #         # set depth range: near, mid, far
# #         set_range(camera, range='far')

# #         return camera

# #     def start_emg(cfg):
# #         ser_port = cfg.SERIALPORT
# #         baud_rate = cfg.BAUDRATE
# #         def open_serial_port():
# #             try:
# #                 logger.info(f"Open serial port")
# #                 return serial.Serial(ser_port, baud_rate)
# #             except SerialException as e:
# #                 logger.error(f"Error: Could not open serial port {ser_port} - {e}")
# #                 return None

# #         ser = open_serial_port()
# #         return ser
    

# #     # start depth camera
# #     cfg, _ = parse_args_sensors()
# #     # camera = start_depth(cfg)
# #     # time.sleep(1)

# #     # read_try_times = 100
# #     # while read_try_times > 0:
# #     #     depth_ret, _ = camera.Ps2_ReadNextFrame()
# #     #     if depth_ret != 0:
# #     #         print("Ps2_ReadNextFrame failed:", depth_ret, read_try_times)
# #     #     if depth_ret == 0:
# #     #         print("Ps2_ReadNextFrame successful")
# #     #         break
# #     #     read_try_times -= 1
# #     #     time.sleep(1)

# #     # if depth_ret != 0:
# #     #     print("Depth camera not connected.")
# #     #     return jsonify({"status": "Depth No Data Read Out"}), 500
    
# #     # start emg sensors
# #     emg_serial = start_emg(cfg)
    
# #             # if line == 0:
# #             #     return jsonify({"status": "Serial No Data Read Out"}), 500
            
# #     return jsonify({"status": "Sensors started successfully"}), 200


# # @app.route('/start_visual_emg')
# # def start_visual_emg():
# #     global emg_serial
# #     frequency_limiter_count = 0  # 初始化计数器
# #     while True:
# #         try:
# #             if emg_serial.in_waiting > 0:
# #                 line = emg_serial.readline().decode().strip()
# #                 logger.info(f"serial data: {line}")
# #                 try:
# #                     data_dict = json.loads(line)
# #                     for mac, data in data_dict.items():
# #                         values = data['values']
# #                         for entry in values:
# #                             timestamp = entry['timestamp']
# #                             value = entry['value']
# #                             emg_queue.put((timestamp, mac, value))
# #                             frequency_limiter_count += 1  
# #                             # if frequency_limiter_count %  == 0:  
# #                             socketio.emit('emg_data', {'timestamp': timestamp, 'mac': mac, 'value': value})
# #                             logger.debug(f"EMG data sent to client: {timestamp}, {mac}, {value}")

# #                 except json.JSONDecodeError as e:
# #                     logger.error(f"Failed to decode JSON: {e}")
# #                 except KeyError as e:
# #                     logger.error(f"Missing key in JSON data: {e}")
# #         except Exception as e:
# #             logger.error(f"Exception occurred while reading from serial port: {e}")

# #     return jsonify({"status": "Start Visualization"}), 200

# # @app.route('/start_collection')
# # def start_collection():
# #     logger.info(f"start collection")
# #     global threads
# #     global emg_serial
    
# #     subject = request.args.get('subject')
# #     action = request.args.get('action')
# #     pattern = request.args.get('pattern')
    
# #     if not subject or not action or not pattern:
# #         return jsonify({"status": "Missing subject or action or Description"}), 400
    
# #     cfg, _ = parse_args(subject, action)
# #     cfg = prepare_output_dir(cfg)

# #     current_sec = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
# #     label_path = os.path.join(cfg.label_dir, current_sec + '.txt')

# #     # Write the label value to the label_path.txt file
# #     with open(label_path, 'w') as f:
# #         f.write(pattern)

# #     # if not is_collecting["depth_and_rgb"]:
# #     #     is_collecting["depth_and_rgb"] = True
# #     #     stop_events["depth_and_rgb"].clear()
# #     #     thread1 = threading.Thread(target=save_depthandrgb_web, args=(cfg, camera, stop_events["depth_and_rgb"], current_sec))
# #     #     thread1.start()
# #     #     threads.append(thread1)
# #     #     logger.info(f"save_depth_rgb thread collection")
        
# #     if not is_collecting["emg"]:
# #         is_collecting["emg"] = True
# #         stop_events["emg"].clear()
# #         thread2 = threading.Thread(target=save_emg_web, args=(cfg, stop_events["emg"], current_sec, emg_queue))
# #         thread2.start()
# #         threads.append(thread2)
# #         logger.info(f"save_emg_web thread collection")
    
# #      # Setup a timer to stop collection after 3 seconds
# #     # timer = threading.Timer(3.0, trigger_stop_collection)
# #     # timer.start()

# #     return jsonify({"status": "Data collection started"})

# # def trigger_stop_collection():
# #     global is_collecting

# #     stop_events["depth_and_rgb"].set()
# #     stop_events["emg"].set()

# #     for thread in threads:
# #         if thread.is_alive():
# #             thread.join()

# #     is_collecting = {"depth_and_rgb": False, "emg": False}

# #     threads.clear()

# # @app.route('/stop_collection')
# # def stop_collection():
# #     global is_collecting

# #     stop_events["depth_and_rgb"].set()
# #     stop_events["emg"].set()

# #     for thread in threads:
# #         if thread.is_alive():
# #             thread.join()

# #     is_collecting = {"depth_and_rgb": False, "emg": False}

# #     threads.clear() 
# #     return jsonify({"status": "Data collection stopped"})

# # @app.route('/countdown')
# # def countdown():
# #     return render_template('countdown.html')
    
# # if __name__ == '__main__':
# #     socketio.run(app, host='0.0.0.0', port=5002, debug=False)
#collect_data_web.py
from flask import Flask, request, render_template, jsonify
import json
import logging
import threading
import serial
import time
from collect_data_all import prepare_output_dir, collect_depthandrgb, collect_emg, parse_args, save_depthandrgb_web, save_emg_web
from config import parse_args, parse_args_sensors, DEPTH_DIR, RGB_DIR, EMG_DIR, DATA_DIR
from camera_utils import init_camera, set_datamode, set_resolution, set_mapper, set_range
from DCAM710.API.Vzense_api_710_aiot_modified import *
from serial.serialutil import SerialException
import subprocess
import datetime
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
# Set the log level to WARNING to suppress INFO messages
logging.getLogger('werkzeug').setLevel(logging.WARNING)


threads = []
emg_data = []
emg_lock = threading.Lock()
emg_serial = None

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
    global emg_serial
    # try:   
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

        # set mode: Output both Depth and RGB frames in 30fps
        set_datamode(camera, mode='PsDepthAndRGB_30')

        # set RGB resoultion: (640, 280), (1280, 720), (640, 360)
        set_resolution(camera, resol='PsRGB_Resolution_640_480')  

        # mapping RGB image to depth camera space
        # set_mapper(camera, mapper='r2d') 

        # set depth range: near, mid, far
        set_range(camera, range='far')

        return camera

    def start_emg(cfg):
        ser_port = cfg.SERIALPORT
        baud_rate = cfg.BAUDRATE
        def open_serial_port():
            try:
                return serial.Serial(ser_port, baud_rate)
            except SerialException as e:
                print(f"Error: Could not open serial port {ser_port} - {e}")
                return None

        ser = open_serial_port()
        return ser
    

    # start depth camera
    cfg, _ = parse_args_sensors()
    # camera = start_depth(cfg)
    # time.sleep(1)

    # read_try_times = 100
    # while read_try_times > 0:
    #     depth_ret, _ = camera.Ps2_ReadNextFrame()
    #     if depth_ret != 0:
    #         print("Ps2_ReadNextFrame failed:", depth_ret, read_try_times)
    #     if depth_ret == 0:
    #         print("Ps2_ReadNextFrame successful")
    #         break
    #     read_try_times -= 1
    #     time.sleep(1)

    # if depth_ret != 0:
    #     print("Depth camera not connected.")
    #     return jsonify({"status": "Depth No Data Read Out"}), 500
    
    # start emg sensors
    emg_serial = start_emg(cfg)
    
            # if line == 0:
            #     return jsonify({"status": "Serial No Data Read Out"}), 500
            
    return jsonify({"status": "Sensors started successfully"}), 200


@app.route('/start_visual_emg')
def start_visual_emg():
    global emg_serial
    stop_events["emg"].set()
    while stop_events["emg"].is_set():
        if emg_serial.in_waiting > 0:
            line = emg_serial.readline().decode().strip()
            print("auto read serial data: ", line)
            try:
                data_list = json.loads(line)
                for data in data_list:
                    timestamp = data['timestamp']
                    mac = data['mac']
                    value = data['value']
                    emg_data.append((timestamp, mac, value))
                    socketio.emit('emg_data', {'timestamp': timestamp, 'mac': mac, 'value': value})
                    
                if len(emg_data) > 1500:  # Keep only the last 1500 EMG data points
                    emg_data.pop(0)
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
            except KeyError as e:
                print(f"Missing key in JSON data: {e}")

    return jsonify({"status": "Start Visualization"}), 200


@app.route('/start_collection')
def start_collection():
    global threads
    global emg_serial
    
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
        
    if not is_collecting["emg"]:
        is_collecting["emg"] = True
        stop_events["emg"].clear()
        thread2 = threading.Thread(target=save_emg_web, args=(cfg, emg_serial, stop_events["emg"], current_sec, emg_data))
        thread2.start()
        threads.append(thread2)

    return jsonify({"status": "Data collection started"})

@app.route('/stop_collection')
def stop_collection():
    global is_collecting

    # Signal the threads to stop
    stop_events["depth_and_rgb"].set()
    stop_events["emg"].set()

    # Join the threads to ensure they have stopped
    for thread in threads:
        if thread.is_alive():
            thread.join()

    is_collecting = {"depth_and_rgb": False, "emg": False}
    threads.clear()   
    return jsonify({"status": "Data collection stopped"})

# former code for front end fetch data from backend, now using websocket
# @app.route('/latest_emg_data')
# def latest_emg_data():
#     if emg_data:
#         latest_data = emg_data[-1]
#         return jsonify({"timestamp": latest_data[0], "mac": latest_data[1], "value": latest_data[2]})
#     else:
#         return jsonify({}), 200
    
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5002, debug=False)

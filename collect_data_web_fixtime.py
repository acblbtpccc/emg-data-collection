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
import signal
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

    def start_depth(cfg):
        # init camera
        camera = init_camera()
        logger.info(f"init_camera")

        # set mode: Output both Depth and RGB frames in 30fps
        set_datamode(camera, mode='PsDepthAndRGB_30')

        # set RGB resoultion: (640, 280), (1280, 720), (640, 360)
        set_resolution(camera, resol='PsRGB_Resolution_640_480')  

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
    
    current_sec = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_path = f"./{DATA_DIR}/{subject}/{action}"
    sample_folder_name = f'S{subject}-A{action}-P{pattern}-{current_sec}'
    sample_folder_path = os.path.join(base_path, sample_folder_name)
    os.makedirs(sample_folder_path, exist_ok=True)

    cfg, _ = parse_args(subject, action)
    # cfg = prepare_output_dir(cfg)
    label_path = os.path.join(sample_folder_path, sample_folder_name + '-text.txt')

    # Write the label value to the label_path.txt file
    with open(label_path, 'w') as f:
        f.write(pattern)

    if not is_collecting["depth_and_rgb"]:
        is_collecting["depth_and_rgb"] = True
        stop_events["depth_and_rgb"].clear()
        thread1 = threading.Thread(target=save_depthandrgb_web, args=(cfg, camera, stop_events["depth_and_rgb"], sample_folder_path, sample_folder_name))
        thread1.start()
        threads.append(thread1)
        logger.info(f"save_depth_rgb thread collection")
        
    if not is_collecting["emg"]:
        is_collecting["emg"] = True
        stop_events["emg"].clear()
        thread2 = threading.Thread(target=save_emg_web, args=(cfg, stop_events["emg"], sample_folder_path, sample_folder_name, emg_queue))
        thread2.start()
        threads.append(thread2)
        logger.info(f"save_emg_web thread collection")
    
    return jsonify({"status": "Data collection started"})

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

def disconnect_all_clients():
    print("Attempting to disconnect all clients...")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        tasks = [loop.create_task(client.disconnect()) for client in bleak_central_mac.vec_myo_ware_clients]
        loop.run_until_complete(asyncio.gather(*tasks))
        print("All Bluetooth clients have been disconnected.")
    except Exception as e:
        print(f"Failed to disconnect clients: {e}")


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    disconnect_all_clients()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)
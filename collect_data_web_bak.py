from flask import Flask, render_template, jsonify
import threading
import time
from collect_data_all import prepare_output_dir, collect_depthandrgb, collect_emg, parse_args

app = Flask(__name__)
threads = []
emg_data = []
emg_lock = threading.Lock()

# Flag to indicate if data collection is running
is_collecting = {"depth_and_rgb": False, "emg": False}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_collection')
def start_collection():
    global threads
    cfg, _ = parse_args()
    cfg = prepare_output_dir(cfg)

    if not is_collecting["depth_and_rgb"]:
        thread1 = threading.Thread(target=collect_depthandrgb, args=(cfg,))
        thread1.start()
        threads.append(thread1)
        is_collecting["depth_and_rgb"] = True

    if not is_collecting["emg"]:
        thread2 = threading.Thread(target=collect_emg, args=(cfg, emg_data, emg_lock))
        thread2.start()
        threads.append(thread2)
        is_collecting["emg"] = True

    return jsonify({"status": "Data collection started"})

@app.route('/stop_collection')
def stop_collection():
    global is_collecting
    # Normally, you would have a way to signal the threads to stop
    # Here, we just join them (this will hang if the threads are in an infinite loop)
    for thread in threads:
        if thread.is_alive():
            thread.join()

    is_collecting = {"depth_and_rgb": False, "emg": False}
    return jsonify({"status": "Data collection stopped"})

@app.route('/latest_emg_data')
def latest_emg_data():
    with emg_lock:
        # Return the last 10 EMG data points, formatted as a list of tuples
        print("[Debug] emg_data:", emg_data)
        return jsonify([(item[0], item[1]) for item in emg_data[-50:]])
    
# @app.route('/latest_emg_data')
# def latest_emg_data():
#     with emg_lock:
#         # Return the last 10 EMG data points, formatted as a list of tuples
#         print("[Debug] emg_data:", emg_data)
#         return jsonify([(item['timestamp'], f"{item['emg1']},{item['emg2']}") for item in emg_data[-10:]])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# 2024-0528-12:35
# from flask import Flask, render_template, jsonify
# import threading
# import time
# from collect_data_all import prepare_output_dir, collect_depthandrgb, collect_emg, parse_args

# app = Flask(__name__)
# threads = []
# emg_data = []
# emg_lock = threading.Lock()

# # Flag to indicate if data collection is running
# is_collecting = {"depth_and_rgb": False, "emg": False}

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/start_collection')
# def start_collection():
#     global threads
#     cfg, _ = parse_args()
#     cfg = prepare_output_dir(cfg)

#     if not is_collecting["depth_and_rgb"]:
#         thread1 = threading.Thread(target=collect_depthandrgb, args=(cfg,))
#         thread1.start()
#         threads.append(thread1)
#         is_collecting["depth_and_rgb"] = True

#     if not is_collecting["emg"]:
#         thread2 = threading.Thread(target=collect_emg, args=(cfg, emg_data, emg_lock))
#         thread2.start()
#         threads.append(thread2)
#         is_collecting["emg"] = True

#     return jsonify({"status": "Data collection started"})

# @app.route('/stop_collection')
# def stop_collection():
#     global is_collecting
#     # Normally, you would have a way to signal the threads to stop
#     # Here, we just join them (this will hang if the threads are in an infinite loop)
#     for thread in threads:
#         if thread.is_alive():
#             thread.join()

#     is_collecting = {"depth_and_rgb": False, "emg": False}
#     return jsonify({"status": "Data collection stopped"})

# @app.route('/latest_emg_data')
# def latest_emg_data():
#     with emg_lock:
#         print("emg_data:", emg_data)
#         return jsonify(emg_data[-10:])  # Return the last 10 EMG data points

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)

# # server.py

# from flask import Flask, render_template, jsonify
# import threading
# import time
# from collect_data_all import prepare_output_dir, collect_depthandrgb, collect_emg, parse_args

# app = Flask(__name__)
# threads = []

# # Flag to indicate if data collection is running
# is_collecting = {"depth_and_rgb": False, "emg": False}

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/start_collection')
# def start_collection():
#     global threads
#     cfg, cfg_file = parse_args()
#     cfg = prepare_output_dir(cfg)

#     if not is_collecting["depth_and_rgb"]:
#         thread1 = threading.Thread(target=collect_depthandrgb, args=(cfg,))
#         thread1.startw()
#         threads.append(thread1)
#         is_collecting["depth_and_rgb"] = True

#     if not is_collecting["emg"]:
#         thread2 = threading.Thread(target=collect_emg, args=(cfg,))
#         thread2.start()
#         threads.append(thread2)
#         is_collecting["emg"] = True

#     return jsonify({"status": "Data collection started"})

# @app.route('/stop_collection')
# def stop_collection():
#     global is_collecting
#     for thread in threads:
#         if thread.is_alive():
#             # Normally, you would have a way to signal the threads to stop
#             # Here, we just join them (this will hang if the threads are in an infinite loop)
#             thread.join()

#     is_collecting = {"depth_and_rgb": False, "emg": False}
#     return jsonify({"status": "Data collection stopped"})

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)
import json
import asyncio
import websockets
import serial
import csv
import datetime, time
import os
from DCAM710.API.Vzense_api_710_aiot_modified import *
import cv2
import numpy as np
import threading
from config import parse_args, DEPTH_DIR, RGB_DIR, EMG_DIR, DATA_DIR, LABEL_DIR
from camera_utils import init_camera, set_datamode, set_resolution, set_mapper, set_range
from serial.serialutil import SerialException
from collect_logger import logger
import queue

def prepare_output_dir(cfg):
    base_path = f"./{DATA_DIR}/{cfg.SUBJECT}/{cfg.ACTION}"
    cfg.depth_dir = os.path.join(base_path, DEPTH_DIR)
    os.makedirs(cfg.depth_dir, exist_ok=True)
    cfg.rgb_dir = os.path.join(base_path, RGB_DIR)
    os.makedirs(cfg.rgb_dir, exist_ok=True)
    cfg.emg_dir = os.path.join(base_path, EMG_DIR)
    os.makedirs(cfg.emg_dir, exist_ok=True)
    cfg.label_dir = os.path.join(base_path, LABEL_DIR)
    os.makedirs(cfg.label_dir, exist_ok=True)
    return cfg

def save_depthandrgb_web(cfg, camera, stop_event, current_sec):
    print("stop_event: ", stop_event)
    _, depthrange = camera.Ps2_GetDepthRange()
    _, depth_max, value_min, value_max = camera.Ps2_GetMeasuringRange(PsDepthRange(depthrange.value))
    print("depth_max, value_min, value_max: ", depth_max, value_min, value_max)

    headers = ['timestamp', 'frame_id']
    depth_video_path = ''
    num_recorded_frame = 0

    # current_sec = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # init path of video file and frame info csv
    depth_video_path = os.path.join(cfg.depth_dir, current_sec + '.mp4')
    rgb_video_path = os.path.join(cfg.rgb_dir, current_sec + '.mp4')
    frame_info_path = os.path.join(cfg.rgb_dir, current_sec + '.csv')
    print("New video saving path: {:s}".format(depth_video_path))

    # init video writer
    vout_d = cv2.VideoWriter()
    vout_d.open(depth_video_path, cv2.VideoWriter_fourcc(*'mp4v'), cfg.CMAERA.FPS, (cfg.CMAERA.HEIGHT, cfg.CMAERA.WIDTH), isColor=False)

    vout_rgb = cv2.VideoWriter()
    vout_rgb.open(rgb_video_path, cv2.VideoWriter_fourcc(*'mp4v'), cfg.CMAERA.FPS, (cfg.CMAERA.HEIGHT, cfg.CMAERA.WIDTH), isColor=True)

    # init csv writer
    with open(frame_info_path, "a") as frame_info:
        f_csv = csv.writer(frame_info)
        f_csv.writerow(headers)
        
    try:
        while not stop_event.is_set():
            # while True:
            ret, frameready = camera.Ps2_ReadNextFrame()
            if  ret != 0:
                print("Ps2_ReadNextFrame failed:",ret)
                time.sleep(1)

            if frameready.depth:
                ret, depthframe = camera.Ps2_GetFrame(PsFrameType.PsDepthFrame)     # (480, 640)
                if ret == 0:
                    frametmp = np.ctypeslib.as_array(depthframe.pFrameData, (1, depthframe.width * depthframe.height * 2))
                    frametmp.dtype = np.uint16
                    frametmp.shape = (depthframe.height, depthframe.width)
                    img = np.int32(frametmp)
                    img = img*255 / depth_max
                    img = np.clip(img, 0, 255)
                    img = np.uint8(img)
                    img = numpy.rot90(img, k=-1)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")
                    vout_d.write(img)

                    # log frame info to frame_info_path
                    num_recorded_frame += 1
                    with open(frame_info_path, "a") as frame_info:
                        f_csv = csv.writer(frame_info)
                        f_csv.writerow([timestamp, num_recorded_frame])

            if frameready.rgb:
                ret, rgbframe = camera.Ps2_GetFrame(PsFrameType.PsRGBFrame)
                if  ret == 0:
                    frametmp = numpy.ctypeslib.as_array(rgbframe.pFrameData, (rgbframe.height, rgbframe.width, 3))
                    frametmp.dtype = numpy.uint8
                    rotated_frame = numpy.rot90(frametmp, k=-1)
                    vout_rgb.write(rotated_frame)
                    
    finally:
        print("video {:s} has been writen!".format(depth_video_path))
        vout_d.release()
        vout_rgb.release()

 
def save_emg_web(cfg, stop_event, current_sec, emg_queue):
    # MAC address to muscle mapping
    mac_to_info = {
    'E4:65:B8:14:BA:9A': ('01', 'L_Biceps'),
    'D4:8A:FC:C5:8B:B2': ('02', 'R_Biceps'),
    'E4:65:B8:14:79:5E': ('03', 'L_Deltoid'),
    'D4:8A:FC:C5:A5:CA': ('04', 'R_Deltoid'),
    'D4:8A:FC:C4:B0:C6': ('05', 'L_Latiss'),
    'D4:8A:FC:C5:AB:32': ('06', 'R_Latiss'),
    'D4:8A:FC:C5:9E:12': ('07', 'L_Trapezius'),
    'D4:8A:FC:C5:06:7E': ('08', 'R_Trapezius')
}
    logger.debug(f"stop_event: {stop_event}")

    emg_path = os.path.join(cfg.emg_dir, current_sec + '.csv')
    header = ['timestamp', 'EMGID', 'mac_address', 'muscle', 'emg_value']

    with open(emg_path, 'a', newline='') as emg_data:
        writer = csv.writer(emg_data)
        writer.writerow(header)

    try:
        batch_size = 150
        buffer = []

        while not stop_event.is_set():
            logger.debug(f"stop_event: {stop_event}")
            
            try:
                timestamp, mac, value = emg_queue.get(timeout=1)
                emgid, muscle = mac_to_info.get(mac, ("Unknown", "Unknown"))
                buffer.append([timestamp, emgid, mac, muscle, value])
                logger.debug(f"{timestamp}: {emgid}: {mac}: {muscle}: {value}")
                
                # 当缓冲区达到批量大小时写入文件
                if len(buffer) >= batch_size:
                    with open(emg_path, 'a', newline='') as emg_data:
                        writer = csv.writer(emg_data)
                        writer.writerows(buffer)
                    buffer.clear()

            except queue.Empty:
                continue
            except KeyError as e:
                logger.error(f"Missing key in shared EMG data: {e}")
                continue
            logger.debug("save_emg_web one loop finished")

        # 在退出之前将剩余的数据写入文件
        if buffer:
            with open(emg_path, 'a', newline='') as emg_data:
                writer = csv.writer(emg_data)
                writer.writerows(buffer)

    except Exception as e:
        logger.error(f"An error occurred while saving EMG data: {e}")
    finally:
        logger.error(f"EMGs {emg_path} has been written!")


def collect_depthandrgb(cfg, camera):
    _, depthrange = camera.Ps2_GetDepthRange()
    _, depth_max, value_min, value_max = camera.Ps2_GetMeasuringRange(PsDepthRange(depthrange.value))
    print("depth_max, value_min, value_max: ", depth_max, value_min, value_max)


    headers = ['timestamp', 'frame_id']
    depth_video_path = ''
    num_recorded_frame = 0

    # start
    try:
        while True:
            # if no save path of current video is given
            if not depth_video_path:
                current_sec = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

                 # init path of video file and frame info csv
                depth_video_path = os.path.join(cfg.depth_dir, current_sec + '.mp4')
                rgb_video_path = os.path.join(cfg.rgb_dir, current_sec + '.mp4')
                frame_info_path = os.path.join(cfg.rgb_dir, current_sec + '.csv')
                print("New video saving path: {:s}".format(depth_video_path))

                # init video writer
                vout_d = cv2.VideoWriter()
                vout_d.open(depth_video_path, cv2.VideoWriter_fourcc(*'mp4v'), cfg.CMAERA.FPS, (cfg.CMAERA.WIDTH, cfg.CMAERA.HEIGHT), isColor=False)

                vout_rgb = cv2.VideoWriter()
                vout_rgb.open(rgb_video_path, cv2.VideoWriter_fourcc(*'mp4v'), cfg.CMAERA.FPS, (cfg.CMAERA.WIDTH, cfg.CMAERA.HEIGHT), isColor=True)

                # init csv writer
                with open(frame_info_path, "a") as frame_info:
                    f_csv = csv.writer(frame_info)
                    f_csv.writerow(headers)
                start_time = time.time()
            
            # if video writer is initialized, just write video file
            else:
                ret, frameready = camera.Ps2_ReadNextFrame()
                if  ret != 0:
                    print("Ps2_ReadNextFrame failed:",ret)
                    time.sleep(1)
                    continue 

                if frameready.mappedDepth:
                    ret, depthframe = camera.Ps2_GetFrame(PsFrameType.PsMappedDepthFrame)     # (480, 640)
                    if ret == 0:
                        frametmp = np.ctypeslib.as_array(depthframe.pFrameData, (1, depthframe.width * depthframe.height * 2))
                        frametmp.dtype = np.uint16
                        frametmp.shape = (depthframe.height, depthframe.width)
                        img = np.int32(frametmp)
                        img = img*255 / depth_max
                        img = np.clip(img, 0, 255)
                        img = np.uint8(img)
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")
                        vout_d.write(img)

                        # log frame info to frame_info_path
                        num_recorded_frame += 1
                        with open(frame_info_path, "a") as frame_info:
                            f_csv = csv.writer(frame_info)
                            f_csv.writerow([timestamp, num_recorded_frame])

                if frameready.rgb:
                    ret, rgbframe = camera.Ps2_GetFrame(PsFrameType.PsRGBFrame)
                    if  ret == 0:
                        frametmp = numpy.ctypeslib.as_array(rgbframe.pFrameData, (1, rgbframe.width * rgbframe.height * 3))
                        frametmp.dtype = numpy.uint8
                        frametmp.shape = (rgbframe.height, rgbframe.width, 3)
                        vout_rgb.write(frametmp)

                # if having been capturing for 1 mins, stop and start a new round
                if time.time() - start_time >= 60:
                    num_recorded_frame = 0
                    print("video {:s} has been writen!".format(depth_video_path))

                    depth_video_path = ''
                    vout_d.release()
                    vout_rgb.release()

    except Exception as e:
        print('Exception: ', e)

    ret = camera.Ps2_StopStream()       
    if  ret == 0:
        print("stop stream successful")
    else:
        print('Ps2_StopStream failed: ' + str(ret))  

    ret = camera.Ps2_CloseDevice()     
    if  ret == 0:
        print("close device successful")
    else:
        print('Ps2_CloseDevice failed: ' + str(ret)) 

def collect_emg(cfg, shared_emg_data, lock):
    ser = serial.Serial(cfg.SERIALPORT, cfg.BAUDRATE)  # Windows Serial port
    # ser = serial.Serial('/dev/ttyACM0', 115200)  # Linux/Mac Serial port
    ser_port = cfg.SERIALPORT
    baud_rate = cfg.BAUDRATE
    emg_path = ''
    header = ['timestamp', 'EMG']
    def open_serial_port():
        try:
            return serial.Serial(ser_port, baud_rate)
        except SerialException as e:
            print(f"Error: Could not open serial port {ser_port} - {e}")
            return None

    ser = open_serial_port()
    if ser is None:
        return
    
    try:
        while True:
            if not emg_path:
                current_sec = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                emg_path = os.path.join(cfg.emg_dir, current_sec + '.csv')
                with open(emg_path, 'a') as emg_data:
                    writer = csv.writer(emg_data)
                    writer.writerow(header)
                start_time = time.time()
                
            else:
                try:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode().strip()
                        # print("[Debug] line:", line)
                        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S.%f')
                        with open(emg_path, "a") as emg_data:
                            writer = csv.writer(emg_data)
                            writer.writerow([timestamp, line])
                        with lock:
                            shared_emg_data.append((timestamp, line))
                            # print("[Debug] shared_emg_data:", shared_emg_data)
                            if len(shared_emg_data) > 50:  # Keep only the last 50 EMG data points
                                shared_emg_data.pop(0)
                        # Push data to WebSocket clients
                        # await websocket.send(f"{timestamp},{line}")

                except SerialException as e:
                    print(f"Serial exception: {e}")
                    ser.close()
                    print("Attempting to reconnect...")
                    ser = open_serial_port()
                    if ser is None:
                        print("Reconnection failed. Exiting.")
                        break

                # if having been capturing for 1 mins, stop and start a new round
                if time.time() - start_time >= 60:
                    print("EMGs {:s} has been writen!".format(emg_path))
                    emg_path = ''

    except KeyboardInterrupt:
        print("Stopped by User")
    finally:
        if ser and ser.is_open:
            ser.close()
        print("Serial Connection Closed")


def main(cfg):
    thread1 = threading.Thread(target=collect_depthandrgb, args=(cfg,))
    thread2 = threading.Thread(target=collect_emg, args=(cfg,))

    thread1.start()
    thread2.start()

    try:
        thread1.join()
        thread2.join()
    except KeyboardInterrupt:
        print("Received interrupt, stopping threads.")
        stop_threads = True
        thread1.join()
        thread2.join()
    finally:
        print("All data collected")



if __name__ == '__main__':
    cfg, cfg_file = parse_args('a', 'b')
    cfg = prepare_output_dir(cfg)
    main(cfg)

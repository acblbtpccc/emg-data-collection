from DCAM710.API.Vzense_api_710_aiot_modified import *
import datetime, time

def init_camera():
    camera = VzenseTofCam()
    if camera is None:
        print("Failed to create VzenseTofCam instance")
    print("camera instance:", camera)

    camera_count = camera.Ps2_GetDeviceCount()
    print("camera_count:", camera_count)
    retry_count = 100
    while camera_count==0 and retry_count > 0:
        retry_count = retry_count-1
        camera_count = camera.Ps2_GetDeviceCount()
        time.sleep(1)
        print("scaning......   ", retry_count)

    device_info = PsDeviceInfo()
    if camera_count > 1:
        ret, device_infolist = camera.Ps2_GetDeviceListInfo(camera_count)
        if ret==0:
            device_info = device_infolist[0]
            for info in device_infolist:
                print('cam uri:  ' + str(info.uri))
        else:
            print(' failed:' + ret)
            exit()
    elif camera_count == 1:
        ret,device_info = camera.Ps2_GetDeviceInfo()
        if ret==0:
            print('cam uri:' + str(device_info.uri))
        else:
            print(' failed:' + ret)
            exit()
    else:
        print("there are no camera found")
        exit()

    rst = camera.Ps2_OpenDevice(device_info.uri)
    if  rst == 0:
        print("open device successful")
    else:
        print('Ps2_OpenDevice failed: ' + str(rst))
    
    ret = camera.Ps2_StartStream()
    if  ret == 0:
        print("start stream successful")
    else:
        print("Ps2_StartStream failed:", ret)

    return camera


def set_datamode(camera, mode='PsDepthAndRGB_30'):
    if mode=='PsDepthAndRGB_30':
        ret = camera.Ps2_SetDataMode(PsDataMode.PsDepthAndRGB_30)
    if  ret != 0:  
        print("Ps2_SetDataMode failed:", ret, mode)
    else:
        print("Ps2_SetDataMode successful:", ret, mode)
    return ret

def set_resolution(camera, resol='PsRGB_Resolution_640_480'):
    if resol=='PsRGB_Resolution_640_480':
        ret = camera.Ps2_SetRGBResolution(PsResolution.PsRGB_Resolution_640_480)
    if  ret != 0:  
        print("Ps2_SetRGBResolution failed:", ret, resol)
    else:
        print("Ps2_SetRGBResolution successful:", ret, resol)
    return ret

def set_mapper(camera, mapper='r2d'):
    if mapper=='r2d':
        ret = camera.Ps2_SetMapperEnabledRGBToDepth(c_bool(True))
    elif mapper=='d2r':
        ret = camera.GetMapperEnabledDepthToRGB(c_bool(True))
    if  ret == 0:
        print("set DepthToRGB")
    else:
        print("Ps2_SetMapperEnabledDepthToRGB failed:", ret, mapper) 
    return ret

def set_range(camera, range='mid'):
    if range == 'far':
        ret = camera.Ps2_SetDepthRange(PsDepthRange.PsFarRange)
    elif range == 'mid':
        ret = camera.Ps2_SetDepthRange(PsDepthRange.PsMidRange)
    elif range == 'near':
        ret = camera.Ps2_SetDepthRange(PsDepthRange.PsNearRange)

    if  ret != 0:
        print("Ps2_SetDepthRange failed:", ret, range)
    else:
        print("Ps2_SetMapperEnabledDepthToRGB successful:", ret, range) 
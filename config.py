import argparse
from yacs.config import CfgNode as CN

# CONSTANTS
# You may modify them at will
DEPTH_DIR = 'depth'
RGB_DIR = 'rgb'
EMG_DIR = 'emg'
LABEL_DIR = 'text'
DATA_DIR = 'data'

# Configuration variables
cfg = CN()
cfg.DEPTH = True
cfg.RGB = True
cfg.EMG = True
cfg.FREQUENCY= 10  
cfg.SUBJECT = 'TestP1'
cfg.ACTION = 'TestA1'
cfg.SERIALPORT = 'COM9'
cfg.BAUDRATE = '115200'

cfg.CMAERA = CN()
cfg.CMAERA.FPS = 30
cfg.CMAERA.WIDTH = 640
cfg.CMAERA.HEIGHT = 480

def get_cfg_defaults():
    """Get a yacs CfgNode object with default values for my_project."""
    # Return a clone so that the defaults will not be altered
    # This is for the "local variable" use pattern
    return cfg.clone()


def update_cfg(cfg_file):
    cfg = get_cfg_defaults()
    cfg.merge_from_file(cfg_file)
    return cfg.clone()

def parse_args_sensors():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, help='cfg file path')

    args = parser.parse_args()
    print(args, end='\n\n')

    cfg_file = args.cfg
    if args.cfg is not None:
        cfg = update_cfg(args.cfg)
    else:
        cfg = get_cfg_defaults()
    
    return cfg, cfg_file


def parse_args(subject, action):
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, help='cfg file path')

    args = parser.parse_args()
    print(args, end='\n\n')

    cfg_file = args.cfg
    if args.cfg is not None:
        cfg = update_cfg(args.cfg)
    else:
        cfg = get_cfg_defaults()
        # Update subject and action if provided
    if subject:
        cfg.SUBJECT = subject
        print("cfg.SUBJECT: ", cfg.SUBJECT)
    if action:
        cfg.ACTION = action
        print("cfg.ACTION: ", cfg.ACTION)

    return cfg, cfg_file

import os
import scipy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shutil
import matplotlib.colors as mcolors


muscles = ['L_Biceps', 'R_Biceps', 'L_Deltoid', 'R_Deltoid', 'L_Latiss', 'R_Latiss', 'L_Trapezius', 'R_Trapezius']
action_order = ['1', '2', '3', '4', '5', '6', '7']
patterns = [f'P{i}' for i in range(12)]  # Generates list ['P0', 'P1', ..., 'P11']

def calculate_rms(values):
    return np.sqrt(np.mean(np.square(values)))

def extract_patterns(sample_name):
    """ Extracts patterns like P0 or P3,11 from the sample name """
    parts = sample_name.split('-')
    for part in parts:
        if 'P' in part:
            return part
        
def standardize_pattern(patterns):
    """ Ensure all patterns are in the format 'Px' """
    standardized_patterns = []
    for pat in patterns:
        if not pat.startswith('P'):
            standardized_patterns.append(f'P{pat}')
        else:
            standardized_patterns.append(pat)
    return standardized_patterns

def plot_emgs(base_path):
    # action_rms = {action: {muscle: [] for muscle in muscles} for action in action_order}
    # muscle_action_rms = {muscle: {action: [] for action in action_order} for muscle in muscles}
    data_container = {action: {pattern: {muscle: [] for muscle in muscles} for pattern in patterns} for action in action_order}

    for action in os.listdir(base_path):
        # pattern_rms = {pattern: {muscle: [] for muscle in muscles} for pattern in patterns}
        action_path = os.path.join(base_path, action)
        for sample in os.listdir(action_path):
            sample_path = os.path.join(action_path, sample)
            pattern = extract_patterns(sample)
            individual_patterns = pattern.split(',')
            individual_patterns = standardize_pattern(individual_patterns)
            # if 'P0' in sample:  # Check if the directory contains 'P0'
            emg_path = os.path.join(sample_path, sample+'-emg.csv')
            data = pd.read_csv(emg_path, parse_dates=['timestamp'])
            for muscle in muscles:
                muscle_data = data[data['muscle'] == muscle]
                rms = calculate_rms(muscle_data['emg_value'])
                for p in individual_patterns:
                    data_container[action][p][muscle].append(rms)
    final_data = {}
    for action in data_container:
        final_data[action] = {}
        for pattern in data_container[action]:
            final_data[action][pattern] = {}
            for muscle in data_container[action][pattern]:
                final_data[action][pattern][muscle] = np.array(data_container[action][pattern][muscle])
    # selected_action = action_order[0]  # 选择第二个动作

    for selected_action in action_order:
        for selected_muscle in muscles:
            patterns_data = {pattern: final_data[selected_action][pattern][selected_muscle] for pattern in final_data[selected_action]}
            variances = {pattern: np.var(data) for pattern, data in patterns_data.items() if len(data) > 0}
            sample_var = np.mean(list(variances.values()))
            all_data = np.concatenate([data for data in patterns_data.values() if len(data) > 0])
            total_variance = np.var(all_data)
            f_stat = (total_variance-sample_var)/sample_var
            print(f"{selected_action:2} {selected_muscle:>16}: {f_stat:5.2f} {1 - scipy.stats.f.cdf(f_stat, len(variances) - 1, sum(len(x) for x in patterns_data.values()) - len(variances)):5.3f}")


    # 计算方差比值
    # variance_ratios = {pattern: var / total_variance for pattern, var in variances.items()}

    # 输出方差比值
    # for pattern, ratio in variance_ratios.items():
    #     print(f"Pattern {pattern}: Variance Ratio = {ratio:.4f}")

        #             action_rms[int(action)][muscle].append(rms)
        #             muscle_action_rms[muscle][int(action)].append(rms)
        #             for pat in individual_patterns:
        #                 pattern_rms[pat][muscle].append(rms)

    
        # plt.figure(figsize=(10, 6))
        # for muscle in muscles:
        #     x = []
        #     y = []
        #     for pattern in patterns:
        #         x.extend([pattern] * len(pattern_rms[pattern][muscle]))
        #         y.extend(pattern_rms[pattern][muscle])
        #     plt.scatter(x, y, label=muscle)
        # plt.xlabel('Pattern')
        # plt.ylabel('RMS EMG Value')
        # plt.title(f'Action {action} EMG Data')
        # plt.legend()
        # plt.grid(True)
        # plt.savefig(f'figs/{action}-rms_emg_muscle.png')
        # plt.close()

    # for action, muscles_data in action_rms.items():
    #     plt.figure(figsize=(12, 6))
    #     for idx, (muscle, rms_values) in enumerate(muscles_data.items()):
    #         x_values = [idx] * len(rms_values)  # Create x values for each muscle
    #         plt.scatter(x_values, rms_values, label=muscle)

    #     plt.xticks(range(len(muscles)), muscles, rotation=45)
    #     plt.xlabel('Muscle')
    #     plt.ylabel('RMS EMG Value')
    #     plt.title(f'Action {action} - RMS EMG Values per Sample')
    #     plt.legend()
    #     plt.tight_layout()
        
    #     plt.savefig(f'figs/{action}-rms_emg_muscle.png')
    #     plt.close()
    
    # for muscle, actions_data in muscle_action_rms.items():
    #     plt.figure(figsize=(10, 5))
    #     for action, rms_values in actions_data.items():
    #         x_values = [action] * len(rms_values)  # Create x values for each action
    #         plt.scatter(x_values, rms_values, label=f'Action {action}')

    #     plt.xticks(action_order)
    #     plt.xlabel('Action')
    #     plt.ylabel('RMS EMG Value')
    #     plt.title(f'RMS EMG Values for {muscle}')
    #     plt.legend()
    #     plt.tight_layout()
    #     plt.savefig(f'figs/{muscle}-rms_emg_action.png')
    #     plt.close()
    
    # # Plotting for each pattern
    # for pattern, muscles_data in pattern_rms.items():
    #     plt.figure(figsize=(12, 6))
    #     for idx, (muscle, rms_values) in enumerate(muscles_data.items()):
    #         x_values = [idx] * len(rms_values)  # Create x values for each muscle
    #         plt.scatter(x_values, rms_values, label=muscle)

    #     plt.xticks(range(len(muscles)), muscles, rotation=45)
    #     plt.xlabel('Muscle')
    #     plt.ylabel('RMS EMG Value')
    #     plt.title(f'EMG RMS Values for Pattern {pattern}')
    #     plt.legend()
    #     plt.tight_layout()
    #     plt.savefig(f'figs/{pattern}-rms_emg_muscle.png')
    #     plt.close()

folders = {
    'depth': '.mp4',
    'rgb': '.mp4',
    'emg': '.csv',
    'text': '.txt'
}

def extract_datetime_part(filename):
    return filename.split('.')[0]  

def get_datetime_parts(path, extension):
    files = os.listdir(path)
    return {extract_datetime_part(f) for f in files if f.endswith(extension)}

def check_lost_file(base_path):
    for action in os.listdir(base_path):
        path = os.path.join(base_path, action)
        depth_dates = get_datetime_parts(os.path.join(path, 'depth'), folders['depth'])
        emg_dates = get_datetime_parts(os.path.join(path, 'emg'), folders['emg'])
        text_dates = get_datetime_parts(os.path.join(path, 'text'), folders['text'])
        rgb_dates = get_datetime_parts(os.path.join(path, 'rgb'), folders['rgb'])
        missing_in_rgb = (depth_dates & emg_dates & text_dates) - rgb_dates
        for date in sorted(missing_in_rgb):
            print(f"{path}: {date}")

def create_sample_folders(base_path, subject_id):
    subject_dir = os.path.join(base_path, subject_id)
    actions = [d for d in os.listdir(subject_dir) if os.path.isdir(os.path.join(subject_dir, d))]
    for action in actions:
        action_dir = os.path.join(subject_dir, action)
        text_dir = os.path.join(action_dir, 'text')
        for text_file in os.listdir(text_dir):
            if text_file.endswith('.txt'):
                text_path = os.path.join(text_dir, text_file)
                with open(text_path, 'r') as file:
                    content = file.read().strip()
    
                modes = content.split()
                mode_name = '-'.join([f"P{mode}" for mode in modes])
                
                base_filename = os.path.splitext(text_file)[0]
                sample_folder_name = f"S{subject_id}-A{action}-{mode_name}-{base_filename}"
                sample_dir = os.path.join(action_dir, sample_folder_name)
                os.makedirs(sample_dir, exist_ok=True)

                for data_type, suffix in folders.items():
                    source_dir = os.path.join(action_dir, data_type)
                    source_file = os.path.join(source_dir, f"{base_filename}{suffix}")
                    if os.path.exists(source_file):
                        dest_file = os.path.join(sample_dir, f"{sample_folder_name}-{data_type}{suffix}")
                        shutil.move(source_file, dest_file)

if __name__ == "__main__":
    base_path = '/root/emg-data-collection/data'
    # create_sample_folders(base_path, subject_id='2')
    plot_emgs('/root/emg-data-collection/data/2')

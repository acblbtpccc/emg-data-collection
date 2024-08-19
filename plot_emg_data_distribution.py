import os
import scipy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shutil
import matplotlib.colors as mcolors

import pandas as pd
import os
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
import seaborn as sns

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
            emg_path = os.path.join(sample_path, sample+'-emg.csv')
            data = pd.read_csv(emg_path, parse_dates=['timestamp'])
            for muscle in muscles:
                muscle_data = data[data['muscle'] == muscle]
                rms = calculate_rms(muscle_data['emg_value'])
                for p in individual_patterns:
                    data_container[action][p][muscle].append(rms)
    
    def flatten_data(data_container):
        rows = []
        for action, patterns in data_container.items():
            for pattern, muscles in patterns.items():
                for muscle, values in muscles.items():
                    for value in values:
                        rows.append({
                            'action': action,
                            'pattern': pattern,
                            'muscle': muscle,
                            'rms': value
                        })
        return pd.DataFrame(rows)

    df = flatten_data(data_container)
    p_values_df = pd.DataFrame(columns=['muscle', 'p_value'])
    for muscle in muscles:
        df_muscle = df[df['muscle'] == muscle]
        model = ols('rms ~ C(action)', data=df_muscle).fit()
        anova_results = anova_lm(model)
        print(f"ANOVA Results for {muscle} across all actions:")
        print(anova_results)
        print("\n")
        temp_df = pd.DataFrame({'muscle': [muscle], 'p_value': [anova_results['PR(>F)'].iloc[0]]})
        p_values_df = pd.concat([p_values_df, temp_df], ignore_index=True)

    def plot_pvalue_barchart(p_values_df, save_name):
        plt.figure(figsize=(12, 6))
        ax = sns.barplot(x='muscle', y='p_value', data=p_values_df)
        plt.title(save_name)
        plt.xlabel('Muscle')
        plt.ylabel('P-value')
        plt.yscale('log')
        plt.xticks(rotation=30)

        # Annotate each bar with the p-value
        for bar in ax.patches:
            plt.text(bar.get_x() + bar.get_width() / 2,  # x-coordinate of the text
                    bar.get_height(),  # y-coordinate of the text
                    f'{bar.get_height():.2e}',  # text to be displayed; formatted to scientific notation
                    ha='center',  # horizontal alignment
                    va='bottom')  # vertical alignment

        plt.savefig(save_name + '.png')
        plt.close()

    plot_pvalue_barchart(p_values_df, f'figs/AVOVA-pvalue-muslce-allactions')

    for action in action_order:
        p_values_df = pd.DataFrame(columns=['muscle', 'p_value'])
        for muscle in muscles:
            df_action_muscle = df[(df['action'] == action) & (df['muscle'] == muscle)]
            model = ols('rms ~ C(pattern)', data=df_action_muscle).fit()
            anova_results = anova_lm(model)
            print(f"ANOVA Results for {muscle} under action {action}:")
            print(anova_results)
            print("\n")
            temp_df = pd.DataFrame({'muscle': [muscle], 'p_value': [anova_results['PR(>F)'].iloc[0]]})
            p_values_df = pd.concat([p_values_df, temp_df], ignore_index=True)
        plot_pvalue_barchart(p_values_df, f'figs/AVOVA-P-values-Action{action}')
    
    # final_data = {}
    # for action in data_container:
    #     final_data[action] = {}
    #     for pattern in data_container[action]:
    #         final_data[action][pattern] = {}
    #         for muscle in data_container[action][pattern]:
    #             final_data[action][pattern][muscle] = np.array(data_container[action][pattern][muscle])
    # selected_action = action_order[0]  # 选择第二个动作

    # for selected_action in action_order:
    #     for selected_muscle in muscles:
    #         patterns_data = {pattern: final_data[selected_action][pattern][selected_muscle] for pattern in final_data[selected_action]}
    #         variances = {pattern: np.var(data) for pattern, data in patterns_data.items() if len(data) > 0}
    #         sample_var = np.mean(list(variances.values()))
    #         all_data = np.concatenate([data for data in patterns_data.values() if len(data) > 0])
    #         total_variance = np.var(all_data)
    #         f_stat = (total_variance-sample_var)/sample_var
    #         p_value = 1 - scipy.stats.f.cdf(f_stat, len(variances) - 1, sum(len(x) for x in patterns_data.values()) - len(variances))
    #         print(f"{selected_action:2} {selected_muscle:>16}: {f_stat:5.2f} {p_value:5.3f}")

    '''
    threshold_rate = 1.
    if not os.path.exists(f'intensity_dict_{threshold_rate}.npz'):
        intensity_dict = {muscle: {action: {pattern: 'middle' for pattern in patterns} for action in data_container} for muscle in muscles}
        import matplotlib.cm as cm
        colors = cm.rainbow(np.linspace(0, 1, 3))
        for action in data_container:
            pattern_rms = data_container[action]
            plt.figure(figsize=(10, 6))
            for muscle in muscles:
                normal = pattern_rms['P0'][muscle]
                std = np.std(normal)
                mean = np.mean(normal)
                for pattern in patterns:
                    x = [pattern] * len(pattern_rms[pattern][muscle])
                    y = pattern_rms[pattern][muscle]
                    y_mean = np.mean(y)
                    if y_mean > mean + threshold_rate * std:
                        label = 'high'
                        c = colors[0]
                    elif y_mean > mean - threshold_rate * std:
                        label = 'middle'
                        c = colors[1]
                    else:
                        label = 'low'
                        c = colors[2]
                    intensity_dict[muscle][action][pattern] = label
                    plt.scatter(x, y, label=pattern+'-'+label, color=c)
                plt.xlabel('Pattern')
                plt.ylabel('RMS EMG Value')
                plt.title(f'Action {action} EMG Data')
                plt.legend()
                plt.grid(True)
                plt.savefig(f'figs/{action}-{muscle}-rms_emg_muscle.png')
                plt.close()
        np.savez(f'intensity_dict_{threshold_rate}', intensity_dict=intensity_dict)
    else:
        intensity_dict = np.load(f'intensity_dict_{threshold_rate}.npz', allow_pickle=True)[()]
    for muscle in intensity_dict:
        for action in intensity_dict[muscle]:
            for pattern in intensity_dict[muscle][action]:
                print(f'{muscle}-{action}-{pattern}: {intensity_dict[muscle][action][pattern]}')
    '''


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
    # action = '1'
    # pattern_rms = data_container[action]
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

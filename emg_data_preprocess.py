import pandas as pd
import numpy as np
import os
import json
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
import seaborn as sns

muscles_name = ['L_Biceps', 'R_Biceps', 'L_Deltoid', 'R_Deltoid', 'L_Latiss', 'R_Latiss', 'L_Trapezius', 'R_Trapezius']
actions_name = ['1', '2', '3', '4', '5', '6', '7']
# actions_name = ['1', '3', '4', '5', '6', '7']
# patterns_name = ['P0', 'P4', 'P4,6', 'P5', 'P6', 'P7']
patterns_name = [f'P{i}' for i in range(12)]+['P1,2', 'P1,3', 'P4,6', 'P2,8','P3,11']
subjects_name = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13','14']
# subjects_name = ['15']


with open('ours_motion_file_list.txt', 'r', encoding='utf-8') as file:
    motion_name_list = [line.strip() for line in file]

def calculate_rms(values):
    return np.sqrt(np.mean(np.square(values)))

def calculate_iemg(values):
    return np.sum(values)

def calculate_pk_top10(values):
    """Calculate the Peak (PK) value of the signal."""
    return np.mean(np.sort(values)[-10:])

def read_data(base_path):
    data_container = {subject:{action: {pattern: {muscle: [] for muscle in muscles_name} for pattern in patterns_name} for action in actions_name} for subject in subjects_name}
    for subject in subjects_name:
        subject_path = os.path.join(base_path, subject)
        for action in actions_name:
            action_path = os.path.join(subject_path, action)
            for sample in os.listdir(action_path):
                if sample+'.npy' not in motion_name_list:
                    print("*****", sample)
                    continue
                sample_path = os.path.join(action_path, sample)
                emg_path = os.path.join(sample_path, sample+'-emg.csv')
                data = pd.read_csv(emg_path)
                pattern_path = os.path.join(sample_path, sample+'-text.txt')
                pattern = 'P'+ open(pattern_path).readline()
                for muscle in muscles_name:
                    muscle_data = data[data['muscle'] == muscle]
                    if len(muscle_data)==0:
                        print(subject, action, sample, muscle)
                    else:
                        features = calculate_rms(muscle_data['emg_value'])
                        # features = calculate_iemg(muscle_data['emg_value'])
                        data_container[subject][action][pattern][muscle].append(features)
    return data_container

def muscle_intensity(data_container, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    # os.makedirs('figs_rms_3sigma', exist_ok=True)
    for subject in data_container.keys():
        intensity_dict = {action: {pattern: {muscle: 'Activated' for muscle in muscles_name} for pattern in patterns_name} for action in actions_name}
        colors = cm.rainbow(np.linspace(0, 1, 3))
        for action in data_container[subject]:
            pattern_rms = data_container[subject][action]
            # plt.figure(figsize=(20, 4))
            for index, muscle in enumerate(muscles_name, start=1):
                ax = plt.subplot(1, len(muscles_name), index)
                normal = pattern_rms['P0'][muscle]
                if np.any(np.isnan(np.array(normal))) or len(normal)==0:
                    print(subject, action, muscle)
                std = np.std(normal)
                mean = np.mean(normal)
                for pattern in patterns_name:
                    x = [pattern] * len(pattern_rms[pattern][muscle])
                    y = pattern_rms[pattern][muscle]
                    y_mean = np.mean(y)
                    if y_mean > mean + 2 * std:
                        label = 'Over-activated'
                        c = colors[0]
                    elif y_mean <  mean - 2 * std:
                        label = 'Under-activated'
                        c = colors[1]
                    else:
                        label = 'Activated'
                        c = colors[2]
                    intensity_dict[action][pattern][muscle] = label
            #         ax.scatter(x, y, label=f'{pattern}-{label}', color=c)
            #     ax.set_title(f'{muscle} in Action {action}')
            #     ax.set_xlabel('Pattern')
            #     ax.set_ylabel('RMS EMG Value')
            #     ax.grid(True)
            #     if index == len(muscles_name):
            #         plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            # plt.subplots_adjust(wspace=0.5) 
            # plt.savefig(f'figs_iemg_3sigma/S{subject}-A{action}-rms_emg_muscle.png')
            # plt.close()
        save_path = os.path.join(save_dir, f'S{subject}_intensity_dict.json')
        with open(save_path, 'w') as f:
            json.dump(intensity_dict, f, indent=4)

def plot_voting_results(intensity_dict, idx2label, save_dir):
    num_actions = len(intensity_dict)
    num_patterns = len(next(iter(intensity_dict.values())))
    fig, axes = plt.subplots(num_actions, num_patterns, figsize=(50, 30), squeeze=False)
    
    for i, action in enumerate(intensity_dict):
        for j, pattern in enumerate(intensity_dict[action]):
            muscle_labels = list(intensity_dict[action][pattern].keys())
            votes = [intensity_dict[action][pattern][muscle] for muscle in muscle_labels]
            
            under_activated = [vote[0] for vote in votes]
            activated = [vote[1] for vote in votes]
            over_activated = [vote[2] for vote in votes]
            
            x = np.arange(len(muscle_labels))
            width = 0.2
            
            ax = axes[i, j]
            ax.bar(x - width, under_activated, width, label='Under-activated')
            ax.bar(x, activated, width, label='Activated')
            ax.bar(x + width, over_activated, width, label='Over-activated')
            
            ax.set_title(f'{action} - {pattern}')
            ax.set_xticks(x)
            ax.set_xticklabels(muscle_labels, rotation=45, ha='right')
            ax.legend()
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    save_path = os.path.join(save_dir, 'voting_results.png')
    plt.savefig(save_path, dpi=300)
    plt.close()


def muscle_intensity_professional(data_container, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    intensity_dict = {action: {pattern: {muscle: [0, 0, 0] for muscle in muscles_name} for pattern in patterns_name} for action in actions_name}
    idx2label = {0: 'low', 1: 'middle', 2: 'high'}
    for subject in data_container.keys():
        for action in data_container[subject]:
            action_rms = data_container[subject][action]
            for index, muscle in enumerate(muscles_name, start=1):
                normal = action_rms['P0'][muscle]
                if np.any(np.isnan(np.array(normal))) or len(normal)==0:
                    print(subject, action, muscle)
                std = np.std(normal)
                mean = np.mean(normal)
                for pattern in patterns_name:
                    y = action_rms[pattern][muscle]
                    y_mean = np.mean(y)
                    if y_mean > mean + .5 * std:
                        idx = 2
                    elif y_mean <  mean - .5 * std:
                        idx = 0
                    else:
                        idx = 1
                    intensity_dict[action][pattern][muscle][idx] += 1
    intensity_label_dict = {action: {pattern: {muscle: idx2label[np.argmax(intensity_dict[action][pattern][muscle])] for muscle in muscles_name} for pattern in patterns_name} for action in actions_name}
    save_path = os.path.join(save_dir, f'professional_intensity_dict.json')
    with open(save_path, 'w') as f:
        json.dump(intensity_label_dict, f, indent=4)
    # Plot the results
    plot_voting_results(intensity_dict, idx2label, save_dir)

def plot_intensity_by_subject(data_container, intensity_dict_dir):
    # Load all intensity dictionaries
    intensity_dicts = {}
    for filename in os.listdir(intensity_dict_dir):
        subject_id = filename.split('_')[0][1:]  # Assuming filename format is 'S{subject}_intensity_dict.json'
        with open(os.path.join(intensity_dict_dir, filename), 'r') as file:
            intensity_dicts[subject_id] = json.load(file)

    # Define colors for different intensity levels
    colors = {'high': 'red', 'middle': 'green', 'low': 'blue'}
    os.makedirs('figs_iemg_each_action_pattern', exist_ok=True)
    # Iterate over each action and pattern
    for action in actions_name:
        for pattern in patterns_name:
            plt.figure(figsize=(35, 4))
            index = 1
            for muscle in muscles_name:
                ax = plt.subplot(1, len(muscles_name), index)
                for subject_id, subject_data in data_container.items():
                    if action in subject_data and pattern in subject_data[action]:
                        rms_values = subject_data[action][pattern][muscle]
                        intensity_label = intensity_dicts[subject_id][action][pattern][muscle]
                        ax.scatter([subject_id] * len(rms_values), rms_values, color=colors[intensity_label], label=f'{subject_id}-{intensity_label}')
                
                ax.set_title(f'{muscle} A{action} {pattern}')
                ax.set_xlabel('Subject')
                ax.set_ylabel('RMS EMG Value')
                ax.grid(True)
                index = index +1
                # if index == len(muscles):
                #     plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            plt.subplots_adjust(left=0.05, right=0.95, wspace=0.3, bottom=0.25)
            plt.savefig(f'figs_iemg_each_action_pattern/A{action}-{pattern}_rms_emg_muscle.png')
            plt.close()

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
        p_value = bar.get_height()
        bar.set_color('#fc8d62' if p_value > 0.05 else '#66c2a5')
        plt.text(bar.get_x() + bar.get_width() / 2,  # x-coordinate of the text
                bar.get_height(),  # y-coordinate of the text
                f'{bar.get_height():.2e}',  # text to be displayed; formatted to scientific notation
                ha='center',  # horizontal alignment
                va='bottom')  # vertical alignment

    plt.savefig(save_name + '.png')
    plt.close()

def anova_analysis(data_container, muscle_map_path):
    rows = []
    for subject, actions in data_container.items():
        with open(os.path.join(muscle_map_path, f'S{subject}_intensity_dict_0.75.json'), 'r') as f:
            intensity_dict = json.load(f)
            print(intensity_dict)

        for action, patterns in actions.items():
            for pattern, muscles in patterns.items():
                for muscle, values in muscles.items():
                    label = intensity_dict[action][pattern][muscle]
                    for value in values:
                         rows.append({
                            'subject': subject,
                            'action': action,
                            'pattern': pattern,
                            'muscle': muscle,
                            'rms': value,
                            'label': label
                        })
    df = pd.DataFrame(rows)
    p_values_df = pd.DataFrame(columns=['muscle', 'p_value'])
    label_mapping = {
        'high': 0,
        'middle': 1,
        'low': 2
    }
    for muscle in muscles_name:
        df_muscle = df[df['muscle'] == muscle]
        df_muscle['label'] = df_muscle['label'].replace(label_mapping)
        model = ols('label ~ C(pattern)', data=df_muscle).fit()
        anova_results = anova_lm(model)
        print(f"ANOVA Results for {muscle} across all actions:")
        print(anova_results)
        print("\n")
        temp_df = pd.DataFrame({'muscle': [muscle], 'p_value': [anova_results['PR(>F)'].iloc[0]]})
        p_values_df = pd.concat([p_values_df, temp_df], ignore_index=True)
    plot_pvalue_barchart(p_values_df, f'figures/S2345-AVOVA-pvalue-muslce-allactions')

    n_actions = len(actions_name)
    fig, axes = plt.subplots(nrows=1, ncols=n_actions, figsize=(n_actions * 6, 6), sharey=True)
    fig.suptitle('P-value Comparison Across Different Actions')

    for idx, action in enumerate(actions_name):
        p_values_df = pd.DataFrame(columns=['muscle', 'p_value'])
        for muscle in muscles:
            df_action_muscle = df[(df['action'] == action) & (df['muscle'] == muscle)]
            df_action_muscle['label'] = df_action_muscle['label'].replace(label_mapping)
            model = ols('label ~ C(pattern)', data=df_action_muscle).fit()
            anova_results = anova_lm(model)
            temp_df = pd.DataFrame({'muscle': [muscle], 'p_value': [anova_results['PR(>F)'].iloc[0]]})
            p_values_df = pd.concat([p_values_df, temp_df], ignore_index=True)
        
        ax = axes[idx]
        sns.barplot(x='muscle', y='p_value', data=p_values_df, ax=ax)
        ax.set_title(f'Action {action}')
        ax.set_yscale('log')
        ax.tick_params(axis='x', rotation=30)
        
        # Annotate each bar with the p-value
        for bar in ax.patches:
            p_value = bar.get_height()
            bar.set_color('#fc8d62' if p_value > 0.05 else '#66c2a5')
            ax.text(bar.get_x() + bar.get_width() / 2, p_value, f'{p_value:.2e}',
                    ha='center', va='bottom')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) 
    plt.savefig('figures/S2345-clslabel-AVOVA-P-values-PerAction.png')
    plt.close()
    
if __name__ == "__main__":
    base_path = '/root/emg-data-collection/data'
    data_container = read_data(base_path)
    # muscle_intensity(data_container, 'rms_muscle_intensity_map')
    muscle_intensity_professional(data_container, 'rms_muscle_intensity_map')
    # plot_intensity_by_subject(data_container, 'img_muscle_intensity_map')
    # anova_analysis(data_container, 'muscle_intensity_map')

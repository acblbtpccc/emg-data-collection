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
patterns = [f'P{i}' for i in range(12)] 

def calculate_rms(values):
    return np.sqrt(np.mean(np.square(values)))

def calculate_iemg(values):
    return np.sum(values)

def calculate_pk_top10(values):
    """Calculate the Peak (PK) value of the signal."""
    return np.mean(np.sort(values)[-10:])

def calculate_var(values):
    """Calculate the Variance (VAR) of the signal."""
    return np.var(values, ddof=1)  # ddof=1 provides the sample variance

def calculate_wamp(values, threshold):
    """Calculate the Willison Amplitude (WAMP) of the signal."""
    return np.sum(np.abs(np.diff(values)) > threshold)

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

def plot_pvalues_all_actions(df, action_order, muscles, save_name):
    n_actions = len(action_order)
    fig, axes = plt.subplots(nrows=1, ncols=n_actions, figsize=(n_actions * 6, 6), sharey=True)
    fig.suptitle('P-value Comparison Across Different Actions')

    for idx, action in enumerate(action_order):
        p_values_df = pd.DataFrame(columns=['muscle', 'p_value'])
        for muscle in muscles:
            df_action_muscle = df[(df['action'] == action) & (df['muscle'] == muscle)]
            model = ols('rms ~ C(pattern)', data=df_action_muscle).fit()
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
    plt.savefig(save_name + '.png')
    plt.close()

def plot_emgs_all_subject(base_path):
    subjects_list = os.listdir(base_path)
    data_container = {subject:{action: {pattern: {muscle: [] for muscle in muscles} for pattern in patterns} for action in action_order} for subject in subjects_list}
    for subject in os.listdir(base_path):
        subject_path = os.path.join(base_path, subject)
        for action in os.listdir(subject_path):
            action_path = os.path.join(subject_path, action)
            for sample in os.listdir(action_path):
                sample_path = os.path.join(action_path, sample)
                pattern = extract_patterns(sample)
                individual_patterns = pattern.split(',')
                individual_patterns = standardize_pattern(individual_patterns)
                emg_path = os.path.join(sample_path, sample+'-emg.csv')
                data = pd.read_csv(emg_path, parse_dates=['timestamp'])
                for muscle in muscles:
                    muscle_data = data[data['muscle'] == muscle]
                    # feats = calculate_rms(muscle_data['emg_value'])
                    feats = calculate_pk_top10(muscle_data['emg_value'])
                    # feats = calculate_iemg(muscle_data['emg_value'])
                    # feats = calculate_wamp(muscle_data['emg_value'], threshold=1000)
                    # feats = calculate_var(muscle_data['emg_value'])

                    for p in individual_patterns:
                        data_container[subject][action][p][muscle].append(feats)
    
    def flatten_data(data_container):
        rows = []
        for subject, actions in data_container.items():
            for action, patterns in actions.items():
                for pattern, muscles in patterns.items():
                    for muscle, values in muscles.items():
                        for value in values:
                            rows.append({
                                'subject': subject,
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

    plot_pvalue_barchart(p_values_df, f'figures/iEMG-AVOVA-pvalue-muslce-allactions')

def plot_emgs(base_path):
    data_container = {action: {pattern: {muscle: [] for muscle in muscles} for pattern in patterns} for action in action_order}

    for action in os.listdir(base_path):
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

    plot_pvalue_barchart(p_values_df, f'figures/S5-AVOVA-pvalue-muslce-allactions')
    plot_pvalues_all_actions(df, action_order, muscles, f'figures/iEMG-AVOVA-P-values-PerAction')

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

if __name__ == "__main__":
    # plot_emgs_all_subject('/root/emg-data-collection/data')
    plot_emgs('/root/emg-data-collection/data/5')

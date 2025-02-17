'''
plot GIF animation of EMG data

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Load CSV data S4-A1-P1-2024-08-21-10-19-16-rgb-mesh
df = pd.read_csv('data/4/1/S4-A1-P1-2024-08-21-10-19-16/S4-A1-P1-2024-08-21-10-19-16-emg.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.sort_values('timestamp', inplace=True)  # 确保数据按时间排序

# Define muscle pairs
muscle_pairs = [
    ('L_Biceps', 'R_Biceps'),
    ('L_Deltoid', 'R_Deltoid'),
    ('L_Latiss', 'R_Latiss'),
    ('L_Trapezius', 'R_Trapezius')
]
colors = {
    'L_Biceps': 'blue',
    'R_Biceps': 'green',
    'L_Deltoid': 'blue',
    'R_Deltoid': 'green',
    'L_Latiss': 'blue',
    'R_Latiss': 'green',
    'L_Trapezius': 'blue',
    'R_Trapezius': 'green'
}

# Prepare the plot
fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(10, 8), sharex=True, sharey=True)
axes = axes.flatten()

# Set time index
df.set_index('timestamp', inplace=True)

# Define a function to update the plot
def update(frame):
    current_time = df.index[frame]
    window_start = max(current_time - pd.Timedelta(seconds=5), df.index.min())  # Adjust 5 seconds back

    for i, (muscle_l, muscle_r) in enumerate(muscle_pairs):
        ax = axes[i]
        if frame == 0:
            ax.clear()
            ax.set_title(f'{muscle_l} vs {muscle_r}')
            ax.legend()

        # Filter data by muscle and limit by the sliding window
        subset_l = df[(df['muscle'] == muscle_l) & (df.index <= current_time) & (df.index >= window_start)]
        subset_r = df[(df['muscle'] == muscle_r) & (df.index <= current_time) & (df.index >= window_start)]

        ax.plot(subset_l.index, subset_l['emg_value'], label=f'{muscle_l}' if frame == 0 else "", color=colors[muscle_l])
        ax.plot(subset_r.index, subset_r['emg_value'], label=f'{muscle_r}' if frame == 0 else "", color=colors[muscle_r])

    # Update x-axis range to the sliding window
    plt.xlim(window_start, current_time)

# Calculate the total number of frames as the length of the DataFrame
frame_step = 60  # 减少帧数，每10行数据更新一次
total_frames = range(0, len(df), frame_step)

# Create animation
ani = FuncAnimation(fig, update, frames=total_frames, repeat=False)

# Show the plot
ani.save('emg_animation.gif', writer='imagemagick')

'''

import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV data
# path_P0 = 'data/12/3/S12-A3-P0-2024-10-17-20-04-39/S12-A3-P0-2024-10-17-20-04-39-emg.csv'
# path_P6 = 'data/12/3/S12-A3-P6-2024-10-17-20-07-32/S12-A3-P6-2024-10-17-20-07-32-emg.csv'
# path_p46 = 'data/12/3/S12-A3-P4,6-2024-10-17-20-08-28/S12-A3-P4,6-2024-10-17-20-08-28-emg.csv'

path_P0 = 'data/11/3/S11-A3-P0-2024-10-16-19-45-00/S11-A3-P0-2024-10-16-19-45-00-emg.csv'
path_P6 = 'data/11/3/S11-A3-P6-2024-10-16-19-48-37/S11-A3-P6-2024-10-16-19-48-37-emg.csv'
path_p46 = 'data/11/3/S11-A3-P4,6-2024-10-16-19-49-21/S11-A3-P4,6-2024-10-16-19-49-21-emg.csv'
def load_and_filter_data(file_path, muscles_of_interest):
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    filtered_data = df[df['muscle'].isin(muscles_of_interest)]
    return filtered_data.sort_values(by='timestamp')
# List of CSV files
csv_files = [path_P0, path_P6, path_p46]
muscles_of_interest = ['R_Deltoid', 'R_Trapezius']
colors = {'R_Deltoid': '#FA7F6F', 'R_Trapezius': '#82B0D2'}

# Create subplots
fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharey=True)

# Process each file
for i, file in enumerate(csv_files):
    data = load_and_filter_data(file, muscles_of_interest)
    for muscle in muscles_of_interest:
        muscle_data = data[data['muscle'] == muscle]
        axes[i].plot(muscle_data['timestamp'], muscle_data['emg_value'], 
                     label=muscle, color=colors[muscle])
    axes[i].set_ylabel('EMG Value', fontsize=20)
    axes[i].set_xlabel('') # Remove x-axis label
    axes[i].set_xticks([]) # Remove x-axis tick labels
    axes[i].legend(fontsize=18)
    axes[i].tick_params(axis='y', labelsize=15)




# df = pd.read_csv(path_p46)

# # Convert the 'timestamp' column to datetime
# df['timestamp'] = pd.to_datetime(df['timestamp'])

# # Filter the data for R_Deltoid and R_Biceps
# muscles_of_interest = ['R_Deltoid', 'R_Biceps']
# filtered_data = df[df['muscle'].isin(muscles_of_interest)]

# # Sort the filtered data by timestamp
# filtered_data = filtered_data.sort_values(by='timestamp')

# # Plot the data
# plt.figure(figsize=(10, 6))

# for muscle in muscles_of_interest:
#     muscle_data = filtered_data[filtered_data['muscle'] == muscle]
#     plt.plot(muscle_data['timestamp'], muscle_data['emg_value'], label=muscle)

# plt.xlabel('')  # Remove x-axis label
# plt.ylabel('sEMG Value')
# plt.xticks([])  # Remove x-axis tick labels
# plt.legend()
# plt.tight_layout()
plt.savefig('emg_plot.png')
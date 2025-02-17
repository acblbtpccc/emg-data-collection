import os
import shutil
import pandas as pd
muscles_name = ['L_Biceps', 'R_Biceps', 'L_Deltoid', 'R_Deltoid', 'L_Latiss', 'R_Latiss', 'L_Trapezius', 'R_Trapezius']

root_dir = '/root/emg-data-collection/data/'
total_sample_size = 0
for subject in os.listdir(root_dir):
    subject_path = os.path.join(root_dir, subject)
    subject_sample_size = 0
    for action in os.listdir(subject_path):
        action_path = os.path.join(subject_path, action)
        for sample in os.listdir(action_path):
            sample_path = os.path.join(action_path, sample)
            emg_path = os.path.join(sample_path, sample+'-emg.csv')
            df = pd.read_csv(emg_path)
            if len(df)>5000:
                print(f"File {sample_path} too long.")
                frame_path = os.path.join(sample_path, sample+'-frame.csv')
                frame_df = pd.read_csv(frame_path)
                frame_df['timestamp'] = pd.to_datetime(frame_df['timestamp'], format='%Y-%m-%d_%H-%M-%S.%f')
                min_frame_timestamp = frame_df['timestamp'].min()
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S.%f')
                
                filtered_emg_df = df[df['timestamp'] >= min_frame_timestamp]
                print(len(filtered_emg_df))
                filtered_emg_df.to_csv(emg_path, index=False)

            existing_muscles = set(df['muscle'].unique())
            missing_muscles = set(muscles_name) - existing_muscles

            if missing_muscles:
                print(f"Missing muscles: {', '.join(missing_muscles)}")
                # os.remove(sample_path)
                print(f"File {sample_path} has been deleted due to missing muscle data.")
            
            # Check if there are any NaN values in the 'emg_value' column
            if df['emg_value'].isna().any():
                print(f"NaN found in {sample}")
            
            # Remove rows where 'emg_value' column has NaN values
            df_cleaned = df.dropna(subset=['emg_value'])

            # Save the cleaned DataFrame back to the CSV, replacing the original
            df_cleaned.to_csv(emg_path, index=False)
            
            required_files = ['-emg.csv', '-depth.mp4', '-rgb.mp4', '-text.txt']

             # Check each file
            files_existence = {}
            all_files_exist = True
            for file_suffix in required_files:
                # Construct full file path
                file_path = os.path.join(sample_path, sample + file_suffix)
                # Check if the file exists
                file_exists = os.path.exists(file_path)
                files_existence[file_suffix] = file_exists
                all_files_exist &= file_exists  # Update the existence check

            # Output the results and potentially delete the directory
            if not all_files_exist:
                print(f"File {sample_path} should check. Missing files detected.")
                # Delete the directory if any required files are missing
                try:
                    shutil.rmtree(sample_path)
                    print(f"Deleted {sample_path} due to missing files.")
                except Exception as e:
                    print(f"Error deleting {sample_path}: {e}")
            total_sample_size = total_sample_size+1
            subject_sample_size = subject_sample_size+1
    print('subject: ', subject, subject_sample_size)
print('total: ', total_sample_size)
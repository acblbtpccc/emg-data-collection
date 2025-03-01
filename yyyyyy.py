import os
import shutil

def rename_files_and_folders(root_path):
    # 递归遍历目录
    # for path, dirs, files in os.walk(root_path, topdown=False):
    #     for dirname in dirs:
    #         if dirname.startswith("S6-A3-P1"):
    #             old_dir_path = os.path.join(path, dirname)
    #             new_dir_path = os.path.join(path, dirname.replace("S6-A3-P1", "S6-A3-P5"))
    #             print(f"Renamed '{old_dir_path}' to '{new_dir_path}'")
    #             shutil.move(old_dir_path, new_dir_path)
                
    for path, dirs, files in os.walk(root_path):
        for dirname in dirs:
            if dirname.startswith("S21-A1-Px-"):
                print(dirname)
                full_dir_path = os.path.join(path, dirname)
                subdir_files = os.listdir(full_dir_path)
                for filename in subdir_files:
                    if filename.startswith("S21-A1-Px-"):
                        old_file_path = os.path.join(full_dir_path, filename)
                        new_file_path = os.path.join(full_dir_path, filename.replace("S21-A1-Px-", "S21-A1-P1-"))
                        print(f"Renamed '{old_file_path}' to '{new_file_path}'")
                        shutil.move(old_file_path, new_file_path)
                
                new_file_path = full_dir_path.replace("S21-A1-Px-", "S21-A1-P1-")
                print(f"Renamed '{full_dir_path}' to '{new_file_path}'")
                shutil.move(full_dir_path, new_file_path)
                    

# # 指定需要更改的起始目录
start_dir = "./data/21/1"
rename_files_and_folders(start_dir)

# import pandas as pd
# import os
# root_dir = '/root/emg-data-collection/data/1'
# for action in os.listdir(root_dir):
#     action_path = os.path.join(root_dir, action)
#     for sample in os.listdir(action_path):
#         sample_path = os.path.join(action_path, sample)
#         emg_path = os.path.join(sample_path, sample+'-emg.csv')
#         df = pd.read_csv(emg_path)
#         if df['emg_value'].isna().any(): 
#             print(sample)

        # r_emg = df[df['muscle'] == 'R_Trapezius']['emg_value'].reset_index(drop=True)
        # l_emg = df[df['muscle'] == 'L_Trapezius']['emg_value'].reset_index(drop=True)
        # print('now dealing with ', sample, r_emg.shape, l_emg.shape)
        # if r_emg.shape[0] == l_emg.shape[0]:
        #     df.loc[(df['muscle'] == 'L_Trapezius'), 'emg_value'] = r_emg
        # elif r_emg.shape[0] > l_emg.shape[0]:
        #     # Copy only the number of data points in l_emg
        #     df.loc[df['muscle'] == 'L_Trapezius', 'emg_value'] = r_emg[:l_emg.shape[0]]
        # else:
        #     # r_emg has fewer samples, so first truncate L_Trapezius then copy r_emg
        #     mask = df['muscle'] == 'L_Trapezius'
        #     idxs_to_keep = df[mask].index[:r_emg.shape[0]]  # Get indices to keep
        #     df = df.drop(df[mask].index.difference(idxs_to_keep))  # Drop extra indices
        #     df.loc[mask, 'emg_value'] = r_emg
        # df.to_csv(emg_path, index=False)



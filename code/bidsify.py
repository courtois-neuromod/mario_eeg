import argparse
import os
from mne.io import read_raw_edf
from mne_bids import write_raw_bids, BIDSPath
import pandas as pd
import shutil

parser = argparse.ArgumentParser(description='BIDSify the mario_eeg source data.')
parser.add_argument('-s',
                    '--sourcedata', 
                    help='Source directory to convert to BIDS. Must contain behav and eeg folders.',
                    type=str,
                    default=None)
parser.add_argument('-b',
                    '--bidsroot', 
                    help='Directory to write BIDS output to.', 
                    type=str,
                    default=None)

def parse_info_from_filename(filename, filetype='eeg'):
    """
    Parse information from the EEG filename.
    """
    if filetype == 'eeg':
        subject = filename.split('_')[0].split('-')[1]
        session = filename.split('_')[1].split('-')[1]
        task = filename.split('_')[2].split('-')[1]
        run = filename.split('_')[3].split('-')[1]
    elif filetype == 'events':
        subject = filename.split('_')[0].split('-')[1]
        session = filename.split('_')[1].split('-')[1]
        task = filename.split('_')[3].split('-')[1]
        run = filename.split('_')[4].split('-')[1]

    return subject, session, task, run

def parse_info_from_bk2name(bk2name):
    """
    Parse information from the BK2 filename.
    Ex. sub-01_ses-001_20230203-102154_SuperMarioBros-Nes_Level1-2_000.bk2
    """
    world = bk2name.split('_')[4][-3]
    level = bk2name.split('_')[4][-1]
    rep = bk2name.split('_')[5].split('.')[0]

    return world, level, rep




def main(args):
    sourcedata_dir = args.sourcedata
    bidsroot = args.bidsroot
    if bidsroot is None:
        bidsroot = os.getcwd()
    if sourcedata_dir is None:
        sourcedata_dir = os.path.join(bidsroot, 'sourcedata')
    print(f'Converting sourcedata from {sourcedata_dir} to BIDS format in {bidsroot}')
    for root, folder, files in sorted(os.walk(sourcedata_dir)):
        for file in files:
            if file.endswith('.edf'):
                subject, session, task, run = parse_info_from_filename(file, filetype='eeg')
                bidspath = BIDSPath(subject=subject, session=session, task=task, run=run, root=bidsroot)
                print(f'Found EEG file: {file} for subject {subject}, session {session}, task {task}, run {run}')
                raw = read_raw_edf(os.path.join(root, file), preload=False, verbose=False)
                write_raw_bids(raw, bidspath, overwrite=True)
    for root, folder, files in sorted(os.walk(sourcedata_dir)):
        for file in files:
            if file.endswith('.tsv'):
                subject, session, task, run = parse_info_from_filename(file, filetype='events')
                print(f'Found events file: {file} for subject {subject}, session {session}, task {task}, run {run}')
                events_fname = f'sub-{subject}_ses-{session}_task-{task}_run-{run}_events.tsv'
                os.makedirs(os.path.join(bidsroot, f'sub-{subject}', f'ses-{session}', 'gamelogs'), exist_ok=True)
                os.makedirs(os.path.join(bidsroot, f'sub-{subject}', f'ses-{session}', 'eeg'), exist_ok=True)
                events_data = pd.read_csv(os.path.join(root, file), sep='\t')
                repetition_events = events_data[events_data['trial_type'] == 'gym-retro_game']
                for idx_row, row in repetition_events.iterrows():
                    bk2_sourcename = row.stim_file.split('/')[-1]
                    bk2_sourcepath = os.path.join(sourcedata_dir, 'behav', f'sub-{subject}', f'ses-{session}', bk2_sourcename)
                    world, level, rep = parse_info_from_bk2name(bk2_sourcename)
                    bk2_destination = os.path.join(bidsroot, f'sub-{subject}', f'ses-{session}', 'gamelogs', f'sub-{subject}_ses-{session}_task-{task}_run-{run}_level-w{world}l{level}_rep-{rep}.bk2')
                    shutil.copy(bk2_sourcepath, bk2_destination)
                    events_data.loc[idx_row, 'stim_file'] = ('/').join(bk2_destination.split('/')[-4:])
                    events_data.loc[idx_row, 'level'] = f'w{world}l{level}'
                
                events_data.to_csv(os.path.join(bidsroot, f'sub-{subject}', f'ses-{session}', 'eeg', events_fname), sep='\t', index=False)
    return

if __name__ == "__main__":
    args = parser.parse_args()
    main(args)

# AUTOGENERATED! DO NOT EDIT! File to edit: 00_metadata.ipynb (unless otherwise specified).

__all__ = ['path', 'path_meta', 'dir_trn', 'dir_tst', 'fth_lbl', 'fth_trn', 'fth_tst', 'fth_trn_comb',
           'fth_trn_comb_any', 'path_trn', 'path_tst', 'fn_splits', 'fn_splits_any', 'fn_splits_sample', 'fn_grps',
           'fn_grps_any', 'htypes', 'fth_df_comb1', 'fth_df_tst1', 'fn_splits_stg1', 'fn_splits_stg1_any',
           'fn_grps_stg1', 'save_lbls', 'load_feather', 'save_feather', 'process_metadata', 'group_cv', 'split_data',
           'get_splits', 'MetaType', 'Meta', 'lazy_loaders']

# Cell
from .imports import *

# Cell
set_num_threads(1)
path = Path('~/data/rsna').expanduser()
path_meta = path/'meta'

# Cell
dir_trn = 'stage_2_train'
dir_tst = 'stage_2_test'
fth_lbl = path_meta/'labels2.fth'
fth_trn = path_meta/'df_trn2.fth'
fth_tst = path_meta/'df_tst2.fth'
fth_trn_comb = path_meta/'df_trn2_comb.fth'
fth_trn_comb_any = path_meta/'df_trn2_any.fth'

# Cell
path_trn = path/dir_trn
path_tst = path/dir_tst


# Cell
fn_splits = path_meta/'splits.pkl'
fn_splits_any = path_meta/'splits_any.pkl'
fn_splits_sample = path_meta/'splits_sample.pkl'
fn_grps = path_meta/'grps.pkl'
fn_grps_any = path_meta/'grps_any.pkl'

# Cell
htypes = ['any','epidural','intraparenchymal','intraventricular','subarachnoid','subdural']

# Cell
# Stage 1 training
# dir_trn = 'stage_1_train_images'
# dir_tst = 'stage_1_test_images'
# fth_lbl = path_meta/'labels.fth'
# fth_trn = path_meta/'df_trn.fth'
# fth_tst = path_meta/'df_tst.fth'

fth_df_comb1 = path_meta/'df_trn1_comb.fth'
fth_df_tst1 = path_meta/'df_tst1.fth'

fn_splits_stg1 = path_meta/'splits_stg1.pkl'
fn_splits_stg1_any = path_meta/'splits_stg1_any.pkl'

fn_grps_stg1 = path_meta/'grps_stg1.pkl'

# Cell
def save_lbls():
    path_lbls = path/f'{dir_trn}.csv'
    if fth_lbl.exists(): return
    lbls = pd.read_csv(path_lbls)
    lbls[["ID","htype"]] = lbls.ID.str.rsplit("_", n=1, expand=True)
    lbls.drop_duplicates(['ID','htype'], inplace=True)
    pvt = lbls.pivot('ID', 'htype', 'Label')
    pvt.reset_index(inplace=True)
    pvt.to_feather(fth_lbl)

# Cell
def load_feather(fth_path):
    df = pd.read_feather(fth_path)
    return df.set_index('SOPInstanceUID').sort_values(['SeriesInstanceUID', "ImagePositionPatient2"])

def save_feather(df, fth_path): df.reset_index().sort_values(['SeriesInstanceUID', "ImagePositionPatient2"]).to_feather(fth_path)

# Cell
def process_metadata(fns, out_f, n_workers=12):
    if out_f.exists(): return
    df = pd.DataFrame.from_dicoms(fns, px_summ=True, window=dicom_windows.brain, n_workers=12)
    save_feather(df, out_f)
    return df


# Cell
def group_cv(idx, grps): return np.concatenate([grps[o] for o in range_of(grps) if o!=idx])

# column can also be PatientID
def split_data(df, cv_idx, grps, column):
    idx = L.range(df)
    grp_cv = group_cv(cv_idx, grps)
    mask_grp = df[column].isin(grp_cv)
    mask_col = df[column].isin(grps[cv_idx])
    return idx[mask_grp],idx[mask_col]

# Cell
def get_splits(df, column='SeriesInstanceUID', nfold=8, ifold=0):
    set_seed(42)
    unique_ids = df[column].unique()
    np.random.shuffle(unique_ids)
    grps = np.array_split(unique_ids, nfold)
    return split_data(df, ifold, grps, column=column), grps

# Cell
lazy_loaders = {
    'df_any': lambda: pd.read_feather(fth_trn_comb_any).set_index('SOPInstanceUID'),
    'df_labels': lambda: pd.read_feather(fth_lbl).set_index('ID'),
    'df_comb': lambda: pd.read_feather(fth_trn_comb).set_index('SOPInstanceUID'),
    'df_tst': lambda: pd.read_feather(fth_tst).set_index('SOPInstanceUID'),
    'df_comb1': lambda: pd.read_feather(fth_df_comb1).set_index('SOPInstanceUID'),
    'fns_trn': lambda: path_trn.ls(),
    'fns_tst': lambda: path_tst.ls(),
    'splits': lambda: fn_splits.load(),
    'grps': lambda: fn_grps.load(),
    'grps_any': lambda: fn_grps_any.load(),
    'grps_stg1': lambda: fn_grps_stg1.load(),
    'splits_any': lambda: fn_splits_any.load(),
    'splits_sample': lambda: fn_splits_sample.load(),
    'splits_stg1': lambda: fn_splits_stg1.load(),
    'splits_stg1_any': lambda: fn_splits_stg1_any.load(),
}

class MetaType(type):
    def __dir__(self):
        return lazy_loaders.keys()
    def __getattr__(self, name: str):
        if name in self.__dict__: return self.__dict__[name]
        if name in lazy_loaders:
            setattr(self, name, lazy_loaders[name]())
            return self.__dict__[name]
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

class Meta(metaclass=MetaType): pass
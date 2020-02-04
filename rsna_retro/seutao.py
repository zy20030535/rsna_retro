# AUTOGENERATED! DO NOT EDIT! File to edit: 06_seutao_features.ipynb (unless otherwise specified).

__all__ = ['path', 'np_file', 'np_file_test', 'csv_file', 'csv_file_test', 'fth_file', 'fth_file_test', 'OpenFeatMap',
           'get_seutao_dls', 'OpenMultFeatMap', 'get_seutao_dls_meta', 'FlattenPred', 'submit_predictions']

# Cell
from .imports import *
from .metadata import *
from .preprocess import *
from .train import *
from .train3d import *

# Cell
path = Path('~/kaggle/RSNA2019_1st_place_solution/SequenceModel/features/stage2_finetune/st_se101_256_fine').expanduser()
np_file = path/'st_se101_256_fine_val_oof_feature_TTA_stage2_finetune.npy'
np_file_test = path/'st_se101_256_fine_test_feature_TTA_stage2_finetune.npy'
csv_file = path/'st_se101_256_fine_val_prob_TTA_stage2_finetune.csv'
csv_file_test = path/'st_se101_256_fine_test_prob_TTA_stage2_finetune.csv'


fth_file = csv_file.with_suffix('.fth')
fth_file_test = csv_file_test.with_suffix('.fth')

# Cell
class OpenFeatMap:
    def __init__(self, feature_map):
        self.fm = feature_map
        self.tt = ToTensor()
    def __call__(self, item):
        if isinstance(item, (str, Path)): return self.fn(item)
        xs = [torch.from_numpy(self.fm[x]) for x in item]
        return TensorCTScan(torch.stack(xs))

# Cell
def get_seutao_dls(df, np_file, csv_file, bs=1, num_workers=8, test=False):
    print('loading features')
    features = np.load(str(np_file))
    prob_df = pd.read_csv(csv_file)
    sops = [f.replace('.dcm', '') for f in prob_df.filename.values]
    feature_map = dict(zip(sops, features))
    print('Done loading features')

    dsets = get_3d_dsets(df, open_fn=OpenFeatMap(feature_map), test=test)
    return get_dls(dsets, bs, None, num_workers)


# Cell
# saving hardcoded positioning so we can normalize the test set the same way
pos_min, pos_max, pos_mean, pos_std = (-998.400024, 1794.01276, 167.08153131830622, 244.90964319136026)

# Cell
class OpenMultFeatMap:
    def __init__(self, feature_map):
        self.fm = feature_map
        self.tt = ToTensor()

    def get_feat(self, sop):
        return [torch.from_numpy(x) for x in self.fm[sop]]

    def __call__(self, item):
        if isinstance(item, (str, Path)): return self.fn(item)
        feats = zip(*[self.get_feat(sop) for sop in item])
        return tuple([torch.stack(col) for col in feats])

# Cell
def get_seutao_dls_meta(df, np_file, csv_file, bs=1, num_workers=8, grps=Meta.grps_stg1, test=False):
    print('loading features')
    features = np.load(str(np_file))
    prob_df = pd.read_csv(csv_file).set_index('filename')
    sops = [f.replace('.dcm', '') for f in prob_df.index.values]

    preds = prob_df.values.astype(features.dtype)
    pos = df.loc[sops].ImagePositionPatient2.values.reshape(-1, 1).astype(features.dtype)
    pos_norm = (pos - pos_mean)/pos_std

    feature_map = dict(zip(sops, zip(features, preds, pos_norm)))
    print('Done loading features')

    dsets = get_3d_dsets(df, open_fn=OpenMultFeatMap(feature_map), grps=grps, test=test)
    return get_dls(dsets, bs, None, num_workers)


# Cell
class FlattenPred(Callback):
    def __init__(self): super().__init__()

    def after_pred(self):
        learn = self.learn
        learn.pred = learn.pred.view(-1, *learn.pred.shape[2:])

# Cell
def submit_predictions(learn, load_fn, sub_fn, message, dfunc=get_seutao_dls):
    df = Meta.df_tst
    learn.dls = dfunc(df, np_file_test, csv_file_test, bs=1, test=True)
    learn.load(load_fn)
    preds,targs = learn.get_preds()
    pred_csv = submission(df, preds, fn=sub_fn)
    api.competition_submit(f'{sub_fn}.csv', message, 'rsna-intracranial-hemorrhage-detection')
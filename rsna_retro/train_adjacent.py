# AUTOGENERATED! DO NOT EDIT! File to edit: 05_train_adjacent.ipynb (unless otherwise specified).

__all__ = ['TfmSlice', 'mean_5c', 'std_5c', 'mean_adj', 'std_adj', 'get_adj_data', 'get_adj_test_data']

# Cell
from .imports import *
from .metadata import *
from .preprocess import *
from .train import *
from .train3d import *

# Cell
class TfmSlice:
    def __init__(self, df, path, windowed=False, num_adj=1):
        self.fn = get_pil_fn(path)
        self.tt = ToTensor()
        self.df = df
        self.windowed = windowed
        self.num_adj = num_adj

    def get_adj(self, idx, x_mid, sid_mid):
        if idx < 0 or idx >= self.df.shape[0] \
        or  self.df.iloc[idx].SeriesInstanceUID != sid_mid:
            return torch.zeros_like(x_mid)
        adj_item = self.df.index[idx]
        return self.tt(self.fn(adj_item))

    def __call__(self, item):
        idx = self.df.index.get_loc(item)
        sid = self.df.loc[item].SeriesInstanceUID
        x = self.tt(self.fn(item))
        x_prevs, x_nexts = [], []
        for i in range(1, self.num_adj+1):
            x_prevs.append(self.get_adj(idx-i, x, sid)[:1])
            x_nexts.append(self.get_adj(idx+i, x, sid)[:1])
        x = x if self.windowed else x[:1]

        return TensorCTScan(torch.cat([*x_prevs, x, *x_nexts]))

# Cell
mean_5c = [mean[0], *mean, mean[0]]
std_5c = [std[0], *std, std[0]]

mean_adj = [mean[0]]*3
std_adj = [std[0]]*3

# Cell
def get_adj_data(bs, sz, splits, img_dir=path_jpg256, windowed=False, num_adj=1, df=Meta.df_comb, test=False):
    tfm = TfmSlice(df, img_dir, windowed=windowed, num_adj=num_adj)
    num_c = (1+2*num_adj)
    mean,std = ([mean[0]]*num_c, [std[0]]*num_c) if windowed else (mean_5c, std_5c)
    return get_data_gen(L(list(df.index)), bs=bs, img_tfm=tfm, sz=sz, splits=splits,
                       mean=mean, std=std, test=test)

# Cell
def get_adj_test_data(bs=512, sz=256, tst_dir='tst_jpg', windowed=False):
    tst_fns = Meta.df_tst.index.values
    tst_splits = [L.range(tst_fns), L.range(tst_fns)]
    tst_dbch = get_adj_data(bs, sz, tst_splits, path/tst_dir, df=Meta.df_tst, windowed=windowed, test=True)
#     tst_dbch = get_data_gen(tst_fns, bs=bs, img_tfm=get_pil_fn(path/tst_dir), sz=sz, splits=tst_splits, test=True)
    tst_dbch.c = 6
    return tst_dbch
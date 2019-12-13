#AUTOGENERATED! DO NOT EDIT! File to edit: dev/05_train_slice.ipynb (unless otherwise specified).

__all__ = ['OpenCTs', 'pad_batch', 'TfmSlice', 'TfmSlice', 'get_3d_dsrc']

#Cell
class OpenCTs:
    def __init__(self, path):
        self.fn = get_pil_fn(path)
        self.tt = ToTensor()

    def __call__(self, item):
        if isinstance(item, (str, Path)): return self.fn(item)
        xs = [self.tt(self.fn(x)) for x in item]
        return TensorCTScan(torch.stack(xs))

#Cell
def pad_batch(x, pad_to=None, value=0):
    bs_pad = pad_to-x.shape[0]
    pad = [0]*len(x.shape)*2
    pad[-1] = bs_pad
    return F.pad(x, pad=pad, value=value)

#Cell
class TfmSlice:
    def __init__(self,df,open_fn):
        self.open_fn = open_fn
        self.df = df

    def x(self, sid):
        sids = self.df.SOPInstanceUID[sid].values
        x = self.open_fn(sids)
        if self.pad_to is None: return x
        t = type(x)
        return t(pad_batch(x, pad_to=self.pad_to))

    def y(self, sid):
        vals = self.df.loc[sid,htypes].values
        return TensorMultiCategory(vals).float()

#Cell
class TfmSlice:
    def __init__(self, df, path):
        self.fn = get_pil_fn(path)
        self.tt = ToTensor()
        self.df = df
    def __call__(self, item):
        idx = self.df.iloc[item]
        prev = self.df
        if isinstance(item, (str, Path)): return self.fn(item)
        xs = [self.tt(self.fn(x)) for x in item]
        return TensorCTScan(torch.stack(xs))

#Cell
def get_3d_dsrc(df, open_fn, grps=Meta.grps, cv_idx=0, splits=Meta.splits_any):
    df_series = df.sort_values(['SeriesInstanceUID', "ImagePositionPatient2"])
    tfm = TfmSOP(df_series, open_fn, pad_to)
    sids = df_series.index.unique()

    s1 = np.where(np.in1d(sids, group_cv(cv_idx,grps)))[0]
    s2 = np.where(np.in1d(sids, grps[cv_idx]))[0]
    dsrc = DataSource(sids, [[tfm.x],[fn2label,EncodedMultiCategorize(htypes)]], splits=splits)
    return dsrc
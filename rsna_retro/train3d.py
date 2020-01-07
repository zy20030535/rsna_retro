#AUTOGENERATED! DO NOT EDIT! File to edit: dev/03_train3d.ipynb (unless otherwise specified).

__all__ = ['OpenCTs', 'pad_batch', 'pad_collate', 'TfmSOP', 'get_3d_dsrc', 'get_dbunch', 'get_3d_dbunch', 'get_np_fn',
           'OpenFeats', 'get_3d_dbunch_feat', 'ReshapeBodyHook', 'conv3', 'Batchify', 'DeBatchify', 'get_3d_head',
           'DePadLoss']

#Cell
from .imports import *
from .metadata import *
from .preprocess import *
from .train import *

#Cell
class OpenCTs:
    def __init__(self, path):
        self.fn = get_pil_fn(path)
        self.tt = ToTensor()
    def __call__(self, item):
        if isinstance(item, (str, Path)): return self.fn(item)
        xs = [self.tt(self.fn(x)) for x in item]
        xs
        return TensorCTScan(torch.stack(xs))

#Cell
def pad_batch(x, pad_to=None, value=0):
    if isinstance(x, tuple): return tuple([pad_batch(s, pad_to, value) for s in x])
    bs_pad = pad_to-x.shape[0]
    pad = [0]*len(x.shape)*2
    pad[-1] = bs_pad
    return F.pad(x, pad=pad, value=value)

def pad_collate(items, values=[0,-1]):
    pad_to = max([x[1].shape[0] for x in items])
    def pad_row(row, pad_to, vals): return tuple([pad_batch(x,pad_to,v) for x,v in zip(row,vals)])
    return [pad_row(row, pad_to, values) for row in items]

#Cell
class TfmSOP:
    def __init__(self,df,open_fn):
        self.open_fn = open_fn
        self.df = df

    def x(self, sid):
        sids = self.df.SOPInstanceUID[sid].values
        return self.open_fn(sids)

    def y(self, sid):
        vals = self.df.loc[sid,htypes].values
        return TensorMultiCategory(tensor(vals)).float()

#Cell
def get_3d_dsrc(df, open_fn, grps=Meta.grps, cv_idx=0, column='SeriesInstanceUID', test=False):
    df_series = df.reset_index().set_index(column).sort_values([column, "ImagePositionPatient2"])
    sids = df_series.index.unique()
    sid2idx = dict(zip(sids, range(len(sids))))

    # multi index is 10x faster
    df_series.index = pd.MultiIndex.from_tuples(df_series.index.str.split('|').tolist())
    tfm = TfmSOP(df_series, open_fn)

    if test: return DataSource(sids, [[tfm.x]], splits=[L.range(sids), L.range(sids)])

    s1 = [sid2idx[sid] for sid in group_cv(cv_idx,grps) if sid in sid2idx]
    s2 = [sid2idx[sid] for sid in grps[cv_idx] if sid in sid2idx]
    dsrc = DataSource(sids, [[tfm.x],[tfm.y]], splits=(s1,s2))
    return dsrc

#Cell
def get_dbunch(dsrc, bs, batch_tfms, num_workers=8):
    dbunch = DataBunch(
        TfmdDL(dsrc.train, bs=bs, before_batch=[pad_collate], after_batch=batch_tfms, num_workers=num_workers, shuffle=True),
        TfmdDL(dsrc.valid, bs=bs, before_batch=[pad_collate], after_batch=batch_tfms, num_workers=num_workers)
    )
    dbunch.device = default_device()
    dbunch.c = 6
    return dbunch

#Cell
def get_3d_dbunch(df, path=path_jpg256, bs=1, num_workers=8):
    dsrc = get_3d_dsrc(df, open_fn=OpenCTs(path))

    nrm = Normalize.from_stats(mean,std)
    batch_tfms = L(nrm, Cuda(), IntToFloatTensor())

    return get_dbunch(dsrc, bs, batch_tfms, num_workers)


#Cell
def get_np_fn(p):
    def _f(fn): return torch.from_numpy(np.load(str(p/f'{fn}.npy')))
    return _f

#Cell
class OpenFeats:
    def __init__(self, path):
        self.fn = get_np_fn(path)
        self.tt = ToTensor()
    def __call__(self, item):
        if isinstance(item, (str, Path)): return self.fn(item)
        xs = [self.tt(self.fn(x)) for x in item]
        return TensorCTScan(torch.stack(xs))

#Cell
def get_3d_dbunch_feat(df, path=path/'features_256', bs=1, num_workers=8):
    dsrc = get_3d_dsrc(df, open_fn=OpenFeats(path))
    return get_dbunch(dsrc, bs, [Cuda()], num_workers)


#Cell
class ReshapeBodyHook():
    def __init__(self, body):
        super().__init__()
        body.register_forward_pre_hook(self.pre_hook)
        body.register_forward_hook(self.forward_hook)
        self.shape = None

    def pre_hook(self, module, input):
        x = input[0]
        self.shape = x.shape
        return (x.view(-1, *x.shape[2:]),)

    def forward_hook(self, module, input, x):
        return x.view(*self.shape[:2], *x.shape[1:])

#Cell
def conv3(ni,nf,stride=1):
    return ConvLayer(ni, nf, (5,3,3), stride=(1,stride,stride), ndim=3, padding=(2,1,1))

#Cell
class Batchify(Module):
    def forward(self, x): return x.transpose(1,2)

class DeBatchify(Module):
    def forward(self, x):
        x_t = x.transpose(1,2)
        x_c = x_t.contiguous().view(-1, *x_t.shape[2:])
        return x_c

def get_3d_head():
    m = nn.Sequential(Batchify(),
        conv3(512,256,2), # 8
        conv3(256,128,2), # 4
        conv3(128, 64,2), # 2
        DeBatchify(), nn.AdaptiveAvgPool2d(1), Flatten(), nn.Linear(64,6))
    init_cnn(m)
    return m

#Cell
class DePadLoss(Callback):
    def __init__(self, pad_idx=-1):
        super().__init__()
        store_attr(self, 'pad_idx')

    def after_pred(self):
        learn = self.learn
        targ = learn.yb[0].view(-1, *learn.yb[0].shape[2:])
        if targ.shape[0] != self.pred.shape[0]:
            pred = learn.pred.view(-1, *learn.pred.shape[2:])
        else: pred = learn.pred

        mask = targ[:,-1] != self.pad_idx

        learn.pred = pred[mask]
        learn.yb = (targ[mask],)
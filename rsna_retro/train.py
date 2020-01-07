#AUTOGENERATED! DO NOT EDIT! File to edit: dev/02_train.ipynb (unless otherwise specified).

__all__ = ['get_pil_fn', 'fn2label', 'get_wgts', 'get_data_gen', 'filename', 'get_data', 'accuracy_any', 'get_loss',
           'get_learner', 'do_fit', 'get_test_data', 'submission', 'DummyLoss', 'save_features', 'path_feat256',
           'path_feat256_tst']

#Cell
from .imports import *
from .metadata import *
from .preprocess import *

#Cell
def get_pil_fn(p):
    def _f(fn): return PILCTScan.create(p/f'{fn}.jpg')
    return _f

#Cell
def fn2label(fn): return Meta.df_comb.loc[fn][htypes].values.astype(np.float32)

#Cell
def get_wgts(df, splits):
    wgts = df['any'][splits[0]].values
    return wgts * (1/0.14 - 2) + 1

#Cell
def get_data_gen(fns, bs, img_tfm, splits, sz=None, nw=8, mean=mean, std=std,
        wgts=None, batch_xtra=None, after_item=None, with_aug=True, test=False, **kwargs):
    tfms = [[img_tfm, ToTensor], [fn2label,EncodedMultiCategorize(htypes)]]
    if test: tfms = [tfms[0]]
    dsrc = DataSource(fns, tfms, splits=splits)
    nrm = Normalize.from_stats(mean,std)
    batch_tfms = L(IntToFloatTensor, nrm, Cuda()) + L(batch_xtra)
    if with_aug: batch_tfms += aug_transforms(**kwargs)
    if sz is not None:
        batch_tfms = batch_tfms+[RandomResizedCropGPU(sz, min_scale=0.7, ratio=(1.,1.), valid_scale=0.9)]
    if wgts is None:
        return dsrc.databunch(bs=bs, num_workers=nw, after_item=after_item, after_batch=batch_tfms)
    else:
        return dsrc.weighted_databunch(wgts, bs=bs, num_workers=nw, after_item=after_item, after_batch=batch_tfms)


#Cell
def filename(o): return os.path.splitext(os.path.basename(o))[0]

#Cell
def get_data(bs, sz, splits, img_dir=path_jpg256):
    return get_data_gen(L(list(Meta.df_comb.index)), bs=bs, img_tfm=get_pil_fn(path/img_dir),
                        sz=sz, splits=splits)

#Cell
def accuracy_any(inp, targ, thresh=0.5, sigmoid=True):
    inp,targ = flatten_check(inp[:,0],targ[:,0])
    if sigmoid: inp = inp.sigmoid()
    return ((inp>thresh)==targ.bool()).float().mean()


def get_loss(scale=None):
    num_classes = 6
    loss_weights = to_device(tensor(2.0, 1, 1, 1, 1, 1))
    loss_weights = loss_weights/loss_weights.sum()*num_classes

    if scale is not None: scale = to_device(tensor([scale]*num_classes))
    return BaseLoss(nn.BCEWithLogitsLoss, weight=loss_weights, #pos_weight=scale,
                    floatify=True, flatten=False, is_2d=False, activation=torch.sigmoid)


#Cell
def get_learner(dbch, arch_or_model, lf=None, pretrained=False, opt_func=None, metrics=None, fp16=True, config=None):
    if lf is None: lf = get_loss()
    if metrics is None: metrics=[accuracy_multi,accuracy_any]
    if opt_func is None: opt_func = partial(Adam, wd=1e-5, eps=1e-4, sqr_mom=0.999)
    if isinstance(arch_or_model, nn.Module):
        learn = Learner(dbch, arch_or_model, loss_func=lf, lr=3e-3,
                    opt_func=opt_func, metrics=metrics)
    else:
        if config is None: config=dict(ps=0., lin_ftrs=[], concat_pool=False)
        learn = cnn_learner(dbch, arch_or_model, pretrained=pretrained, loss_func=lf, lr=3e-3,
                            opt_func=opt_func, metrics=metrics, config=config)
    return learn.to_fp16() if fp16 else learn

#Cell
def do_fit(learn, epochs, lr, freeze=False, do_slice=False, **kwargs):
    if do_slice: lr = slice(lr*3,lr)
    if freeze:
        learn.freeze()
        learn.fit_one_cycle(1, lr, div=2, div_final=1, pct_start=0.1)
    learn.unfreeze()
    learn.fit_one_cycle(epochs, lr, **kwargs)

#Cell
def get_test_data(df_tst, bs=512, sz=256, tst_dir='tst_jpg', sl=None):
    tst_fns = df_tst.index.values
    if sl is not None: tst_fns = tst_fns[sl]
    tst_splits = [L.range(tst_fns), L.range(tst_fns)]
    tst_dbch = get_data_gen(tst_fns, bs=bs, img_tfm=get_pil_fn(path/tst_dir), sz=sz, splits=tst_splits, test=True)
    tst_dbch.c = 6
    return tst_dbch

#Cell
def submission(df_tst, preds, fn='submission'):
    ids,labels = [],[]
    for idx,pred in zip(df_tst.index, preds):
        for i,label in enumerate(htypes):
            ids.append(f"{idx}_{label}")
            labels.append('{0:1.10f}'.format(pred[i].item()))
    df_csv = pd.DataFrame({'ID': ids, 'Label': labels})
    df_csv.to_csv(f'{fn}.csv', index=False)
    return df_csv

#Cell
class DummyLoss:
    def __call__(self, p, *t, **kwargs): return torch.tensor(0, device=p.device).float()

#Cell
def save_features(learn, feat_path):
    preds,targs = learn.get_preds(dl=learn.dbunch.valid_dl)
    val_ids = dbunch.valid_dl.dataset.items
    feat_path.mkdir(exist_ok=True)
    for idx,pred in progress_bar(zip(val_ids, preds), total=len(val_ids)):
        np.save(str(feat_path/f'{idx}'), pred.squeeze().numpy())

#Cell
path_feat256 = path/'features_512'
path_feat256_tst = path/'tst_features_512'
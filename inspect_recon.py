import xarray as xr
ds = xr.open_dataset(r'C:\Users\dce25\AppData\Local\Temp\recon_download\combined_recon.nc')
print('Variables:', list(ds.data_vars))
print('Dims:', dict(ds.sizes))
for v in ds.data_vars:
    print(f'  {v}: shape={ds[v].shape} dtype={ds[v].dtype}')

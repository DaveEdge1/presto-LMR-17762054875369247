import xarray as xr
import numpy as np
import os

SRC = r'C:\Users\dce25\AppData\Local\Temp\recon_download\combined_recon.nc'
DST = r'C:\Users\dce25\AppData\Local\Temp\recon_download\combined_recon_int16.nc'

ds = xr.open_dataset(SRC)

# int16 quantization: anomalies in Kelvin fit easily in [-32, +32] K with 0.001 K resolution.
# NetCDF automatically applies: value = packed * scale_factor + add_offset
SCALE = 0.001  # 0.001 K = 1 mK precision, plenty for climate anomalies
OFFSET = 0.0

encoding = {}
for v in ds.data_vars:
    data_min = float(ds[v].min())
    data_max = float(ds[v].max())
    print(f'{v}: min={data_min:.3f} max={data_max:.3f}')
    # Pick scale so [min,max] fits inside int16 range [-32767, 32767] with headroom.
    # Use 0.01 for wide-range fields (tas has outliers ±100), 0.0001 for narrow-range (tas_gm).
    rng = max(abs(data_min), abs(data_max))
    scale = 0.0001 if rng < 5 else 0.01
    encoding[v] = {
        'zlib': True,
        'complevel': 5,
        'shuffle': True,
        'dtype': 'int16',
        'scale_factor': scale,
        'add_offset': 0.0,
        '_FillValue': np.int16(-32768),
    }
    print(f'  scale_factor={scale}, representable range +/-{scale*32767:.2f}')

ds.to_netcdf(DST, encoding=encoding)
ds.close()

src_mb = os.path.getsize(SRC) / (1024 * 1024)
dst_mb = os.path.getsize(DST) / (1024 * 1024)
print(f'{SRC}: {src_mb:.1f} MB')
print(f'{DST}: {dst_mb:.1f} MB  (ratio {src_mb/dst_mb:.1f}x)')

# Sanity-check round-trip precision
ds2 = xr.open_dataset(DST)
for v in ds2.data_vars:
    orig = xr.open_dataset(SRC)[v].values
    new  = ds2[v].values
    max_err = float(np.abs(orig - new).max())
    print(f'{v}: max round-trip error = {max_err:.6f}')

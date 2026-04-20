# CFR Column Name Requirements

## Problem
CFR expects DataFrame columns to follow the PAGES2k naming convention, not generic names.

## All Column Name Fixes Applied

### 1. Proxy ID Column
- **CFR expects:** `paleoData_pages2kID`
- **We had:** `pid`
- **Fixed in commit:** 0fd4425f8

### 2. Geographic Columns
- **CFR expects:** `geo_meanLat`, `geo_meanLon`, `geo_meanElev`
- **We had:** `lat`, `lon`, `elev`
- **Fixed in commit:** b0a6d811b

## Complete Required Column List

CFR requires these exact column names:

| Column Name | Description | Data Type |
|-------------|-------------|-----------|
| `paleoData_pages2kID` | Unique proxy identifier | string |
| `geo_meanLat` | Latitude (degrees) | float |
| `geo_meanLon` | Longitude (degrees, 0-360) | float |
| `geo_meanElev` | Elevation (meters) | float |
| `time` | Time values (years) | list/array |
| `value` | Proxy measurements | list/array |
| `ptype` | Proxy type (e.g., "coral.d18O") | string |
| `value_name` | Description of measurement | string |

## Current DataFrame Structure

After all fixes, our converted DataFrame has these columns:
```python
['paleoData_pages2kID', 'geo_meanLat', 'geo_meanLon', 'geo_meanElev',
 'time', 'value', 'ptype', 'value_name']
```

## Verification

You can verify the columns are correct by running:
```python
import pandas as pd
df = pd.read_pickle('lipd_cfr.pkl')
print(df.columns.tolist())
```

Expected output:
```
['paleoData_pages2kID', 'geo_meanLat', 'geo_meanLon', 'geo_meanElev',
 'time', 'value', 'ptype', 'value_name']
```

## Why These Names?

CFR was designed to work with PAGES2k data format. The column names follow the PAGES2k naming convention:
- `paleoData_pages2kID` - Standard identifier in PAGES2k datasets
- `geo_meanLat/Lon/Elev` - Geographic metadata prefix `geo_` with `mean` for averaged coordinates
- `ptype` - Proxy type in format "archive.measurement" (e.g., "coral.d18O")

## Testing Compatibility

Run the test script to verify compatibility:
```bash
python test_config_locally.py
```

All tests should pass with "[OK]" status.

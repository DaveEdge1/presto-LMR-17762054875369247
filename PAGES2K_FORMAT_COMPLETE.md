# Complete PAGES2k Format Specification

## Column Name Mappings - Final Fix

This document shows all the column name transformations needed for CFR compatibility.

### Generic → PAGES2k Column Mapping

| Generic Name | PAGES2k Name | Description | Required |
|--------------|--------------|-------------|----------|
| `pid` | `paleoData_pages2kID` | Unique proxy identifier | ✅ Yes |
| - | `dataSetName` | Dataset name (same as ID) | ✅ Yes |
| - | `archiveType` | Archive type (coral, tree, ice, etc.) | ✅ Yes |
| `lat` | `geo_meanLat` | Latitude in degrees | ✅ Yes |
| `lon` | `geo_meanLon` | Longitude in degrees (0-360) | ✅ Yes |
| `elev` | `geo_meanElev` | Elevation in meters | ✅ Yes |
| `time` | `year` | Time values (years) | ✅ Yes |
| `value` | `paleoData_values` | Proxy measurement values | ✅ Yes |
| - | `paleoData_variableName` | Measurement variable name | ✅ Yes |
| - | `paleoData_units` | Measurement units | ✅ Yes |
| - | `paleoData_proxy` | Proxy type name | ✅ Yes |
| `ptype` | `paleoData_ProxyObsType` | Combined archive.proxy format | ✅ Yes |

### Complete DataFrame Structure

After all fixes, the converted DataFrame has these 12 columns:

```python
[
    'paleoData_pages2kID',      # Unique proxy ID
    'dataSetName',              # Dataset name
    'archiveType',              # Archive type (coral, tree, etc.)
    'geo_meanLat',              # Latitude
    'geo_meanLon',              # Longitude
    'geo_meanElev',             # Elevation
    'year',                     # Time values
    'paleoData_values',         # Proxy measurements
    'paleoData_variableName',   # Variable name (d18O, TRW, etc.)
    'paleoData_units',          # Units (permil, mm, etc.)
    'paleoData_proxy',          # Proxy type
    'paleoData_ProxyObsType'    # Combined format (coral.d18O)
]
```

### Error Resolution Timeline

All KeyError exceptions resolved:

1. ✅ `KeyError: 'paleoData_pages2kID'` → Changed `pid` to `paleoData_pages2kID`
2. ✅ `KeyError: 'geo_meanLat'` → Changed `lat` to `geo_meanLat`
3. ✅ `KeyError: 'geo_meanLon'` → Changed `lon` to `geo_meanLon`
4. ✅ `KeyError: 'year'` → Changed `time` to `year` + added 6 more PAGES2k columns

### Sample Data Row

Example of a converted proxy record:

```python
{
    'paleoData_pages2kID': 'Ocn-Bermuda.DraschbaA.2000',
    'dataSetName': 'Ocn-Bermuda.DraschbaA.2000',
    'archiveType': 'coral',
    'geo_meanLat': 30.09,
    'geo_meanLon': 295.46,
    'geo_meanElev': 0.0,
    'year': [1856, 1857, ..., 1920],
    'paleoData_values': [-4.2, -4.3, ..., -4.1],
    'paleoData_variableName': 'd18O',
    'paleoData_units': 'permil',
    'paleoData_proxy': 'd18O',
    'paleoData_ProxyObsType': 'coral.d18O'
}
```

### Units Convention

The converter assigns units based on proxy type:
- **d18O or dD**: `'permil'` (per mil, ‰)
- **Others**: `'unknown'` (CFR may infer from proxy type)

Common units in PAGES2k:
- Temperature: degC
- Precipitation: mm
- Tree ring width: mm or relative units
- Isotopes: permil

### Filter Configuration

CFR filters proxies using `paleoData_ProxyObsType` which has the format:
```
{archiveType}.{proxyType}
```

Examples:
- `coral.d18O`
- `coral.SrCa`
- `tree.TRW`
- `ice.d18O`

The `filter_proxydb_kwargs` in `lmr_configs.yml` filters by archive type:
```yaml
filter_proxydb_kwargs:
  by: ptype
  keys:
  - coral
  - tree
  - ice
  - lake
  - bivalve
```

This matches against the archive type prefix (before the dot).

### Verification Commands

Check DataFrame structure:
```python
import pandas as pd
df = pd.read_pickle('lipd_cfr.pkl')

print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"Proxy types: {df['paleoData_ProxyObsType'].value_counts()}")
```

Test CFR loading:
```python
import cfr
pdb = cfr.ProxyDatabase().fetch('lipd_cfr.pkl')
print(f"Loaded {pdb.nrec} proxy records")
```

### References

- PAGES2k Consortium: https://www.pastglobalchanges.org/science/wg/2k-network
- CFR Package: https://github.com/fzhu2e/cfr
- PAGES2k v2 Data Format: NetCDF with specific variable naming conventions

## Commits Applied

```
5238fe66c Fix: Use complete PAGES2k column format systematically
b0a6d811b Fix: Use PAGES2k-style column names (geo_meanLat, geo_meanLon, geo_meanElev)
0fd4425f8 Fix: Use CFR's expected column name 'paleoData_pages2kID' instead of 'pid'
```

This systematic fix resolves all column name mismatches and provides complete PAGES2k format compatibility.

# GitHub Actions Workflow Fix Summary

## Problems Found and Fixed

### Problem 1: Missing proxydb_path Configuration ✓ FIXED
**Issue:** The `proxydb_path` was commented out in `lmr_configs.yml` (line 80), so CFR couldn't locate the custom proxy data even though the workflow was mounting it into the container.

**Fix:** Uncommented line 80 in `lmr_configs.yml`:
```yaml
proxydb_path: /app/lipd_cfr.pkl
```

### Problem 2: Pandas Version Incompatibility ✓ FIXED
**Issue:** The workflow was converting `lipd.pkl` to `lipd_cfr.pkl` on the GitHub Actions runner using pip-installed pandas, but then the Docker container (using conda-installed pandas) couldn't load the pickle file due to version incompatibility.

**Error Message:**
```
TypeError: StringDtype.__init__() takes from 1 to 2 positional arguments but 3 were given
TypeError: issubclass() arg 1 must be a class
```

**Root Cause:** Pandas pickle files are not portable across different pandas versions. The runner had pandas 2.2+ while the container likely has an older version.

**Fix:** Modified `.github/workflows/cfr-custom.yml` to:
1. **Removed** the conversion steps from the GitHub Actions runner (lines 59-80)
2. **Added** a new step to convert inside the Docker container before running the analysis

This ensures the pickle file is created and read using the **same pandas version** from the conda environment.

## Modified Files

### 1. lmr_configs.yml
```diff
- #proxydb_path: /app/lipd_cfr.pkl   # For custom data workflow
+ proxydb_path: /app/lipd_cfr.pkl   # For custom data workflow
```

### 2. .github/workflows/cfr-custom.yml
**Removed:** Steps that installed pandas on runner and converted there
**Added:** New step that converts inside the Docker container

New workflow step:
```yaml
- name: Convert LiPD to CFR format inside container
  run: |
    echo "Converting LiPD pickle to CFR-compatible DataFrame inside container..."
    echo "This ensures pandas version compatibility!"
    docker run --rm \
      -v "${{ github.workspace }}/lipd.pkl":/app/lipd.pkl:ro \
      -v "${{ github.workspace }}/convert_lipd_to_cfr_dataframe.py":/app/convert_lipd_to_cfr_dataframe.py:ro \
      -v "${{ github.workspace }}":/output \
      -w /app \
      ${{ env.IMAGE_NAME }} \
      conda run -n cfr-env python convert_lipd_to_cfr_dataframe.py lipd.pkl /output/lipd_cfr.pkl
```

### 3. convert_lipd_to_cfr_dataframe.py
- Fixed Windows encoding issues (replaced Unicode checkmarks with [OK]/[SKIP])
- Added pickle protocol 4 for better compatibility (though not the main fix)

## How the Fixed Workflow Works

1. **Checkout repository** - Gets all code and config files
2. **Extract LiPD URL** - Reads `lipd_data_url` from `lmr_configs.yml`
3. **Download LiPD data** - Downloads raw `lipd.pkl` from GitHub
4. **Setup swap space** - Adds 5GB swap for memory-intensive operations
5. **Pull Docker image** - Gets the latest `davidedge/lmr2:latest` image
6. **Create output directory** - Makes `./recons/` for results
7. **Convert inside container** ✨ NEW - Converts `lipd.pkl` → `lipd_cfr.pkl` using the container's pandas version
8. **Run CFR analysis** - Mounts `lipd_cfr.pkl` at `/app/lipd_cfr.pkl` (where `proxydb_path` points)
9. **Upload artifacts** - Saves results and converted data
10. **Commit results** - Optionally commits to repo

## Key Insights

### Why This Fix Works

1. **Version Consistency:** By running the conversion inside the same container that will use the data, we ensure pandas versions match perfectly.

2. **Pickle Compatibility:** Pandas pickle format changes between versions. Even with `protocol=4`, the internal representation of dtypes (like `StringDtype`) can be incompatible.

3. **Isolation:** The container's conda environment has specific package versions optimized for CFR. We now use those same versions for all data processing.

## Testing

### Local Testing (if Docker is available)
```bash
# Test the conversion inside container
docker pull davidedge/lmr2:latest
docker run --rm \
  -v "$(pwd)/lipd.pkl":/app/lipd.pkl:ro \
  -v "$(pwd)/convert_lipd_to_cfr_dataframe.py":/app/convert_lipd_to_cfr_dataframe.py:ro \
  -v "$(pwd)":/output \
  -w /app \
  davidedge/lmr2:latest \
  conda run -n cfr-env python convert_lipd_to_cfr_dataframe.py lipd.pkl /output/lipd_cfr.pkl
```

### Configuration Validation
```bash
# Test config without Docker
python test_config_locally.py
```

## Next Steps

1. **Commit all changes:**
   ```bash
   git add lmr_configs.yml .github/workflows/cfr-custom.yml convert_lipd_to_cfr_dataframe.py
   git commit -m "Fix: Resolve pandas version incompatibility and enable custom proxy data"
   git push
   ```

2. **Monitor GitHub Actions:** The workflow will trigger on push and should now complete successfully.

3. **Check artifacts:** After successful run, download the `cfr-custom-results-*` artifact to verify results.

## Expected Behavior

After these fixes:
- ✅ CFR will find the proxy data at `/app/lipd_cfr.pkl`
- ✅ The pickle file will be readable by the container's pandas version
- ✅ Analysis will run with 64 coral proxies (63 d18O + 1 temperature)
- ✅ Results will be saved to `./recons/` directory
- ✅ Artifacts will be uploaded for download

## Troubleshooting

If issues persist, check:
1. Docker image has latest code: `docker pull davidedge/lmr2:latest`
2. Config file is properly formatted YAML (no tabs, correct indentation)
3. GitHub Actions logs for specific error messages
4. Mounted file permissions (should be readable)

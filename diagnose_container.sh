#!/bin/bash
# Diagnostic script to check what's inside the container and if data is accessible

IMAGE_NAME="davidedge/lmr2:latest"
WORKSPACE=$(pwd)

echo "============================================"
echo "Container Diagnostics"
echo "============================================"
echo ""

echo "1. Checking if lipd_cfr.pkl exists locally..."
if [ -f "${WORKSPACE}/lipd_cfr.pkl" ]; then
    echo "✓ lipd_cfr.pkl exists"
    ls -lh "${WORKSPACE}/lipd_cfr.pkl"
else
    echo "✗ lipd_cfr.pkl NOT FOUND - need to run conversion first"
    exit 1
fi
echo ""

echo "2. Pulling latest Docker image..."
docker pull $IMAGE_NAME
echo ""

echo "3. Testing file mounts and CFR configuration in container..."
docker run --rm \
  -v "${WORKSPACE}/lipd_cfr.pkl":/app/lipd_cfr.pkl:ro \
  -v "${WORKSPACE}/lmr_configs.yml":/app/lmr_configs.yml:ro \
  -w /app \
  $IMAGE_NAME \
  bash -c "
    echo '--- Mounted files check ---'
    ls -lh /app/lipd_cfr.pkl 2>&1 || echo 'ERROR: lipd_cfr.pkl not found in container'
    ls -lh /app/lmr_configs.yml 2>&1 || echo 'ERROR: lmr_configs.yml not found in container'
    ls -lh /app/PAGES2kV2.nc 2>&1 || echo 'PAGES2kV2.nc not found (expected if using custom data)'
    echo ''

    echo '--- Config file content (proxydb_path section) ---'
    grep -A 2 'proxydb_path' /app/lmr_configs.yml || echo 'proxydb_path not found in config'
    echo ''

    echo '--- Testing Python/CFR environment ---'
    conda run -n cfr-env python -c '
import sys
import yaml
import pandas as pd
print(f\"Python: {sys.version}\")
print()

print(\"Loading config file...\")
with open(\"/app/lmr_configs.yml\", \"r\") as f:
    config = yaml.safe_load(f)

proxydb_path = config.get(\"proxydb_path\")
print(f\"proxydb_path in config: {proxydb_path}\")
print()

# Try to load the lipd_cfr.pkl file
print(\"Attempting to load /app/lipd_cfr.pkl...\")
try:
    df = pd.read_pickle(\"/app/lipd_cfr.pkl\")
    print(f\"✓ Successfully loaded DataFrame\")
    print(f\"  Shape: {df.shape}\")
    print(f\"  Columns: {list(df.columns)}\")
    if \"ptype\" in df.columns:
        print(f\"  Proxy types: {df[\\\"ptype\\\"].value_counts().to_dict()}\")
except Exception as e:
    print(f\"✗ Failed to load lipd_cfr.pkl: {e}\")
    import traceback
    traceback.print_exc()
print()

# Try to import and use CFR
print(\"Testing CFR import and ProxyDatabase...\")
try:
    import cfr
    print(f\"✓ CFR version: {cfr.__version__}\")

    # Check if proxydb_path is set
    if proxydb_path:
        print(f\"  Attempting to load proxy database from: {proxydb_path}\")
        pdb = cfr.ProxyDatabase().fetch(proxydb_path)
        print(f\"  ✓ Loaded {pdb.nrec} proxy records\")
    else:
        print(\"  ⚠ proxydb_path not configured in lmr_configs.yml\")
        print(\"  This is likely the issue - CFR doesn\\'t know where to find the data\")

except Exception as e:
    print(f\"✗ CFR error: {e}\")
    import traceback
    traceback.print_exc()
'
    echo ''
    echo '=== Diagnostics complete ==='
  "

echo ""
echo "============================================"
echo "Diagnostics complete!"
echo "============================================"

#!/bin/bash
# Local replication of the GitHub Actions CFR workflow for debugging
# This script mimics the steps in .github/workflows/cfr-custom.yml

set -e  # Exit on error

echo "============================================"
echo "Local CFR Workflow Debugging Script"
echo "============================================"
echo ""

# Configuration
IMAGE_NAME="davidedge/lmr2:latest"
WORKSPACE=$(pwd)

echo "Working directory: $WORKSPACE"
echo ""

# Step 1: Extract LiPD data URL from config
echo "Step 1: Extracting LiPD data URL from lmr_configs.yml..."
LIPD_URL=$(python -c "
import yaml
with open('lmr_configs.yml', 'r') as f:
    config = yaml.safe_load(f)
print(config.get('lipd_data_url', ''))
")

if [ -z "$LIPD_URL" ]; then
  echo "ERROR: lipd_data_url not found in lmr_configs.yml"
  exit 1
fi

echo "LiPD data URL: $LIPD_URL"
echo ""

# Step 2: Download LiPD pickle file
echo "Step 2: Downloading LiPD data..."
curl -L -o "${WORKSPACE}/lipd.pkl" "$LIPD_URL"

echo "Verifying downloaded file:"
ls -lh "${WORKSPACE}/lipd.pkl"

# Check file is not empty
if [ ! -s "${WORKSPACE}/lipd.pkl" ]; then
  echo "ERROR: Downloaded file is empty"
  exit 1
fi
echo ""

# Step 3: Convert LiPD to CFR DataFrame format
echo "Step 3: Converting LiPD pickle to CFR-compatible DataFrame..."
python convert_lipd_to_cfr_dataframe.py lipd.pkl lipd_cfr.pkl

echo ""
echo "Conversion complete! Verifying output:"
ls -lh lipd_cfr.pkl

# Verify the converted file can be loaded
python -c "
import pandas as pd
df = pd.read_pickle('lipd_cfr.pkl')
print(f'✓ DataFrame loaded successfully: {df.shape[0]} proxies')
print(f'✓ Columns: {list(df.columns)}')
print(f'✓ Proxy types: {df[\"ptype\"].value_counts().to_dict()}')
"
echo ""

# Step 4: Pull Docker image
echo "Step 4: Pulling Docker image..."
docker pull $IMAGE_NAME
echo ""

# Step 5: Create output directory
echo "Step 5: Creating output directory..."
mkdir -p ./recons
echo ""

# Step 6: Run CFR analysis with custom data
echo "Step 6: Running CFR analysis with converted LiPD data..."
echo ""
echo "Docker command to be executed:"
echo "docker run --rm \\"
echo "  -v \"${WORKSPACE}/lipd_cfr.pkl\":/app/lipd_cfr.pkl:ro \\"
echo "  -v \"${WORKSPACE}/cfr_main_code.py\":/app/cfr_main_code.py:ro \\"
echo "  -v \"${WORKSPACE}/lmr_configs.yml\":/app/lmr_configs.yml:ro \\"
echo "  -v \"${WORKSPACE}/recons\":/app/recons \\"
echo "  -w /app \\"
echo "  $IMAGE_NAME \\"
echo "  conda run -n cfr-env python cfr_main_code.py"
echo ""

docker run --rm \
  -v "${WORKSPACE}/lipd_cfr.pkl":/app/lipd_cfr.pkl:ro \
  -v "${WORKSPACE}/cfr_main_code.py":/app/cfr_main_code.py:ro \
  -v "${WORKSPACE}/lmr_configs.yml":/app/lmr_configs.yml:ro \
  -v "${WORKSPACE}/recons":/app/recons \
  -w /app \
  $IMAGE_NAME \
  conda run -n cfr-env python cfr_main_code.py

echo ""
echo "============================================"
echo "Step 7: Listing output files..."
echo "============================================"
ls -lh ./recons/

echo ""
echo "============================================"
echo "Workflow completed successfully!"
echo "============================================"

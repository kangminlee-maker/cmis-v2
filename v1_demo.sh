#!/bin/bash
# UMIS v9 v1 Demo Script

echo "==================================================="
echo "UMIS v9 - structure_analysis v1 Demo"
echo "==================================================="
echo ""

# Run structure analysis
python3 -m umis_v9_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --output output/structure_result.json

echo ""
echo "==================================================="
echo "Demo Complete!"
echo "==================================================="

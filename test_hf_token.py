#!/usr/bin/env python3
"""
Quick test to verify HF_TOKEN is being loaded correctly
"""

import os
from app.core.config import settings

print("🔍 Environment Variable Check:")
print(f"HF_TOKEN from os.environ: {os.environ.get('HF_TOKEN', 'NOT SET')}")
print(f"HF_TOKEN from settings: {settings.HF_TOKEN}")

# Test direct environment loading
if os.environ.get('HF_TOKEN'):
    print("✅ HF_TOKEN found in environment")
else:
    print("❌ HF_TOKEN not found in environment")

if settings.HF_TOKEN:
    print("✅ HF_TOKEN found in settings")
    print(f"Token preview: {settings.HF_TOKEN[:10]}...")
else:
    print("❌ HF_TOKEN not found in settings")

#!/usr/bin/env bash
# Render.com build script
set -o errexit

cd backend
pip install --upgrade pip
pip install -r requirements.txt

# Audio presets papkasini yaratish
mkdir -p static/audio_presets

echo "✅ Build completed successfully!"

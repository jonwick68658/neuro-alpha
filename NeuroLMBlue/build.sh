#!/bin/bash
# Container size optimization script for deployment
# Cleans cache and temporary files to reduce container size

echo "Starting container optimization..."

# Remove Python cache files
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true
find . -name '*.pyo' -delete 2>/dev/null || true
find . -name '*.pyd' -delete 2>/dev/null || true

# Clean cache directories
rm -rf .cache/* 2>/dev/null || true
rm -rf /tmp/* 2>/dev/null || true
rm -rf /var/tmp/* 2>/dev/null || true

# Remove backup files
rm -rf *_backup/ 2>/dev/null || true
rm -rf *.bak 2>/dev/null || true

# Remove logs
rm -rf *.log 2>/dev/null || true
rm -rf logs/ 2>/dev/null || true

echo "Container optimization complete."
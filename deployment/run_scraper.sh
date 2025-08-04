#!/bin/bash
# Simple wrapper for running YouTube scraper

cd /opt/youtube_app
source venv/bin/activate
python src/scripts/youtube_collection_manager.py
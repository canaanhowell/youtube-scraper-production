#!/bin/bash
# Script to update all references from wget_youtube_scraper to youtube_app

echo "Updating references from wget_youtube_scraper to youtube_app..."

# Update deployment scripts
find . -name "*.sh" -type f -exec sed -i 's|/opt/youtube_app|/opt/youtube_app|g' {} \;

# Update Python files
find . -name "*.py" -type f -exec sed -i 's|wget_youtube_scraper|youtube_app|g' {} \;

# Update YAML files
find . -name "*.yml" -type f -exec sed -i 's|/opt/youtube_app|/opt/youtube_app|g' {} \;
find . -name "*.yaml" -type f -exec sed -i 's|/opt/youtube_app|/opt/youtube_app|g' {} \;

# Update documentation
find ./docs -name "*.md" -type f -exec sed -i 's|wget_youtube_scraper|youtube_app|g' {} \;
find ./docs -name "*.md" -type f -exec sed -i 's|wget-youtube-scraper|youtube-app|g' {} \;
find ./docs -name "*.md" -type f -exec sed -i 's|Wget YouTube Scraper|YouTube App|g' {} \;

# Update .env files
sed -i 's|/opt/youtube_app|/opt/youtube_app|g' .env.production 2>/dev/null || true
sed -i 's|/opt/youtube_app|/opt/youtube_app|g' .env 2>/dev/null || true

# Update README
sed -i 's|wget_youtube_scraper|youtube_app|g' README.md 2>/dev/null || true
sed -i 's|Wget YouTube Scraper|YouTube App|g' README.md 2>/dev/null || true

echo "Update complete!"
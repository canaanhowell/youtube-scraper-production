# YouTube Analytics Module

This module provides comprehensive analytics capabilities for YouTube data collected by the scraper.

## Structure

```
analytics/
├── metrics/              # Metrics calculation modules
│   ├── daily_metrics_unified.py    # Unified daily metrics calculator
│   └── keywords_interval_metrics.py # Interval metrics collector
├── aggregators/          # Data aggregation modules
│   ├── category_metrics_aggregator.py  # Category-level aggregation
│   └── category_daily_snapshots.py     # Daily snapshot generation
└── visualizers/          # Data visualization tools
    ├── category_metrics.py              # View category metrics
    ├── category_timeline.py             # Timeline visualization
    ├── youtube_categories.py            # Category overview
    ├── youtube_category_daily_snapshots.py  # Snapshot viewer
    └── youtube_keyword_metrics.py      # Keyword metrics viewer
```

## Features

### Metrics Calculation
- **Interval Metrics**: Tracks video counts and views over time periods
- **Daily Metrics**: Calculates velocity, acceleration, and growth rates
- **Time Windows**: Analyzes data over 7d, 30d, 90d, and 365d periods

### Category Aggregation
- Groups keywords into categories (AI chatbots, media generation, productivity, etc.)
- Calculates aggregate metrics across categories
- Tracks top-performing keywords within each category

### Visualization Tools
Run any visualization script to see formatted output:
```bash
python -m src.analytics.visualizers.category_metrics
python -m src.analytics.visualizers.youtube_keyword_metrics
```

## Usage

### Run All Analytics
```bash
python3 src/scripts/collectors/run_analytics.py
```

### Run Specific Tasks
```bash
python3 src/scripts/collectors/run_analytics.py --task interval    # Interval metrics only
python3 src/scripts/collectors/run_analytics.py --task daily       # Daily metrics only
python3 src/scripts/collectors/run_analytics.py --task aggregate   # Category aggregation only
python3 src/scripts/collectors/run_analytics.py --task snapshots   # Daily snapshots only
```

### Run Full Pipeline (Scraping + Analytics)
```bash
python3 src/scripts/collectors/run_full_pipeline.py
```

## Scheduling

Add to crontab for automated analytics:
```bash
# Run analytics every 2 hours
0 */2 * * * /opt/youtube_app/deployment/schedule_analytics.sh
```

## Configuration

Category mappings are defined in: `src/config/category_mapping.json`

## Data Flow

1. **Scraper** collects raw video data → `youtube_videos/{keyword}/videos/`
2. **Interval Metrics** processes video counts → `youtube_keywords/{keyword}/interval_metrics/`
3. **Daily Metrics** calculates trends → `youtube_keywords/{keyword}/daily_metrics/`
4. **Aggregators** combine by category → `youtube_categories/{category}/`
5. **Visualizers** display formatted results
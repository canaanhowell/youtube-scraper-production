#!/usr/bin/env python3
"""
Main entry point for YouTube analytics operations.

This script orchestrates various analytics tasks including:
- Interval metrics collection
- Daily metrics calculation
- Category aggregation
- Snapshot generation
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, 'logs/analytics.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_analytics_module(module_path, task_name):
    """Run an analytics module as a subprocess."""
    try:
        logger.info(f"Running {task_name}...")
        result = subprocess.run(
            [sys.executable, '-m', module_path],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            logger.info(f"✓ {task_name} completed")
            return True
        else:
            logger.error(f"✗ {task_name} failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run {task_name}: {e}", exc_info=True)
        return False


def run_analytics_pipeline(task='all'):
    """
    Run the complete analytics pipeline or specific tasks.
    
    Args:
        task: Which analytics task to run ('all', 'interval', 'daily', 'aggregate', 'snapshots')
    """
    try:
        logger.info(f"Starting analytics pipeline - Task: {task}")
        
        success = True
        
        if task in ['all', 'interval']:
            if not run_analytics_module('src.analytics.metrics.keywords_interval_metrics', 
                                       'Interval metrics collection'):
                success = False
        
        if task in ['all', 'daily']:
            if not run_analytics_module('src.analytics.metrics.daily_metrics_unified', 
                                       'Daily metrics calculation'):
                success = False
        
        if task in ['all', 'aggregate']:
            if not run_analytics_module('src.analytics.aggregators.category_metrics_aggregator', 
                                       'Category aggregation'):
                success = False
        
        if task in ['all', 'snapshots']:
            if not run_analytics_module('src.analytics.aggregators.category_daily_snapshots', 
                                       'Daily snapshots'):
                success = False
        
        if success:
            logger.info(f"Analytics pipeline completed successfully - Task: {task}")
        else:
            logger.error(f"Analytics pipeline completed with errors - Task: {task}")
            raise Exception("One or more analytics tasks failed")
        
    except Exception as e:
        logger.error(f"Analytics pipeline failed: {e}", exc_info=True)
        raise


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='YouTube Analytics Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Tasks:
  all        Run complete analytics pipeline (default)
  interval   Run interval metrics collection only
  daily      Run daily metrics calculation only
  aggregate  Run category aggregation only
  snapshots  Run daily snapshots only

Examples:
  python run_analytics.py                    # Run all analytics
  python run_analytics.py --task interval    # Run interval metrics only
  python run_analytics.py --task daily       # Run daily metrics only
        '''
    )
    
    parser.add_argument(
        '--task',
        choices=['all', 'interval', 'daily', 'aggregate', 'snapshots'],
        default='all',
        help='Which analytics task to run'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure logs directory exists
    Path(os.path.join(project_root, 'logs')).mkdir(exist_ok=True)
    
    # Run the analytics pipeline
    run_analytics_pipeline(args.task)


if __name__ == '__main__':
    main()
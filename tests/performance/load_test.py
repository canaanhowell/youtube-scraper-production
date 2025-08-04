"""
Load testing for YouTube scraper system

Tests system performance under various load conditions to ensure
it can handle 50+ keywords efficiently.
"""
import time
import statistics
import multiprocessing
import concurrent.futures
from typing import List, Dict, Tuple
import psutil
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scripts.youtube_scraper_production import YouTubeScraperProduction
from src.utils.firebase_client_enhanced import FirebaseClient
from src.utils.redis_client_enhanced import RedisClientEnhanced


class LoadTester:
    """Load testing framework for YouTube scraper"""
    
    def __init__(self):
        self.results = {
            'start_time': None,
            'end_time': None,
            'total_duration': 0,
            'keywords_tested': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'videos_collected': 0,
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'errors': []
        }
    
    def measure_single_keyword_performance(self, keyword: str) -> Dict:
        """Measure performance for scraping a single keyword"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        result = {
            'keyword': keyword,
            'start_time': start_time,
            'success': False,
            'videos_collected': 0,
            'error': None
        }
        
        try:
            scraper = YouTubeScraperProduction()
            scrape_result = scraper.scrape_keyword(keyword, max_videos=100)
            
            result['success'] = scrape_result.get('success', False)
            result['videos_collected'] = scrape_result.get('saved_to_firebase', 0)
            
        except Exception as e:
            result['error'] = str(e)
            self.results['errors'].append({
                'keyword': keyword,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        result['duration'] = end_time - start_time
        result['memory_delta'] = end_memory - start_memory
        result['cpu_percent'] = psutil.Process().cpu_percent(interval=0.1)
        
        return result
    
    def run_concurrent_load_test(self, keywords: List[str], max_workers: int = 5) -> Dict:
        """Run load test with concurrent keyword processing"""
        print(f"Starting concurrent load test with {len(keywords)} keywords, {max_workers} workers")
        
        self.results['start_time'] = datetime.utcnow()
        self.results['keywords_tested'] = len(keywords)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_keyword = {
                executor.submit(self.measure_single_keyword_performance, keyword): keyword 
                for keyword in keywords
            }
            
            for future in concurrent.futures.as_completed(future_to_keyword):
                keyword = future_to_keyword[future]
                try:
                    result = future.result()
                    self._process_result(result)
                except Exception as e:
                    print(f"Keyword {keyword} generated exception: {e}")
                    self.results['failed_scrapes'] += 1
        
        self.results['end_time'] = datetime.utcnow()
        self.results['total_duration'] = (
            self.results['end_time'] - self.results['start_time']
        ).total_seconds()
        
        return self._generate_report()
    
    def run_sequential_load_test(self, keywords: List[str]) -> Dict:
        """Run load test with sequential keyword processing (simulates VPN rotation)"""
        print(f"Starting sequential load test with {len(keywords)} keywords")
        
        self.results['start_time'] = datetime.utcnow()
        self.results['keywords_tested'] = len(keywords)
        
        for keyword in keywords:
            result = self.measure_single_keyword_performance(keyword)
            self._process_result(result)
            
            # Simulate VPN rotation delay
            time.sleep(2)
        
        self.results['end_time'] = datetime.utcnow()
        self.results['total_duration'] = (
            self.results['end_time'] - self.results['start_time']
        ).total_seconds()
        
        return self._generate_report()
    
    def _process_result(self, result: Dict):
        """Process individual test result"""
        if result['success']:
            self.results['successful_scrapes'] += 1
            self.results['videos_collected'] += result['videos_collected']
        else:
            self.results['failed_scrapes'] += 1
        
        self.results['response_times'].append(result['duration'])
        self.results['memory_usage'].append(result.get('memory_delta', 0))
        self.results['cpu_usage'].append(result.get('cpu_percent', 0))
    
    def _generate_report(self) -> Dict:
        """Generate performance report"""
        response_times = self.results['response_times']
        
        report = {
            'summary': {
                'total_keywords': self.results['keywords_tested'],
                'successful': self.results['successful_scrapes'],
                'failed': self.results['failed_scrapes'],
                'success_rate': (self.results['successful_scrapes'] / 
                               self.results['keywords_tested'] * 100 
                               if self.results['keywords_tested'] > 0 else 0),
                'total_videos': self.results['videos_collected'],
                'total_duration_seconds': self.results['total_duration'],
                'average_time_per_keyword': (self.results['total_duration'] / 
                                            self.results['keywords_tested'] 
                                            if self.results['keywords_tested'] > 0 else 0)
            },
            'performance': {
                'response_times': {
                    'min': min(response_times) if response_times else 0,
                    'max': max(response_times) if response_times else 0,
                    'mean': statistics.mean(response_times) if response_times else 0,
                    'median': statistics.median(response_times) if response_times else 0,
                    'p95': self._percentile(response_times, 95) if response_times else 0,
                    'p99': self._percentile(response_times, 99) if response_times else 0
                },
                'memory': {
                    'max_delta_mb': max(self.results['memory_usage']) if self.results['memory_usage'] else 0,
                    'avg_delta_mb': statistics.mean(self.results['memory_usage']) if self.results['memory_usage'] else 0
                },
                'cpu': {
                    'max_percent': max(self.results['cpu_usage']) if self.results['cpu_usage'] else 0,
                    'avg_percent': statistics.mean(self.results['cpu_usage']) if self.results['cpu_usage'] else 0
                }
            },
            'errors': self.results['errors'],
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on test results"""
        recommendations = []
        
        # Check success rate
        success_rate = (self.results['successful_scrapes'] / 
                       self.results['keywords_tested'] * 100 
                       if self.results['keywords_tested'] > 0 else 0)
        
        if success_rate < 95:
            recommendations.append(
                f"Success rate is {success_rate:.1f}%. Consider improving error handling and retry logic."
            )
        
        # Check response times
        if self.results['response_times']:
            avg_time = statistics.mean(self.results['response_times'])
            if avg_time > 30:
                recommendations.append(
                    f"Average response time is {avg_time:.1f}s. Consider optimizing scraping logic."
                )
        
        # Check memory usage
        if self.results['memory_usage']:
            max_memory = max(self.results['memory_usage'])
            if max_memory > 100:  # MB
                recommendations.append(
                    f"High memory usage detected ({max_memory:.1f}MB). Check for memory leaks."
                )
        
        # Scale recommendations
        if self.results['keywords_tested'] >= 50:
            total_time = self.results['total_duration']
            if total_time > 1200:  # 20 minutes
                recommendations.append(
                    f"Processing 50+ keywords took {total_time/60:.1f} minutes. "
                    "Consider implementing parallel processing where possible."
                )
        
        return recommendations


def run_load_tests():
    """Main function to run load tests"""
    tester = LoadTester()
    
    # Test keywords
    test_keywords = [
        'python programming', 'machine learning', 'api development',
        'docker containers', 'microservices', 'cloud computing',
        'data science', 'artificial intelligence', 'web development',
        'software engineering', 'devops', 'kubernetes', 'react js',
        'node js', 'golang', 'rust programming', 'typescript',
        'graphql', 'rest api', 'mongodb'
    ]
    
    print("="*60)
    print("YouTube Scraper Load Test")
    print("="*60)
    
    # Test 1: Sequential processing (simulates actual VPN rotation)
    print("\nTest 1: Sequential Processing (20 keywords)")
    sequential_report = tester.run_sequential_load_test(test_keywords[:20])
    
    print("\nSequential Test Results:")
    print(f"Success Rate: {sequential_report['summary']['success_rate']:.1f}%")
    print(f"Total Duration: {sequential_report['summary']['total_duration_seconds']:.1f}s")
    print(f"Avg Time/Keyword: {sequential_report['summary']['average_time_per_keyword']:.1f}s")
    print(f"Total Videos: {sequential_report['summary']['total_videos']}")
    
    # Reset for next test
    tester = LoadTester()
    
    # Test 2: Concurrent processing (stress test)
    print("\nTest 2: Concurrent Processing (10 keywords, 3 workers)")
    concurrent_report = tester.run_concurrent_load_test(test_keywords[:10], max_workers=3)
    
    print("\nConcurrent Test Results:")
    print(f"Success Rate: {concurrent_report['summary']['success_rate']:.1f}%")
    print(f"Total Duration: {concurrent_report['summary']['total_duration_seconds']:.1f}s")
    print(f"Avg Time/Keyword: {concurrent_report['summary']['average_time_per_keyword']:.1f}s")
    
    # Save detailed report
    report_path = Path(__file__).parent / 'reports' / f'load_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump({
            'sequential_test': sequential_report,
            'concurrent_test': concurrent_report
        }, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Print recommendations
    print("\nRecommendations:")
    all_recommendations = set(
        sequential_report['recommendations'] + 
        concurrent_report['recommendations']
    )
    for i, rec in enumerate(all_recommendations, 1):
        print(f"{i}. {rec}")


if __name__ == "__main__":
    run_load_tests()
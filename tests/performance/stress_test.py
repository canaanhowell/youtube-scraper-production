"""
Stress testing for YouTube scraper system

Tests system behavior under extreme conditions to find breaking points
and ensure graceful degradation.
"""
import time
import threading
import queue
import psutil
import gc
from typing import List, Dict
import sys
from pathlib import Path
from datetime import datetime
import json
import resource

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class StressTester:
    """Stress testing framework for YouTube scraper"""
    
    def __init__(self):
        self.results = {
            'tests': [],
            'system_limits': {},
            'breaking_points': {},
            'recovery_metrics': {}
        }
    
    def test_memory_stress(self, max_iterations: int = 1000) -> Dict:
        """Test system behavior under memory pressure"""
        print("Starting memory stress test...")
        
        test_result = {
            'test_name': 'memory_stress',
            'start_time': datetime.utcnow(),
            'iterations': 0,
            'peak_memory_mb': 0,
            'error': None
        }
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples = []
        
        try:
            # Simulate memory-intensive operations
            large_data = []
            for i in range(max_iterations):
                # Create large video data objects
                video_batch = []
                for j in range(100):
                    video_data = {
                        'id': f'stress_test_{i}_{j}',
                        'title': 'x' * 1000,  # 1KB title
                        'description': 'y' * 5000,  # 5KB description
                        'metadata': {'z' * 100: 'a' * 100 for _ in range(10)}
                    }
                    video_batch.append(video_data)
                
                large_data.append(video_batch)
                
                # Measure memory
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
                # Check if we're approaching limits
                if current_memory > 1024:  # 1GB threshold
                    print(f"Memory threshold reached at iteration {i}: {current_memory:.1f}MB")
                    break
                
                if i % 100 == 0:
                    print(f"Iteration {i}: Memory usage: {current_memory:.1f}MB")
                
                test_result['iterations'] = i + 1
        
        except MemoryError as e:
            test_result['error'] = f"MemoryError at iteration {test_result['iterations']}: {str(e)}"
        except Exception as e:
            test_result['error'] = f"Unexpected error: {str(e)}"
        
        # Cleanup and measure recovery
        del large_data
        gc.collect()
        time.sleep(2)
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        test_result['peak_memory_mb'] = max(memory_samples) if memory_samples else 0
        test_result['final_memory_mb'] = final_memory
        test_result['memory_recovered_mb'] = test_result['peak_memory_mb'] - final_memory
        test_result['end_time'] = datetime.utcnow()
        
        self.results['tests'].append(test_result)
        return test_result
    
    def test_concurrent_connections(self, max_connections: int = 100) -> Dict:
        """Test system behavior with many concurrent operations"""
        print("Starting concurrent connections stress test...")
        
        test_result = {
            'test_name': 'concurrent_connections',
            'start_time': datetime.utcnow(),
            'max_concurrent': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'errors': []
        }
        
        operation_queue = queue.Queue()
        results_queue = queue.Queue()
        active_threads = []
        
        def mock_scrape_operation(thread_id: int):
            """Simulate a scraping operation"""
            try:
                start_time = time.time()
                # Simulate network request and processing
                time.sleep(0.5)
                
                # Simulate some CPU work
                _ = sum(i * i for i in range(10000))
                
                duration = time.time() - start_time
                results_queue.put({
                    'thread_id': thread_id,
                    'success': True,
                    'duration': duration
                })
            except Exception as e:
                results_queue.put({
                    'thread_id': thread_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Launch threads
        for i in range(max_connections):
            thread = threading.Thread(target=mock_scrape_operation, args=(i,))
            thread.start()
            active_threads.append(thread)
            
            # Monitor active thread count
            active_count = len([t for t in active_threads if t.is_alive()])
            test_result['max_concurrent'] = max(test_result['max_concurrent'], active_count)
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.01)
        
        # Wait for all threads to complete
        for thread in active_threads:
            thread.join(timeout=30)
        
        # Collect results
        while not results_queue.empty():
            result = results_queue.get()
            if result['success']:
                test_result['successful_operations'] += 1
            else:
                test_result['failed_operations'] += 1
                test_result['errors'].append(result.get('error', 'Unknown error'))
        
        test_result['end_time'] = datetime.utcnow()
        self.results['tests'].append(test_result)
        return test_result
    
    def test_rate_limiting(self, requests_per_second: int = 50) -> Dict:
        """Test system behavior under rate limiting conditions"""
        print(f"Starting rate limiting test ({requests_per_second} req/s)...")
        
        test_result = {
            'test_name': 'rate_limiting',
            'start_time': datetime.utcnow(),
            'target_rps': requests_per_second,
            'actual_rps': 0,
            'total_requests': 0,
            'throttled_requests': 0,
            'duration_seconds': 10
        }
        
        request_times = []
        start_time = time.time()
        
        while time.time() - start_time < test_result['duration_seconds']:
            # Simulate rapid requests
            request_start = time.time()
            
            # Simulate API call (would be actual scraper call in production)
            time.sleep(0.01)  # Minimal processing time
            
            request_times.append(time.time())
            test_result['total_requests'] += 1
            
            # Calculate current rate
            recent_requests = [t for t in request_times if t > time.time() - 1]
            current_rate = len(recent_requests)
            
            # Simulate rate limiting
            if current_rate > requests_per_second:
                test_result['throttled_requests'] += 1
                time.sleep(0.1)  # Backoff
            
            # Maintain target rate
            expected_interval = 1.0 / requests_per_second
            actual_interval = time.time() - request_start
            if actual_interval < expected_interval:
                time.sleep(expected_interval - actual_interval)
        
        # Calculate actual RPS
        total_duration = time.time() - start_time
        test_result['actual_rps'] = test_result['total_requests'] / total_duration
        test_result['end_time'] = datetime.utcnow()
        
        self.results['tests'].append(test_result)
        return test_result
    
    def test_error_recovery(self, error_rate: float = 0.3) -> Dict:
        """Test system recovery from various error conditions"""
        print(f"Starting error recovery test (error rate: {error_rate*100}%)...")
        
        test_result = {
            'test_name': 'error_recovery',
            'start_time': datetime.utcnow(),
            'total_operations': 100,
            'induced_errors': 0,
            'recovered_errors': 0,
            'unrecovered_errors': 0,
            'recovery_times': []
        }
        
        import random
        
        for i in range(test_result['total_operations']):
            should_fail = random.random() < error_rate
            
            if should_fail:
                test_result['induced_errors'] += 1
                recovery_start = time.time()
                
                # Simulate different error types
                error_type = random.choice(['network', 'timeout', 'parse', 'auth'])
                
                # Simulate recovery attempts
                max_retries = 3
                recovered = False
                
                for retry in range(max_retries):
                    time.sleep(0.1 * (2 ** retry))  # Exponential backoff
                    
                    # Simulate recovery success rate
                    if random.random() > 0.3:  # 70% chance of recovery
                        recovered = True
                        recovery_time = time.time() - recovery_start
                        test_result['recovery_times'].append(recovery_time)
                        test_result['recovered_errors'] += 1
                        break
                
                if not recovered:
                    test_result['unrecovered_errors'] += 1
            
            # Small delay between operations
            time.sleep(0.05)
        
        # Calculate recovery metrics
        if test_result['recovery_times']:
            test_result['avg_recovery_time'] = sum(test_result['recovery_times']) / len(test_result['recovery_times'])
            test_result['max_recovery_time'] = max(test_result['recovery_times'])
        else:
            test_result['avg_recovery_time'] = 0
            test_result['max_recovery_time'] = 0
        
        test_result['recovery_rate'] = (test_result['recovered_errors'] / 
                                       test_result['induced_errors'] * 100 
                                       if test_result['induced_errors'] > 0 else 0)
        
        test_result['end_time'] = datetime.utcnow()
        self.results['tests'].append(test_result)
        return test_result
    
    def test_resource_limits(self) -> Dict:
        """Test system resource limits"""
        print("Testing system resource limits...")
        
        test_result = {
            'test_name': 'resource_limits',
            'cpu_cores': psutil.cpu_count(),
            'total_memory_gb': psutil.virtual_memory().total / (1024**3),
            'available_memory_gb': psutil.virtual_memory().available / (1024**3),
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'open_files_limit': resource.getrlimit(resource.RLIMIT_NOFILE)[0],
            'process_limit': resource.getrlimit(resource.RLIMIT_NPROC)[0]
        }
        
        self.results['system_limits'] = test_result
        return test_result
    
    def generate_stress_report(self) -> Dict:
        """Generate comprehensive stress test report"""
        report = {
            'summary': {
                'total_tests': len(self.results['tests']),
                'test_names': [t['test_name'] for t in self.results['tests']],
                'system_limits': self.results.get('system_limits', {})
            },
            'test_results': {},
            'recommendations': []
        }
        
        # Process each test result
        for test in self.results['tests']:
            test_name = test['test_name']
            
            if test_name == 'memory_stress':
                report['test_results']['memory'] = {
                    'peak_memory_mb': test.get('peak_memory_mb', 0),
                    'memory_recovered_mb': test.get('memory_recovered_mb', 0),
                    'iterations_before_limit': test.get('iterations', 0)
                }
                
                if test.get('peak_memory_mb', 0) > 512:
                    report['recommendations'].append(
                        "High memory usage detected. Implement memory-efficient data structures."
                    )
            
            elif test_name == 'concurrent_connections':
                report['test_results']['concurrency'] = {
                    'max_concurrent': test.get('max_concurrent', 0),
                    'success_rate': (test.get('successful_operations', 0) / 
                                   (test.get('successful_operations', 0) + 
                                    test.get('failed_operations', 1)) * 100)
                }
                
                if test.get('failed_operations', 0) > 0:
                    report['recommendations'].append(
                        "Connection failures detected under high concurrency. "
                        "Implement connection pooling and retry logic."
                    )
            
            elif test_name == 'rate_limiting':
                report['test_results']['rate_limiting'] = {
                    'target_rps': test.get('target_rps', 0),
                    'actual_rps': test.get('actual_rps', 0),
                    'throttled_percentage': (test.get('throttled_requests', 0) / 
                                           test.get('total_requests', 1) * 100)
                }
                
                if test.get('throttled_requests', 0) > test.get('total_requests', 0) * 0.1:
                    report['recommendations'].append(
                        "Significant rate limiting detected. Implement adaptive rate control."
                    )
            
            elif test_name == 'error_recovery':
                report['test_results']['error_recovery'] = {
                    'recovery_rate': test.get('recovery_rate', 0),
                    'avg_recovery_time': test.get('avg_recovery_time', 0),
                    'max_recovery_time': test.get('max_recovery_time', 0)
                }
                
                if test.get('recovery_rate', 0) < 90:
                    report['recommendations'].append(
                        "Low error recovery rate. Improve error handling and retry strategies."
                    )
        
        return report


def run_stress_tests():
    """Main function to run stress tests"""
    tester = StressTester()
    
    print("="*60)
    print("YouTube Scraper Stress Test Suite")
    print("="*60)
    
    # Test 1: System resource limits
    print("\nTest 1: System Resource Limits")
    resource_limits = tester.test_resource_limits()
    print(f"CPU Cores: {resource_limits['cpu_cores']}")
    print(f"Total Memory: {resource_limits['total_memory_gb']:.1f}GB")
    print(f"Available Memory: {resource_limits['available_memory_gb']:.1f}GB")
    
    # Test 2: Memory stress
    print("\nTest 2: Memory Stress Test")
    memory_result = tester.test_memory_stress(max_iterations=500)
    print(f"Peak Memory: {memory_result.get('peak_memory_mb', 0):.1f}MB")
    print(f"Memory Recovered: {memory_result.get('memory_recovered_mb', 0):.1f}MB")
    
    # Test 3: Concurrent connections
    print("\nTest 3: Concurrent Connections Test")
    concurrency_result = tester.test_concurrent_connections(max_connections=50)
    print(f"Max Concurrent: {concurrency_result['max_concurrent']}")
    print(f"Success Rate: {(concurrency_result['successful_operations'] / (concurrency_result['successful_operations'] + concurrency_result['failed_operations']) * 100):.1f}%")
    
    # Test 4: Rate limiting
    print("\nTest 4: Rate Limiting Test")
    rate_result = tester.test_rate_limiting(requests_per_second=30)
    print(f"Target RPS: {rate_result['target_rps']}")
    print(f"Actual RPS: {rate_result['actual_rps']:.1f}")
    print(f"Throttled: {rate_result['throttled_requests']}/{rate_result['total_requests']}")
    
    # Test 5: Error recovery
    print("\nTest 5: Error Recovery Test")
    recovery_result = tester.test_error_recovery(error_rate=0.3)
    print(f"Recovery Rate: {recovery_result['recovery_rate']:.1f}%")
    print(f"Avg Recovery Time: {recovery_result.get('avg_recovery_time', 0):.2f}s")
    
    # Generate and save report
    report = tester.generate_stress_report()
    
    report_path = Path(__file__).parent / 'reports' / f'stress_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Print recommendations
    print("\nRecommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")


if __name__ == "__main__":
    run_stress_tests()
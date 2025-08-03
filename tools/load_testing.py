#!/usr/bin/env python3
"""
Load testing framework for YouTube Scraper
Tests system performance under various load conditions and identifies bottlenecks
"""

import asyncio
import time
import json
import statistics
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import psutil
import subprocess
import threading
import requests


@dataclass
class LoadTestResult:
    """Represents results from a load test"""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    resource_usage: Dict[str, Any]
    errors: List[str]


@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    name: str
    description: str
    concurrent_users: int
    total_requests: int
    ramp_up_time: float  # seconds
    test_duration: float  # seconds
    target_function: str
    function_args: Dict[str, Any]
    assertions: List[Dict[str, Any]]


class ResourceMonitor:
    """Monitors system resources during load testing"""
    
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.monitoring = False
        self.data: List[Dict[str, Any]] = []
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start resource monitoring"""
        self.monitoring = True
        self.data = []
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self) -> Dict[str, Any]:
        """Stop monitoring and return summary"""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=5)
        
        if not self.data:
            return {}
        
        # Calculate statistics
        cpu_values = [d['cpu_percent'] for d in self.data]
        memory_values = [d['memory_percent'] for d in self.data]
        
        return {
            'duration': self.data[-1]['timestamp'] - self.data[0]['timestamp'],
            'samples': len(self.data),
            'cpu': {
                'avg': statistics.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'p95': self._percentile(cpu_values, 95)
            },
            'memory': {
                'avg': statistics.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'p95': self._percentile(memory_values, 95)
            }
        }
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                
                self.data.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available / 1024 / 1024  # MB
                })
                
                time.sleep(self.interval)
                
            except Exception:
                break
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class ScraperLoadTester:
    """Load testing specifically for YouTube scraper functionality"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)
        self.resource_monitor = ResourceMonitor()
    
    def test_keyword_scraping_load(self, keywords: List[str], concurrent_workers: int = 5) -> LoadTestResult:
        """Test scraping multiple keywords concurrently"""
        test_name = f"keyword_scraping_load_{concurrent_workers}_workers"
        start_time = datetime.now()
        
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        self.resource_monitor.start()
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
                # Submit all keyword scraping tasks
                future_to_keyword = {
                    executor.submit(self._scrape_keyword_mock, keyword): keyword 
                    for keyword in keywords
                }
                
                # Collect results
                for future in concurrent.futures.as_completed(future_to_keyword):
                    keyword = future_to_keyword[future]
                    
                    try:
                        result = future.result(timeout=60)  # 60 second timeout per keyword
                        response_times.append(result['duration'])
                        successful_requests += 1
                        
                    except Exception as e:
                        errors.append(f"Keyword '{keyword}': {str(e)}")
                        failed_requests += 1
        
        except Exception as e:
            errors.append(f"Executor error: {str(e)}")
        
        finally:
            resource_usage = self.resource_monitor.stop()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_requests = len(keywords)
        avg_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        p95_response_time = self._percentile(response_times, 95)
        p99_response_time = self._percentile(response_times, 99)
        requests_per_second = successful_requests / duration if duration > 0 else 0
        error_rate = (failed_requests / total_requests) * 100 if total_requests > 0 else 0
        
        return LoadTestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            resource_usage=resource_usage,
            errors=errors
        )
    
    def test_vpn_rotation_performance(self, rotation_count: int = 10) -> LoadTestResult:
        """Test VPN server rotation performance"""
        test_name = f"vpn_rotation_performance_{rotation_count}_rotations"
        start_time = datetime.now()
        
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        self.resource_monitor.start()
        
        try:
            for i in range(rotation_count):
                rotation_start = time.time()
                
                try:
                    # Mock VPN rotation - replace with actual VPN rotation logic
                    self._rotate_vpn_mock()
                    rotation_time = time.time() - rotation_start
                    response_times.append(rotation_time)
                    successful_requests += 1
                    
                except Exception as e:
                    errors.append(f"Rotation {i+1}: {str(e)}")
                    failed_requests += 1
        
        except Exception as e:
            errors.append(f"Test error: {str(e)}")
        
        finally:
            resource_usage = self.resource_monitor.stop()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_requests = rotation_count
        avg_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        p95_response_time = self._percentile(response_times, 95)
        p99_response_time = self._percentile(response_times, 99)
        requests_per_second = successful_requests / duration if duration > 0 else 0
        error_rate = (failed_requests / total_requests) * 100 if total_requests > 0 else 0
        
        return LoadTestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            resource_usage=resource_usage,
            errors=errors
        )
    
    def test_database_write_performance(self, batch_sizes: List[int] = [1, 10, 50, 100]) -> Dict[int, LoadTestResult]:
        """Test database write performance with different batch sizes"""
        results = {}
        
        for batch_size in batch_sizes:
            test_name = f"database_write_batch_{batch_size}"
            start_time = datetime.now()
            
            response_times = []
            errors = []
            successful_requests = 0
            failed_requests = 0
            
            self.resource_monitor.start()
            
            try:
                # Test 10 batches of each size
                for batch_num in range(10):
                    batch_start = time.time()
                    
                    try:
                        # Mock database write - replace with actual database logic
                        self._write_batch_mock(batch_size)
                        batch_time = time.time() - batch_start
                        response_times.append(batch_time)
                        successful_requests += 1
                        
                    except Exception as e:
                        errors.append(f"Batch {batch_num+1} (size {batch_size}): {str(e)}")
                        failed_requests += 1
            
            except Exception as e:
                errors.append(f"Batch size {batch_size} test error: {str(e)}")
            
            finally:
                resource_usage = self.resource_monitor.stop()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Calculate statistics
            total_requests = 10  # 10 batches
            avg_response_time = statistics.mean(response_times) if response_times else 0
            min_response_time = min(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            p95_response_time = self._percentile(response_times, 95)
            p99_response_time = self._percentile(response_times, 99)
            requests_per_second = successful_requests / duration if duration > 0 else 0
            error_rate = (failed_requests / total_requests) * 100 if total_requests > 0 else 0
            
            results[batch_size] = LoadTestResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                avg_response_time=avg_response_time,
                min_response_time=min_response_time,
                max_response_time=max_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                requests_per_second=requests_per_second,
                error_rate=error_rate,
                resource_usage=resource_usage,
                errors=errors
            )
        
        return results
    
    def _scrape_keyword_mock(self, keyword: str) -> Dict[str, Any]:
        """Mock keyword scraping for testing"""
        start_time = time.time()
        
        # Simulate scraping work
        time.sleep(0.5 + (hash(keyword) % 10) * 0.1)  # 0.5-1.4 seconds
        
        # Simulate occasional failures
        if hash(keyword) % 20 == 0:  # 5% failure rate
            raise Exception(f"Mock scraping failure for keyword: {keyword}")
        
        duration = time.time() - start_time
        
        return {
            'keyword': keyword,
            'duration': duration,
            'videos_found': hash(keyword) % 50 + 10,  # 10-59 videos
            'success': True
        }
    
    def _rotate_vpn_mock(self) -> Dict[str, Any]:
        """Mock VPN rotation for testing"""
        # Simulate VPN rotation time
        time.sleep(0.2 + (time.time() % 10) * 0.05)  # 0.2-0.7 seconds
        
        # Simulate occasional failures
        if int(time.time()) % 25 == 0:  # ~4% failure rate
            raise Exception("Mock VPN rotation failure")
        
        return {'success': True, 'new_ip': f"192.168.{int(time.time()) % 255}.{int(time.time() * 10) % 255}"}
    
    def _write_batch_mock(self, batch_size: int) -> Dict[str, Any]:
        """Mock database batch write for testing"""
        # Simulate write time proportional to batch size
        base_time = 0.01  # 10ms base
        time_per_item = 0.002  # 2ms per item
        total_time = base_time + (batch_size * time_per_item)
        
        time.sleep(total_time)
        
        # Simulate occasional failures for large batches
        if batch_size > 50 and int(time.time()) % 30 == 0:  # ~3% failure rate for large batches
            raise Exception(f"Mock database write failure for batch size {batch_size}")
        
        return {'batch_size': batch_size, 'success': True}
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class LoadTestReporter:
    """Generates load test reports"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, results: List[LoadTestResult]) -> str:
        """Generate comprehensive load test report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"load_test_report_{timestamp}.html"
        
        html_content = self._generate_html_report(results)
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        # Also save JSON data
        json_file = self.output_dir / f"load_test_data_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump([asdict(result) for result in results], f, indent=2, default=str)
        
        return str(report_file)
    
    def _generate_html_report(self, results: List[LoadTestResult]) -> str:
        """Generate HTML report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report - YouTube Scraper</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .test-result {{ border: 1px solid #ddd; margin: 15px 0; padding: 20px; border-radius: 5px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric h4 {{ margin: 0 0 10px 0; color: #495057; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .metric .unit {{ font-size: 14px; color: #6c757d; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .error {{ color: #dc3545; }}
        .resource-chart {{ margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .errors {{ background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Load Test Report - YouTube Scraper</h1>
        <p>Generated: {timestamp}</p>
        <p>Total Tests: {total_tests}</p>
    </div>
    
    {test_results_html}
    
    <div class="summary">
        <h2>Test Summary</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Duration (s)</th>
                <th>Requests</th>
                <th>Success Rate</th>
                <th>Avg Response Time (s)</th>
                <th>RPS</th>
                <th>P95 Response Time (s)</th>
            </tr>
            {summary_rows}
        </table>
    </div>
    
</body>
</html>
        """
        
        # Generate test results HTML
        test_results_html = ""
        summary_rows = ""
        
        for result in results:
            success_rate = ((result.successful_requests / result.total_requests) * 100) if result.total_requests > 0 else 0
            success_class = "success" if success_rate >= 95 else "warning" if success_rate >= 80 else "error"
            
            errors_html = ""
            if result.errors:
                errors_html = f"""
                <div class="errors">
                    <h4>Errors ({len(result.errors)}):</h4>
                    <ul>
                        {''.join(f'<li>{error}</li>' for error in result.errors[:10])}
                        {f'<li>... and {len(result.errors) - 10} more errors</li>' if len(result.errors) > 10 else ''}
                    </ul>
                </div>
                """
            
            resource_html = ""
            if result.resource_usage:
                cpu = result.resource_usage.get('cpu', {})
                memory = result.resource_usage.get('memory', {})
                resource_html = f"""
                <div class="resource-chart">
                    <h4>Resource Usage</h4>
                    <div class="metrics">
                        <div class="metric">
                            <h4>CPU Usage</h4>
                            <div class="value">{cpu.get('avg', 0):.1f}</div>
                            <div class="unit">% avg (max: {cpu.get('max', 0):.1f}%)</div>
                        </div>
                        <div class="metric">
                            <h4>Memory Usage</h4>
                            <div class="value">{memory.get('avg', 0):.1f}</div>
                            <div class="unit">% avg (max: {memory.get('max', 0):.1f}%)</div>
                        </div>
                    </div>
                </div>
                """
            
            test_results_html += f"""
            <div class="test-result">
                <h3>{result.test_name}</h3>
                <div class="metrics">
                    <div class="metric">
                        <h4>Total Requests</h4>
                        <div class="value">{result.total_requests}</div>
                    </div>
                    <div class="metric">
                        <h4>Success Rate</h4>
                        <div class="value {success_class}">{success_rate:.1f}</div>
                        <div class="unit">%</div>
                    </div>
                    <div class="metric">
                        <h4>Avg Response Time</h4>
                        <div class="value">{result.avg_response_time:.3f}</div>
                        <div class="unit">seconds</div>
                    </div>
                    <div class="metric">
                        <h4>Requests/Second</h4>
                        <div class="value">{result.requests_per_second:.2f}</div>
                    </div>
                    <div class="metric">
                        <h4>P95 Response Time</h4>
                        <div class="value">{result.p95_response_time:.3f}</div>
                        <div class="unit">seconds</div>
                    </div>
                    <div class="metric">
                        <h4>P99 Response Time</h4>
                        <div class="value">{result.p99_response_time:.3f}</div>
                        <div class="unit">seconds</div>
                    </div>
                </div>
                {resource_html}
                {errors_html}
            </div>
            """
            
            summary_rows += f"""
            <tr>
                <td>{result.test_name}</td>
                <td>{result.duration:.2f}</td>
                <td>{result.total_requests}</td>
                <td class="{success_class}">{success_rate:.1f}%</td>
                <td>{result.avg_response_time:.3f}</td>
                <td>{result.requests_per_second:.2f}</td>
                <td>{result.p95_response_time:.3f}</td>
            </tr>
            """
        
        return html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_tests=len(results),
            test_results_html=test_results_html,
            summary_rows=summary_rows
        )


class LoadTestSuite:
    """Complete load testing suite for YouTube Scraper"""
    
    def __init__(self, project_root: Path, output_dir: Path = None):
        self.project_root = project_root
        self.output_dir = output_dir or project_root / 'tools' / 'load_test_reports'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.tester = ScraperLoadTester(project_root)
        self.reporter = LoadTestReporter(self.output_dir)
        self.logger = logging.getLogger(__name__)
    
    def run_comprehensive_test_suite(self) -> str:
        """Run comprehensive load testing suite"""
        self.logger.info("Starting comprehensive load test suite...")
        
        results = []
        
        # Test 1: Keyword scraping under different loads
        self.logger.info("Testing keyword scraping performance...")
        
        test_keywords = [
            'tech startup', 'ai technology', 'python programming', 'web development',
            'machine learning', 'data science', 'cloud computing', 'cybersecurity',
            'blockchain', 'mobile app development'
        ]
        
        for workers in [1, 3, 5, 8]:
            result = self.tester.test_keyword_scraping_load(test_keywords, workers)
            results.append(result)
            self.logger.info(f"Completed keyword test with {workers} workers: "
                           f"{result.successful_requests}/{result.total_requests} successful")
        
        # Test 2: VPN rotation performance
        self.logger.info("Testing VPN rotation performance...")
        vpn_result = self.tester.test_vpn_rotation_performance(20)
        results.append(vpn_result)
        self.logger.info(f"VPN rotation test completed: "
                        f"{vpn_result.successful_requests}/{vpn_result.total_requests} successful")
        
        # Test 3: Database write performance
        self.logger.info("Testing database write performance...")
        db_results = self.tester.test_database_write_performance([1, 5, 10, 25, 50])
        results.extend(db_results.values())
        self.logger.info(f"Database write tests completed for {len(db_results)} batch sizes")
        
        # Generate report
        report_file = self.reporter.generate_report(results)
        self.logger.info(f"Load test suite completed. Report: {report_file}")
        
        # Print summary
        self._print_summary(results)
        
        return report_file
    
    def _print_summary(self, results: List[LoadTestResult]):
        """Print test summary to console"""
        print("\n" + "=" * 80)
        print("LOAD TEST SUMMARY")
        print("=" * 80)
        
        for result in results:
            success_rate = (result.successful_requests / result.total_requests) * 100 if result.total_requests > 0 else 0
            status = "✓" if success_rate >= 95 else "⚠" if success_rate >= 80 else "✗"
            
            print(f"{status} {result.test_name}")
            print(f"   Success Rate: {success_rate:.1f}% ({result.successful_requests}/{result.total_requests})")
            print(f"   Avg Response: {result.avg_response_time:.3f}s")
            print(f"   RPS: {result.requests_per_second:.2f}")
            if result.errors:
                print(f"   Errors: {len(result.errors)}")
            print()
        
        print("=" * 80)


def main():
    """CLI interface for load testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Scraper Load Testing')
    parser.add_argument('--project-root', type=Path, default=Path.cwd(),
                       help='Path to project root')
    parser.add_argument('--output-dir', type=Path,
                       help='Output directory for reports')
    parser.add_argument('--test-type', choices=['full', 'keywords', 'vpn', 'database'],
                       default='full', help='Type of test to run')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of concurrent workers for keyword tests')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    suite = LoadTestSuite(args.project_root, args.output_dir)
    
    if args.test_type == 'full':
        report_file = suite.run_comprehensive_test_suite()
        print(f"\nComplete load test report: {report_file}")
    
    elif args.test_type == 'keywords':
        keywords = ['test1', 'test2', 'test3', 'test4', 'test5']
        result = suite.tester.test_keyword_scraping_load(keywords, args.workers)
        report_file = suite.reporter.generate_report([result])
        print(f"\nKeyword test report: {report_file}")
    
    elif args.test_type == 'vpn':
        result = suite.tester.test_vpn_rotation_performance(10)
        report_file = suite.reporter.generate_report([result])
        print(f"\nVPN test report: {report_file}")
    
    elif args.test_type == 'database':
        results = suite.tester.test_database_write_performance([1, 10, 50])
        report_file = suite.reporter.generate_report(list(results.values()))
        print(f"\nDatabase test report: {report_file}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Performance profiling and optimization tools for YouTube Scraper
Provides detailed performance analysis, bottleneck detection, and optimization recommendations
"""

import time
import cProfile
import pstats
import io
import psutil
import json
import subprocess
import sys
from functools import wraps
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import memory_profiler
import line_profiler


@dataclass
class PerformanceMetric:
    """Represents a performance measurement"""
    name: str
    duration: float
    memory_usage: float
    cpu_usage: float
    timestamp: datetime
    metadata: Dict[str, Any]


class PerformanceProfiler:
    """Main performance profiling class"""
    
    def __init__(self, output_dir: str = "/opt/youtube_scraper/profiling"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: List[PerformanceMetric] = []
        self.active_profiles = {}
        
    def profile_function(self, include_memory: bool = True, include_line: bool = False):
        """Decorator to profile function performance"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self._profile_execution(
                    func, args, kwargs, include_memory, include_line
                )
            return wrapper
        return decorator
    
    def _profile_execution(self, func: Callable, args: tuple, kwargs: dict, 
                          include_memory: bool, include_line: bool) -> Any:
        """Execute function with profiling"""
        func_name = f"{func.__module__}.{func.__name__}"
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # CPU profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            # Memory profiling if requested
            if include_memory:
                result = self._memory_profile_function(func, args, kwargs)
            else:
                result = func(*args, **kwargs)
                
        finally:
            profiler.disable()
            
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        duration = end_time - start_time
        memory_delta = end_memory - start_memory
        
        # Save CPU profile
        cpu_profile_path = self.output_dir / f"{func_name}_{int(start_time)}.prof"
        profiler.dump_stats(str(cpu_profile_path))
        
        # Generate readable CPU report
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative').print_stats(20)
        cpu_report = s.getvalue()
        
        # Save readable report
        report_path = self.output_dir / f"{func_name}_{int(start_time)}.txt"
        with open(report_path, 'w') as f:
            f.write(f"Performance Profile for {func_name}\n")
            f.write(f"Execution Time: {duration:.4f} seconds\n")
            f.write(f"Memory Delta: {memory_delta:.2f} MB\n")
            f.write(f"Timestamp: {datetime.now()}\n\n")
            f.write("CPU Profile:\n")
            f.write(cpu_report)
        
        # Store metric
        metric = PerformanceMetric(
            name=func_name,
            duration=duration,
            memory_usage=memory_delta,
            cpu_usage=0,  # Would need more complex calculation
            timestamp=datetime.now(),
            metadata={
                'args_count': len(args),
                'kwargs_count': len(kwargs),
                'profile_file': str(cpu_profile_path),
                'report_file': str(report_path)
            }
        )
        self.metrics.append(metric)
        
        return result
    
    def _memory_profile_function(self, func: Callable, args: tuple, kwargs: dict) -> Any:
        """Profile function memory usage"""
        @memory_profiler.profile
        def profiled_func():
            return func(*args, **kwargs)
        
        return profiled_func()
    
    def profile_script(self, script_path: str, args: List[str] = None) -> Dict[str, Any]:
        """Profile an entire script execution"""
        args = args or []
        script_path = Path(script_path)
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        timestamp = int(time.time())
        profile_file = self.output_dir / f"script_{script_path.stem}_{timestamp}.prof"
        
        # Build command
        cmd = [
            sys.executable, '-m', 'cProfile', '-o', str(profile_file),
            str(script_path)
        ] + args
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Execute with profiling
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, 
                cwd=script_path.parent, timeout=3600
            )
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Analyze profile
            stats = pstats.Stats(str(profile_file))
            
            # Generate report
            report_data = {
                'script': str(script_path),
                'duration': end_time - start_time,
                'memory_delta': end_memory - start_memory,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'profile_file': str(profile_file),
                'top_functions': self._get_top_functions(stats, 10),
                'timestamp': datetime.now().isoformat()
            }
            
            # Save detailed report
            report_file = self.output_dir / f"script_{script_path.stem}_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            return report_data
            
        except subprocess.TimeoutExpired:
            return {
                'script': str(script_path),
                'error': 'Script execution timed out',
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_top_functions(self, stats: pstats.Stats, limit: int = 10) -> List[Dict[str, Any]]:
        """Extract top functions from profile stats"""
        stats.sort_stats('cumulative')
        
        top_functions = []
        for func_info in stats.get_stats().items()[:limit]:
            func_key, (call_count, reccall_count, total_time, cumulative_time) = func_info
            filename, line_num, func_name = func_key
            
            top_functions.append({
                'function': func_name,
                'filename': filename,
                'line_number': line_num,
                'call_count': call_count,
                'total_time': total_time,
                'cumulative_time': cumulative_time,
                'per_call_time': total_time / call_count if call_count > 0 else 0
            })
        
        return top_functions
    
    def benchmark_keywords(self, keyword_list: List[str], iterations: int = 3) -> Dict[str, Any]:
        """Benchmark scraping performance for different keywords"""
        results = {
            'total_keywords': len(keyword_list),
            'iterations': iterations,
            'results': [],
            'summary': {}
        }
        
        for keyword in keyword_list:
            keyword_results = []
            
            for iteration in range(iterations):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                # This would call your actual scraping function
                # For now, simulate with sleep
                time.sleep(0.1)  # Replace with actual scraping call
                
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                keyword_results.append({
                    'iteration': iteration + 1,
                    'duration': end_time - start_time,
                    'memory_delta': end_memory - start_memory
                })
            
            # Calculate statistics
            durations = [r['duration'] for r in keyword_results]
            memory_deltas = [r['memory_delta'] for r in keyword_results]
            
            keyword_summary = {
                'keyword': keyword,
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'avg_memory': sum(memory_deltas) / len(memory_deltas),
                'iterations': keyword_results
            }
            
            results['results'].append(keyword_summary)
        
        # Overall summary
        all_durations = [r['avg_duration'] for r in results['results']]
        results['summary'] = {
            'total_avg_duration': sum(all_durations) / len(all_durations),
            'fastest_keyword': min(results['results'], key=lambda x: x['avg_duration'])['keyword'],
            'slowest_keyword': max(results['results'], key=lambda x: x['avg_duration'])['keyword'],
            'estimated_total_time': sum(all_durations)
        }
        
        # Save results
        timestamp = int(time.time())
        benchmark_file = self.output_dir / f"keyword_benchmark_{timestamp}.json"
        with open(benchmark_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return results


class SystemResourceMonitor:
    """Monitors system resources during execution"""
    
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.monitoring = False
        self.data: List[Dict[str, Any]] = []
        self.thread: Optional[threading.Thread] = None
    
    def start_monitoring(self):
        """Start resource monitoring in background"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.data = []
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_monitoring(self) -> List[Dict[str, Any]]:
        """Stop monitoring and return collected data"""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=5)
        
        return self.data.copy()
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # CPU and memory for current process
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                
                # System-wide resources
                system_cpu = psutil.cpu_percent()
                system_memory = psutil.virtual_memory()
                
                data_point = {
                    'timestamp': time.time(),
                    'process': {
                        'cpu_percent': cpu_percent,
                        'memory_rss': memory_info.rss / 1024 / 1024,  # MB
                        'memory_vms': memory_info.vms / 1024 / 1024,  # MB
                    },
                    'system': {
                        'cpu_percent': system_cpu,
                        'memory_percent': system_memory.percent,
                        'memory_available': system_memory.available / 1024 / 1024,  # MB
                    }
                }
                
                self.data.append(data_point)
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"Error in monitoring: {e}")
                break


class PerformanceAnalyzer:
    """Analyzes performance data and provides recommendations"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
    
    def analyze_bottlenecks(self, profile_file: str) -> Dict[str, Any]:
        """Analyze profile data to identify bottlenecks"""
        stats = pstats.Stats(profile_file)
        
        # Get function statistics
        function_stats = []
        for func_info in stats.get_stats().items():
            func_key, (call_count, reccall_count, total_time, cumulative_time) = func_info
            filename, line_num, func_name = func_key
            
            function_stats.append({
                'function': func_name,
                'filename': filename,
                'total_time': total_time,
                'cumulative_time': cumulative_time,
                'call_count': call_count,
                'time_per_call': total_time / call_count if call_count > 0 else 0
            })
        
        # Sort by cumulative time to find bottlenecks
        function_stats.sort(key=lambda x: x['cumulative_time'], reverse=True)
        
        analysis = {
            'top_time_consumers': function_stats[:10],
            'high_call_count': sorted(function_stats, key=lambda x: x['call_count'], reverse=True)[:5],
            'slow_functions': sorted(function_stats, key=lambda x: x['time_per_call'], reverse=True)[:5]
        }
        
        return analysis
    
    def generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        # Check for slow functions
        if analysis['slow_functions']:
            slowest = analysis['slow_functions'][0]
            if slowest['time_per_call'] > 1.0:
                recommendations.append(
                    f"Optimize {slowest['function']}: {slowest['time_per_call']:.2f}s per call is very slow"
                )
        
        # Check for high call counts
        if analysis['high_call_count']:
            most_called = analysis['high_call_count'][0]
            if most_called['call_count'] > 10000:
                recommendations.append(
                    f"Consider caching for {most_called['function']}: called {most_called['call_count']} times"
                )
        
        # Check for time-consuming functions
        if analysis['top_time_consumers']:
            top_consumer = analysis['top_time_consumers'][0]
            if top_consumer['cumulative_time'] > 60:  # More than 1 minute
                recommendations.append(
                    f"Major bottleneck in {top_consumer['function']}: {top_consumer['cumulative_time']:.2f}s total"
                )
        
        return recommendations
    
    def create_performance_report(self, resource_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create comprehensive performance report"""
        if not resource_data:
            return {'error': 'No resource data available'}
        
        # Calculate statistics
        cpu_values = [d['process']['cpu_percent'] for d in resource_data]
        memory_values = [d['process']['memory_rss'] for d in resource_data]
        
        report = {
            'duration': resource_data[-1]['timestamp'] - resource_data[0]['timestamp'],
            'data_points': len(resource_data),
            'cpu_stats': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory_stats': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'peak_usage': max(memory_values)
            },
            'resource_efficiency': {
                'cpu_utilization': 'high' if max(cpu_values) > 80 else 'moderate' if max(cpu_values) > 50 else 'low',
                'memory_efficiency': 'high' if max(memory_values) < 500 else 'moderate' if max(memory_values) < 1000 else 'low'
            }
        }
        
        return report


def main():
    """Demo of profiling tools"""
    profiler = PerformanceProfiler()
    monitor = SystemResourceMonitor()
    analyzer = PerformanceAnalyzer(profiler)
    
    print("Performance Profiling Tools Demo")
    
    # Example: Profile a function
    @profiler.profile_function(include_memory=True)
    def example_function(n: int) -> int:
        """Example function to profile"""
        result = 0
        for i in range(n):
            result += i ** 2
        return result
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Run profiled function
    result = example_function(100000)
    
    # Stop monitoring
    resource_data = monitor.stop_monitoring()
    
    # Generate report
    performance_report = analyzer.create_performance_report(resource_data)
    
    print(f"Function result: {result}")
    print(f"Performance report: {performance_report}")
    print(f"Collected {len(profiler.metrics)} performance metrics")


if __name__ == "__main__":
    main()
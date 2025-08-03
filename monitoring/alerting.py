#!/usr/bin/env python3
"""
Advanced monitoring and alerting system for YouTube Scraper
Provides real-time metrics, health checks, and automated alerts
"""

import asyncio
import smtplib
import json
import time
import logging
import psutil
import subprocess
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests


@dataclass
class MetricThreshold:
    """Defines thresholds for monitoring metrics"""
    name: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str


@dataclass
class Alert:
    """Represents an alert condition"""
    severity: str  # info, warning, critical
    metric: str
    current_value: float
    threshold: float
    timestamp: datetime
    description: str
    node_id: str = "youtube-scraper-vm"


class SystemMetrics:
    """Collects system-level metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage statistics"""
        memory = psutil.virtual_memory()
        return {
            'used_percent': memory.percent,
            'used_gb': memory.used / (1024**3),
            'available_gb': memory.available / (1024**3),
            'total_gb': memory.total / (1024**3)
        }
    
    def get_disk_usage(self, path: str = '/') -> Dict[str, float]:
        """Get disk usage for specified path"""
        disk = psutil.disk_usage(path)
        return {
            'used_percent': (disk.used / disk.total) * 100,
            'used_gb': disk.used / (1024**3),
            'free_gb': disk.free / (1024**3),
            'total_gb': disk.total / (1024**3)
        }
    
    def get_network_stats(self) -> Dict[str, int]:
        """Get network I/O statistics"""
        net = psutil.net_io_counters()
        return {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv
        }
    
    def get_docker_stats(self) -> List[Dict[str, Any]]:
        """Get Docker container statistics"""
        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 
                 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            containers = []
            
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 5:
                    containers.append({
                        'name': parts[0],
                        'cpu_percent': parts[1].replace('%', ''),
                        'memory_usage': parts[2],
                        'network_io': parts[3],
                        'block_io': parts[4]
                    })
            
            return containers
            
        except Exception as e:
            self.logger.error(f"Failed to get Docker stats: {e}")
            return []


class ApplicationMetrics:
    """Collects application-specific metrics"""
    
    def __init__(self, log_dir: str = "/opt/youtube_scraper/logs"):
        self.log_dir = Path(log_dir)
        self.logger = logging.getLogger(__name__)
    
    def get_scraper_status(self) -> Dict[str, Any]:
        """Get YouTube scraper status from logs"""
        try:
            scraper_log = self.log_dir / "scraper.log"
            if not scraper_log.exists():
                return {'status': 'unknown', 'last_run': None}
            
            # Read last 50 lines to get recent status
            result = subprocess.run(
                ['tail', '-50', str(scraper_log)], 
                capture_output=True, text=True
            )
            
            lines = result.stdout.split('\n')
            
            # Look for completion or error patterns
            last_success = None
            last_error = None
            
            for line in reversed(lines):
                if 'Collection completed successfully' in line:
                    last_success = self._extract_timestamp(line)
                    break
                elif 'ERROR' in line or 'CRITICAL' in line:
                    last_error = self._extract_timestamp(line)
            
            # Determine status
            if last_success:
                status = 'running'
                last_run = last_success
            elif last_error:
                status = 'error'
                last_run = last_error
            else:
                status = 'unknown'
                last_run = None
            
            return {
                'status': status,
                'last_run': last_run,
                'last_success': last_success,
                'last_error': last_error
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get scraper status: {e}")
            return {'status': 'error', 'last_run': None}
    
    def _extract_timestamp(self, log_line: str) -> Optional[datetime]:
        """Extract timestamp from log line"""
        try:
            # Assuming log format: YYYY-MM-DD HH:MM:SS,mmm - ...
            timestamp_str = log_line.split(' - ')[0]
            return datetime.strptime(timestamp_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
        except:
            return None
    
    def get_error_rate(self, hours: int = 24) -> Dict[str, int]:
        """Calculate error rate from logs"""
        try:
            error_log = self.log_dir / "error.log"
            if not error_log.exists():
                return {'total_errors': 0, 'critical_errors': 0, 'warnings': 0}
            
            since = datetime.now() - timedelta(hours=hours)
            
            # Count errors by severity
            errors = {'total_errors': 0, 'critical_errors': 0, 'warnings': 0}
            
            with open(error_log, 'r') as f:
                for line in f:
                    timestamp = self._extract_timestamp(line)
                    if timestamp and timestamp >= since:
                        if 'CRITICAL' in line:
                            errors['critical_errors'] += 1
                        elif 'ERROR' in line:
                            errors['total_errors'] += 1
                        elif 'WARNING' in line:
                            errors['warnings'] += 1
            
            return errors
            
        except Exception as e:
            self.logger.error(f"Failed to calculate error rate: {e}")
            return {'total_errors': 0, 'critical_errors': 0, 'warnings': 0}
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics from analytics"""
        try:
            # This would integrate with your analytics system
            # For now, return mock data structure
            return {
                'avg_scrape_time': 15.5,  # seconds per keyword
                'success_rate': 98.5,     # percentage
                'videos_per_hour': 450,   # throughput
                'keywords_processed': 50  # daily count
            }
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return {}


class AlertManager:
    """Manages alert generation and delivery"""
    
    def __init__(self, config_path: str = "/opt/youtube_scraper/monitoring/alert_config.json"):
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        self.active_alerts: List[Alert] = []
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load alerting configuration"""
        default_config = {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipients": []
            },
            "slack": {
                "webhook_url": "",
                "channel": "#alerts"
            },
            "thresholds": {
                "cpu_warning": 80.0,
                "cpu_critical": 95.0,
                "memory_warning": 85.0,
                "memory_critical": 95.0,
                "disk_warning": 80.0,
                "disk_critical": 90.0,
                "error_rate_warning": 5.0,
                "error_rate_critical": 10.0,
                "success_rate_warning": 90.0,
                "success_rate_critical": 80.0
            },
            "cooldown_minutes": 30
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                default_config.update(config)
            return default_config
        except Exception as e:
            self.logger.error(f"Failed to load config, using defaults: {e}")
            return default_config
    
    def check_thresholds(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        thresholds = self.config['thresholds']
        
        # CPU alerts
        cpu_usage = metrics.get('system', {}).get('cpu_usage', 0)
        if cpu_usage >= thresholds['cpu_critical']:
            alerts.append(Alert(
                severity='critical',
                metric='cpu_usage',
                current_value=cpu_usage,
                threshold=thresholds['cpu_critical'],
                timestamp=datetime.now(),
                description=f"CPU usage critical: {cpu_usage:.1f}%"
            ))
        elif cpu_usage >= thresholds['cpu_warning']:
            alerts.append(Alert(
                severity='warning',
                metric='cpu_usage',
                current_value=cpu_usage,
                threshold=thresholds['cpu_warning'],
                timestamp=datetime.now(),
                description=f"CPU usage high: {cpu_usage:.1f}%"
            ))
        
        # Memory alerts
        memory_usage = metrics.get('system', {}).get('memory', {}).get('used_percent', 0)
        if memory_usage >= thresholds['memory_critical']:
            alerts.append(Alert(
                severity='critical',
                metric='memory_usage',
                current_value=memory_usage,
                threshold=thresholds['memory_critical'],
                timestamp=datetime.now(),
                description=f"Memory usage critical: {memory_usage:.1f}%"
            ))
        elif memory_usage >= thresholds['memory_warning']:
            alerts.append(Alert(
                severity='warning',
                metric='memory_usage',
                current_value=memory_usage,
                threshold=thresholds['memory_warning'],
                timestamp=datetime.now(),
                description=f"Memory usage high: {memory_usage:.1f}%"
            ))
        
        # Disk alerts
        disk_usage = metrics.get('system', {}).get('disk', {}).get('used_percent', 0)
        if disk_usage >= thresholds['disk_critical']:
            alerts.append(Alert(
                severity='critical',
                metric='disk_usage',
                current_value=disk_usage,
                threshold=thresholds['disk_critical'],
                timestamp=datetime.now(),
                description=f"Disk usage critical: {disk_usage:.1f}%"
            ))
        elif disk_usage >= thresholds['disk_warning']:
            alerts.append(Alert(
                severity='warning',
                metric='disk_usage',
                current_value=disk_usage,
                threshold=thresholds['disk_warning'],
                timestamp=datetime.now(),
                description=f"Disk usage high: {disk_usage:.1f}%"
            ))
        
        # Application alerts
        app_metrics = metrics.get('application', {})
        success_rate = app_metrics.get('performance', {}).get('success_rate', 100)
        
        if success_rate <= thresholds['success_rate_critical']:
            alerts.append(Alert(
                severity='critical',
                metric='success_rate',
                current_value=success_rate,
                threshold=thresholds['success_rate_critical'],
                timestamp=datetime.now(),
                description=f"Scraper success rate critical: {success_rate:.1f}%"
            ))
        elif success_rate <= thresholds['success_rate_warning']:
            alerts.append(Alert(
                severity='warning',
                metric='success_rate',
                current_value=success_rate,
                threshold=thresholds['success_rate_warning'],
                timestamp=datetime.now(),
                description=f"Scraper success rate low: {success_rate:.1f}%"
            ))
        
        return alerts
    
    def send_email_alert(self, alert: Alert):
        """Send email notification for alert"""
        try:
            email_config = self.config['email']
            if not email_config['sender_email'] or not email_config['recipients']:
                return
            
            msg = MimeMultipart()
            msg['From'] = email_config['sender_email']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = f"[{alert.severity.upper()}] YouTube Scraper Alert - {alert.metric}"
            
            body = f"""
Alert Details:
- Severity: {alert.severity.upper()}
- Metric: {alert.metric}
- Current Value: {alert.current_value}
- Threshold: {alert.threshold}
- Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Description: {alert.description}
- Node: {alert.node_id}

Please investigate immediately if this is a critical alert.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email alert sent for {alert.metric}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    def send_slack_alert(self, alert: Alert):
        """Send Slack notification for alert"""
        try:
            slack_config = self.config['slack']
            if not slack_config['webhook_url']:
                return
            
            color = {'info': 'good', 'warning': 'warning', 'critical': 'danger'}[alert.severity]
            
            payload = {
                "channel": slack_config['channel'],
                "username": "YouTube Scraper Monitor",
                "icon_emoji": ":warning:",
                "attachments": [{
                    "color": color,
                    "title": f"{alert.severity.upper()} Alert: {alert.metric}",
                    "text": alert.description,
                    "fields": [
                        {"title": "Current Value", "value": str(alert.current_value), "short": True},
                        {"title": "Threshold", "value": str(alert.threshold), "short": True},
                        {"title": "Node", "value": alert.node_id, "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "short": True}
                    ]
                }]
            }
            
            response = requests.post(slack_config['webhook_url'], json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Slack alert sent for {alert.metric}")
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
    
    def process_alerts(self, alerts: List[Alert]):
        """Process and send alerts with cooldown logic"""
        for alert in alerts:
            # Check cooldown
            cooldown_key = f"{alert.metric}_{alert.severity}"
            last_sent = getattr(self, f"_last_sent_{cooldown_key}", None)
            
            if last_sent:
                minutes_since = (datetime.now() - last_sent).total_seconds() / 60
                if minutes_since < self.config['cooldown_minutes']:
                    continue
            
            # Send notifications
            if alert.severity in ['warning', 'critical']:
                self.send_email_alert(alert)
                self.send_slack_alert(alert)
            
            # Update cooldown
            setattr(self, f"_last_sent_{cooldown_key}", datetime.now())
            
            self.logger.info(f"Processed {alert.severity} alert for {alert.metric}")


class MonitoringDashboard:
    """Creates monitoring dashboard and reports"""
    
    def __init__(self, output_dir: str = "/opt/youtube_scraper/monitoring/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def generate_html_report(self, metrics: Dict[str, Any], alerts: List[Alert]) -> str:
        """Generate HTML monitoring report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Scraper Monitoring Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .metric-card { border: 1px solid #ddd; margin: 10px; padding: 15px; border-radius: 5px; }
        .critical { background-color: #ffebee; border-color: #f44336; }
        .warning { background-color: #fff3e0; border-color: #ff9800; }
        .normal { background-color: #e8f5e8; border-color: #4caf50; }
        .alert { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .alert.critical { background: #ffcdd2; }
        .alert.warning { background: #ffe0b2; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>YouTube Scraper Monitoring Dashboard</h1>
        <p>Generated: {timestamp}</p>
    </div>
    
    <h2>System Metrics</h2>
    <div class="metric-card {cpu_status}">
        <h3>CPU Usage: {cpu_usage:.1f}%</h3>
    </div>
    
    <div class="metric-card {memory_status}">
        <h3>Memory Usage: {memory_usage:.1f}%</h3>
        <p>Used: {memory_used:.1f} GB / {memory_total:.1f} GB</p>
    </div>
    
    <div class="metric-card {disk_status}">
        <h3>Disk Usage: {disk_usage:.1f}%</h3>
        <p>Used: {disk_used:.1f} GB / {disk_total:.1f} GB</p>
    </div>
    
    <h2>Application Status</h2>
    <div class="metric-card {app_status}">
        <h3>Scraper Status: {scraper_status}</h3>
        <p>Last Run: {last_run}</p>
        <p>Success Rate: {success_rate:.1f}%</p>
    </div>
    
    <h2>Active Alerts ({alert_count})</h2>
    {alerts_html}
    
    <h2>Docker Containers</h2>
    <table>
        <tr><th>Container</th><th>CPU</th><th>Memory</th><th>Network I/O</th></tr>
        {containers_html}
    </table>
</body>
</html>
        """
        
        # Prepare data
        system_metrics = metrics.get('system', {})
        app_metrics = metrics.get('application', {})
        
        cpu_usage = system_metrics.get('cpu_usage', 0)
        memory = system_metrics.get('memory', {})
        disk = system_metrics.get('disk', {})
        
        # Status determination
        cpu_status = 'critical' if cpu_usage > 95 else 'warning' if cpu_usage > 80 else 'normal'
        memory_status = 'critical' if memory.get('used_percent', 0) > 95 else 'warning' if memory.get('used_percent', 0) > 85 else 'normal'
        disk_status = 'critical' if disk.get('used_percent', 0) > 90 else 'warning' if disk.get('used_percent', 0) > 80 else 'normal'
        
        scraper_status = app_metrics.get('status', {}).get('status', 'unknown')
        app_status = 'critical' if scraper_status == 'error' else 'normal'
        
        # Alerts HTML
        alerts_html = ""
        for alert in alerts:
            alerts_html += f'<div class="alert {alert.severity}">{alert.description}</div>'
        
        # Containers HTML
        containers_html = ""
        for container in metrics.get('docker', []):
            containers_html += f"""
            <tr>
                <td>{container['name']}</td>
                <td>{container['cpu_percent']}</td>
                <td>{container['memory_usage']}</td>
                <td>{container['network_io']}</td>
            </tr>
            """
        
        return html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            cpu_usage=cpu_usage,
            cpu_status=cpu_status,
            memory_usage=memory.get('used_percent', 0),
            memory_used=memory.get('used_gb', 0),
            memory_total=memory.get('total_gb', 0),
            memory_status=memory_status,
            disk_usage=disk.get('used_percent', 0),
            disk_used=disk.get('used_gb', 0),
            disk_total=disk.get('total_gb', 0),
            disk_status=disk_status,
            scraper_status=scraper_status,
            app_status=app_status,
            last_run=app_metrics.get('status', {}).get('last_run', 'Unknown'),
            success_rate=app_metrics.get('performance', {}).get('success_rate', 0),
            alert_count=len(alerts),
            alerts_html=alerts_html,
            containers_html=containers_html
        )
    
    def save_report(self, html_content: str):
        """Save HTML report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.output_dir / f"monitoring_report_{timestamp}.html"
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        # Also save as latest.html
        latest_path = self.output_dir / "latest.html"
        with open(latest_path, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Monitoring report saved to {report_path}")


async def main():
    """Main monitoring loop"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    system_metrics = SystemMetrics()
    app_metrics = ApplicationMetrics()
    alert_manager = AlertManager()
    dashboard = MonitoringDashboard()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting monitoring system...")
    
    while True:
        try:
            # Collect all metrics
            metrics = {
                'system': {
                    'cpu_usage': system_metrics.get_cpu_usage(),
                    'memory': system_metrics.get_memory_usage(),
                    'disk': system_metrics.get_disk_usage(),
                    'network': system_metrics.get_network_stats()
                },
                'docker': system_metrics.get_docker_stats(),
                'application': {
                    'status': app_metrics.get_scraper_status(),
                    'errors': app_metrics.get_error_rate(),
                    'performance': app_metrics.get_performance_metrics()
                }
            }
            
            # Check for alerts
            alerts = alert_manager.check_thresholds(metrics)
            
            # Process alerts
            if alerts:
                alert_manager.process_alerts(alerts)
            
            # Generate dashboard
            html_report = dashboard.generate_html_report(metrics, alerts)
            dashboard.save_report(html_report)
            
            # Log summary
            logger.info(f"Monitoring cycle completed. "
                       f"CPU: {metrics['system']['cpu_usage']:.1f}%, "
                       f"Memory: {metrics['system']['memory']['used_percent']:.1f}%, "
                       f"Alerts: {len(alerts)}")
            
            # Wait for next cycle (5 minutes)
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry


if __name__ == "__main__":
    asyncio.run(main())
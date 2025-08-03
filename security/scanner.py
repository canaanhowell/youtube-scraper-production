#!/usr/bin/env python3
"""
Automated security scanning and vulnerability assessment for YouTube Scraper
Provides comprehensive security analysis, dependency scanning, and code auditing
"""

import json
import subprocess
import sys
import os
import re
import hashlib
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging


@dataclass
class SecurityFinding:
    """Represents a security finding"""
    severity: str  # critical, high, medium, low, info
    category: str  # dependency, code, configuration, secret
    title: str
    description: str
    file_path: Optional[str]
    line_number: Optional[int]
    cwe_id: Optional[str]
    cvss_score: Optional[float]
    remediation: str
    timestamp: datetime


@dataclass
class SecurityReport:
    """Complete security assessment report"""
    scan_id: str
    timestamp: datetime
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings: List[SecurityFinding]
    scan_duration: float
    tools_used: List[str]


class DependencyScanner:
    """Scans Python dependencies for known vulnerabilities"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)
    
    def scan_with_safety(self) -> List[SecurityFinding]:
        """Scan dependencies using Safety"""
        findings = []
        
        try:
            # Run safety check
            result = subprocess.run(
                [sys.executable, '-m', 'safety', 'check', '--json'],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.stdout:
                vulnerabilities = json.loads(result.stdout)
                
                for vuln in vulnerabilities:
                    finding = SecurityFinding(
                        severity=self._map_safety_severity(vuln.get('id', '')),
                        category='dependency',
                        title=f"Vulnerable dependency: {vuln.get('package_name', 'unknown')}",
                        description=vuln.get('advisory', 'No description available'),
                        file_path='requirements.txt',
                        line_number=None,
                        cwe_id=None,
                        cvss_score=None,
                        remediation=f"Upgrade {vuln.get('package_name')} to version {vuln.get('analyzed_version', 'latest')}",
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
        except Exception as e:
            self.logger.error(f"Safety scan failed: {e}")
        
        return findings
    
    def scan_with_pip_audit(self) -> List[SecurityFinding]:
        """Scan dependencies using pip-audit"""
        findings = []
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip_audit', '--format=json'],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.stdout:
                audit_data = json.loads(result.stdout)
                
                for vuln in audit_data.get('vulnerabilities', []):
                    finding = SecurityFinding(
                        severity=self._map_cvss_to_severity(vuln.get('fix', {}).get('cvss', 0)),
                        category='dependency',
                        title=f"CVE in {vuln.get('package', 'unknown')}: {vuln.get('id', 'unknown')}",
                        description=vuln.get('description', 'No description available'),
                        file_path='requirements.txt',
                        line_number=None,
                        cwe_id=vuln.get('cwe'),
                        cvss_score=vuln.get('fix', {}).get('cvss'),
                        remediation=f"Update to version {vuln.get('fix', {}).get('versions', ['latest'])[0]}",
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
        except Exception as e:
            self.logger.error(f"pip-audit scan failed: {e}")
        
        return findings
    
    def _map_safety_severity(self, vuln_id: str) -> str:
        """Map Safety vulnerability ID to severity"""
        # This is a simplified mapping - in practice, you'd want more sophisticated logic
        high_priority_patterns = ['44715', '44716', '44717']  # Example critical CVEs
        
        if any(pattern in vuln_id for pattern in high_priority_patterns):
            return 'critical'
        return 'medium'
    
    def _map_cvss_to_severity(self, cvss_score: float) -> str:
        """Map CVSS score to severity level"""
        if cvss_score >= 9.0:
            return 'critical'
        elif cvss_score >= 7.0:
            return 'high'
        elif cvss_score >= 4.0:
            return 'medium'
        elif cvss_score > 0.0:
            return 'low'
        return 'info'


class CodeScanner:
    """Scans source code for security vulnerabilities"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)
    
    def scan_with_bandit(self) -> List[SecurityFinding]:
        """Scan code using Bandit"""
        findings = []
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'bandit', '-r', 'src/', '-f', 'json'],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.stdout:
                bandit_data = json.loads(result.stdout)
                
                for result_item in bandit_data.get('results', []):
                    finding = SecurityFinding(
                        severity=result_item.get('issue_severity', 'medium').lower(),
                        category='code',
                        title=f"Bandit {result_item.get('test_id', 'unknown')}: {result_item.get('test_name', 'Security issue')}",
                        description=result_item.get('issue_text', 'No description available'),
                        file_path=result_item.get('filename'),
                        line_number=result_item.get('line_number'),
                        cwe_id=result_item.get('cwe', {}).get('id'),
                        cvss_score=None,
                        remediation=result_item.get('issue_text', 'Review and fix the identified issue'),
                        timestamp=datetime.now()
                    )
                    findings.append(finding)
            
        except Exception as e:
            self.logger.error(f"Bandit scan failed: {e}")
        
        return findings
    
    def scan_for_secrets(self) -> List[SecurityFinding]:
        """Scan for hardcoded secrets and sensitive data"""
        findings = []
        
        # Patterns for common secrets
        secret_patterns = {
            'aws_access_key': r'AKIA[0-9A-Z]{16}',
            'aws_secret_key': r'[A-Za-z0-9/+=]{40}',
            'api_key': r'(api[_-]?key|password|secret|token)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{10,}',
            'private_key': r'-----BEGIN [A-Z ]+PRIVATE KEY-----',
            'jwt_token': r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*',
            'database_url': r'(mysql|postgres|mongodb)://[^:]+:[^@]+@[^/]+',
            'email_password': r'(smtp|email)[_-]?(password|pass)["\']?\s*[:=]\s*["\']?[^"\'\\s]+',
        }
        
        # Scan Python files
        for py_file in self.project_root.rglob('*.py'):
            if any(exclude in str(py_file) for exclude in ['.git', '__pycache__', '.venv', 'venv']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for line_num, line in enumerate(content.split('\n'), 1):
                    for secret_type, pattern in secret_patterns.items():
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            # Skip comments and test files
                            if line.strip().startswith('#') or 'test' in str(py_file).lower():
                                continue
                                
                            finding = SecurityFinding(
                                severity='critical',
                                category='secret',
                                title=f"Potential {secret_type.replace('_', ' ')} in code",
                                description=f"Found pattern matching {secret_type} in source code",
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=line_num,
                                cwe_id='CWE-798',
                                cvss_score=9.8,
                                remediation="Move secrets to environment variables or secure vault",
                                timestamp=datetime.now()
                            )
                            findings.append(finding)
                            
            except Exception as e:
                self.logger.error(f"Error scanning {py_file}: {e}")
        
        return findings
    
    def scan_sql_injection(self) -> List[SecurityFinding]:
        """Scan for potential SQL injection vulnerabilities"""
        findings = []
        
        # Patterns that might indicate SQL injection risks
        sql_patterns = [
            r'execute\s*\(\s*["\'].*%.*["\']',  # String formatting in SQL
            r'cursor\.execute\s*\(\s*["\'][^"\']*\+',  # String concatenation
            r'query\s*=\s*["\'][^"\']*\+',  # Query string concatenation
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            if any(exclude in str(py_file) for exclude in ['.git', '__pycache__', '.venv']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern in sql_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            finding = SecurityFinding(
                                severity='high',
                                category='code',
                                title="Potential SQL Injection vulnerability",
                                description="SQL query construction using string concatenation or formatting",
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=line_num,
                                cwe_id='CWE-89',
                                cvss_score=8.1,
                                remediation="Use parameterized queries or ORM methods",
                                timestamp=datetime.now()
                            )
                            findings.append(finding)
                            
            except Exception as e:
                self.logger.error(f"Error scanning {py_file} for SQL injection: {e}")
        
        return findings


class ConfigurationScanner:
    """Scans configuration files for security issues"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)
    
    def scan_docker_security(self) -> List[SecurityFinding]:
        """Scan Docker configuration for security issues"""
        findings = []
        
        # Check Dockerfile
        dockerfile = self.project_root / 'Dockerfile'
        if dockerfile.exists():
            findings.extend(self._scan_dockerfile(dockerfile))
        
        # Check docker-compose.yml
        compose_file = self.project_root / 'docker-compose.yml'
        if compose_file.exists():
            findings.extend(self._scan_docker_compose(compose_file))
        
        return findings
    
    def _scan_dockerfile(self, dockerfile: Path) -> List[SecurityFinding]:
        """Scan Dockerfile for security issues"""
        findings = []
        
        try:
            with open(dockerfile, 'r') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for root user
                if line.startswith('USER root') or (line.startswith('RUN') and 'sudo' in line):
                    findings.append(SecurityFinding(
                        severity='medium',
                        category='configuration',
                        title="Running as root user",
                        description="Container is configured to run as root user",
                        file_path='Dockerfile',
                        line_number=line_num,
                        cwe_id='CWE-250',
                        cvss_score=5.3,
                        remediation="Create and use a non-root user for the container",
                        timestamp=datetime.now()
                    ))
                
                # Check for --privileged flag
                if '--privileged' in line:
                    findings.append(SecurityFinding(
                        severity='high',
                        category='configuration',
                        title="Privileged container configuration",
                        description="Container is configured to run in privileged mode",
                        file_path='Dockerfile',
                        line_number=line_num,
                        cwe_id='CWE-250',
                        cvss_score=7.2,
                        remediation="Remove --privileged flag and use specific capabilities instead",
                        timestamp=datetime.now()
                    ))
                
                # Check for COPY without user/group specification
                if line.startswith('COPY') and '--chown=' not in line:
                    findings.append(SecurityFinding(
                        severity='low',
                        category='configuration',
                        title="Files copied without ownership specification",
                        description="Files are copied without specifying ownership",
                        file_path='Dockerfile',
                        line_number=line_num,
                        cwe_id='CWE-732',
                        cvss_score=3.1,
                        remediation="Use --chown flag when copying files",
                        timestamp=datetime.now()
                    ))
                    
        except Exception as e:
            self.logger.error(f"Error scanning Dockerfile: {e}")
        
        return findings
    
    def _scan_docker_compose(self, compose_file: Path) -> List[SecurityFinding]:
        """Scan docker-compose.yml for security issues"""
        findings = []
        
        try:
            import yaml
            
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            services = compose_data.get('services', {})
            
            for service_name, service_config in services.items():
                # Check for privileged mode
                if service_config.get('privileged', False):
                    findings.append(SecurityFinding(
                        severity='high',
                        category='configuration',
                        title=f"Service {service_name} runs in privileged mode",
                        description="Service is configured to run in privileged mode",
                        file_path='docker-compose.yml',
                        line_number=None,
                        cwe_id='CWE-250',
                        cvss_score=7.2,
                        remediation="Remove privileged: true and use specific capabilities",
                        timestamp=datetime.now()
                    ))
                
                # Check for host network mode
                if service_config.get('network_mode') == 'host':
                    findings.append(SecurityFinding(
                        severity='medium',
                        category='configuration',
                        title=f"Service {service_name} uses host networking",
                        description="Service is configured to use host network",
                        file_path='docker-compose.yml',
                        line_number=None,
                        cwe_id='CWE-250',
                        cvss_score=5.3,
                        remediation="Use bridge networking and expose specific ports",
                        timestamp=datetime.now()
                    ))
                
                # Check for volume mounts of sensitive directories
                volumes = service_config.get('volumes', [])
                for volume in volumes:
                    if isinstance(volume, str) and any(sensitive in volume for sensitive in ['/', '/etc', '/var', '/usr']):
                        findings.append(SecurityFinding(
                            severity='medium',
                            category='configuration',
                            title=f"Service {service_name} mounts sensitive directory",
                            description=f"Service mounts sensitive system directory: {volume}",
                            file_path='docker-compose.yml',
                            line_number=None,
                            cwe_id='CWE-732',
                            cvss_score=5.9,
                            remediation="Avoid mounting sensitive system directories",
                            timestamp=datetime.now()
                        ))
                        
        except Exception as e:
            self.logger.error(f"Error scanning docker-compose.yml: {e}")
        
        return findings


class SecurityScanner:
    """Main security scanner orchestrator"""
    
    def __init__(self, project_root: Path, output_dir: Path = None):
        self.project_root = project_root
        self.output_dir = output_dir or project_root / 'security' / 'reports'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.dependency_scanner = DependencyScanner(project_root)
        self.code_scanner = CodeScanner(project_root)
        self.config_scanner = ConfigurationScanner(project_root)
        
        self.logger = logging.getLogger(__name__)
    
    def run_full_scan(self) -> SecurityReport:
        """Run comprehensive security scan"""
        scan_id = f"scan_{int(time.time())}"
        start_time = time.time()
        
        self.logger.info("Starting comprehensive security scan...")
        
        all_findings = []
        tools_used = []
        
        # Dependency scanning
        self.logger.info("Scanning dependencies...")
        try:
            safety_findings = self.dependency_scanner.scan_with_safety()
            pip_audit_findings = self.dependency_scanner.scan_with_pip_audit()
            all_findings.extend(safety_findings + pip_audit_findings)
            tools_used.extend(['safety', 'pip-audit'])
        except Exception as e:
            self.logger.error(f"Dependency scanning failed: {e}")
        
        # Code scanning
        self.logger.info("Scanning source code...")
        try:
            bandit_findings = self.code_scanner.scan_with_bandit()
            secret_findings = self.code_scanner.scan_for_secrets()
            sql_findings = self.code_scanner.scan_sql_injection()
            all_findings.extend(bandit_findings + secret_findings + sql_findings)
            tools_used.extend(['bandit', 'custom-secret-scanner', 'custom-sql-scanner'])
        except Exception as e:
            self.logger.error(f"Code scanning failed: {e}")
        
        # Configuration scanning
        self.logger.info("Scanning configuration...")
        try:
            config_findings = self.config_scanner.scan_docker_security()
            all_findings.extend(config_findings)
            tools_used.append('custom-config-scanner')
        except Exception as e:
            self.logger.error(f"Configuration scanning failed: {e}")
        
        # Generate report
        end_time = time.time()
        scan_duration = end_time - start_time
        
        # Count findings by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        for finding in all_findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        
        report = SecurityReport(
            scan_id=scan_id,
            timestamp=datetime.now(),
            total_findings=len(all_findings),
            critical_count=severity_counts['critical'],
            high_count=severity_counts['high'],
            medium_count=severity_counts['medium'],
            low_count=severity_counts['low'],
            findings=all_findings,
            scan_duration=scan_duration,
            tools_used=list(set(tools_used))
        )
        
        # Save report
        self._save_report(report)
        
        self.logger.info(f"Security scan completed in {scan_duration:.2f}s. "
                        f"Found {len(all_findings)} total findings "
                        f"({severity_counts['critical']} critical, {severity_counts['high']} high)")
        
        return report
    
    def _save_report(self, report: SecurityReport):
        """Save security report to files"""
        timestamp = report.timestamp.strftime('%Y%m%d_%H%M%S')
        
        # JSON report
        json_file = self.output_dir / f"security_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        # HTML report
        html_file = self.output_dir / f"security_report_{timestamp}.html"
        html_content = self._generate_html_report(report)
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        # CSV for easy filtering
        csv_file = self.output_dir / f"security_findings_{timestamp}.csv"
        with open(csv_file, 'w') as f:
            f.write("Severity,Category,Title,File,Line,CWE,CVSS,Remediation\n")
            for finding in report.findings:
                f.write(f'"{finding.severity}","{finding.category}","{finding.title}",'
                       f'"{finding.file_path or ""}","{finding.line_number or ""}",'
                       f'"{finding.cwe_id or ""}","{finding.cvss_score or ""}",'
                       f'"{finding.remediation}"\n')
        
        self.logger.info(f"Security reports saved: {json_file}, {html_file}, {csv_file}")
    
    def _generate_html_report(self, report: SecurityReport) -> str:
        """Generate HTML security report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Security Scan Report - {scan_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
        .critical {{ background: #dc3545; color: white; }}
        .high {{ background: #fd7e14; color: white; }}
        .medium {{ background: #ffc107; color: black; }}
        .low {{ background: #28a745; color: white; }}
        .finding {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .finding.critical {{ border-color: #dc3545; background: #f8d7da; }}
        .finding.high {{ border-color: #fd7e14; background: #fff3cd; }}
        .finding.medium {{ border-color: #ffc107; background: #fff3cd; }}
        .finding.low {{ border-color: #28a745; background: #d4edda; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Security Scan Report</h1>
        <p>Scan ID: {scan_id}</p>
        <p>Timestamp: {timestamp}</p>
        <p>Duration: {duration:.2f} seconds</p>
        <p>Tools Used: {tools}</p>
    </div>
    
    <div class="summary">
        <div class="metric critical">
            <h3>{critical_count}</h3>
            <p>Critical</p>
        </div>
        <div class="metric high">
            <h3>{high_count}</h3>
            <p>High</p>
        </div>
        <div class="metric medium">
            <h3>{medium_count}</h3>
            <p>Medium</p>
        </div>
        <div class="metric low">
            <h3>{low_count}</h3>
            <p>Low</p>
        </div>
        <div class="metric">
            <h3>{total_findings}</h3>
            <p>Total</p>
        </div>
    </div>
    
    <h2>Findings</h2>
    {findings_html}
    
</body>
</html>
        """
        
        # Generate findings HTML
        findings_html = ""
        for finding in sorted(report.findings, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.severity, 4)):
            findings_html += f"""
            <div class="finding {finding.severity}">
                <h3>{finding.title}</h3>
                <p><strong>Severity:</strong> {finding.severity.upper()}</p>
                <p><strong>Category:</strong> {finding.category}</p>
                <p><strong>Description:</strong> {finding.description}</p>
                {f'<p><strong>File:</strong> {finding.file_path}:{finding.line_number}</p>' if finding.file_path else ''}
                {f'<p><strong>CWE:</strong> {finding.cwe_id}</p>' if finding.cwe_id else ''}
                {f'<p><strong>CVSS Score:</strong> {finding.cvss_score}</p>' if finding.cvss_score else ''}
                <p><strong>Remediation:</strong> {finding.remediation}</p>
            </div>
            """
        
        return html_template.format(
            scan_id=report.scan_id,
            timestamp=report.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            duration=report.scan_duration,
            tools=', '.join(report.tools_used),
            critical_count=report.critical_count,
            high_count=report.high_count,
            medium_count=report.medium_count,
            low_count=report.low_count,
            total_findings=report.total_findings,
            findings_html=findings_html
        )


def main():
    """CLI interface for security scanner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Scraper Security Scanner')
    parser.add_argument('--project-root', type=Path, default=Path.cwd(),
                       help='Path to project root directory')
    parser.add_argument('--output-dir', type=Path,
                       help='Output directory for reports')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick scan (skip some time-consuming checks)')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scanner = SecurityScanner(args.project_root, args.output_dir)
    report = scanner.run_full_scan()
    
    print(f"\nSecurity Scan Complete!")
    print(f"Total Findings: {report.total_findings}")
    print(f"Critical: {report.critical_count}, High: {report.high_count}, "
          f"Medium: {report.medium_count}, Low: {report.low_count}")
    print(f"Scan Duration: {report.scan_duration:.2f} seconds")


if __name__ == "__main__":
    main()
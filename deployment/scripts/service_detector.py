#!/usr/bin/env python3
"""
Smart Service Detection and Auto-Configuration
Automatically detects new Python scripts and systemd services, configures them properly
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Set
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/service_detector.log')
    ]
)
logger = logging.getLogger(__name__)

class ServiceDetector:
    """Detects and auto-configures services based on file patterns"""
    
    def __init__(self, project_dir: str = "/opt/youtube_app"):
        self.project_dir = Path(project_dir)
        self.systemd_dir = Path("/etc/systemd/system")
        self.service_config_file = self.project_dir / "deployment" / "auto_services.json"
        
    def scan_for_new_scripts(self) -> List[Dict]:
        """Scan for Python scripts that could be services"""
        logger.info("Scanning for new executable Python scripts...")
        
        new_services = []
        
        # Patterns that indicate a script should be a service
        service_patterns = [
            r".*_manager\.py$",      # *_manager.py files
            r".*_collector\.py$",    # *_collector.py files  
            r".*_scraper\.py$",      # *_scraper.py files
            r".*_monitor\.py$",      # *_monitor.py files
            r".*_analytics\.py$",    # *_analytics.py files
            r"run_.*\.py$",          # run_*.py files
        ]
        
        # Scan src/ and scripts/ directories
        scan_dirs = [
            self.project_dir / "src",
            self.project_dir / "src" / "scripts",
            self.project_dir / "src" / "scripts" / "collectors",
            self.project_dir,  # Root directory
        ]
        
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
                
            for py_file in scan_dir.rglob("*.py"):
                # Skip __init__.py and test files
                if py_file.name.startswith("__") or "test" in py_file.name.lower():
                    continue
                
                # Check if file matches service patterns
                for pattern in service_patterns:
                    if re.match(pattern, py_file.name):
                        # Check if it's executable or has main block
                        if self._is_executable_script(py_file):
                            service_info = self._analyze_script(py_file)
                            if service_info:
                                new_services.append(service_info)
                        break
        
        logger.info(f"Found {len(new_services)} potential new services")
        return new_services
    
    def _is_executable_script(self, py_file: Path) -> bool:
        """Check if Python file is executable (has main block or shebang)"""
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Check for main block
            if 'if __name__ == "__main__"' in content:
                return True
                
            # Check for shebang
            if content.startswith('#!/'):
                return True
                
            # Check for async main or direct execution patterns
            if re.search(r'async def main\(|def main\(|asyncio\.run\(', content):
                return True
                
        except Exception as e:
            logger.warning(f"Could not read {py_file}: {e}")
            
        return False
    
    def _analyze_script(self, py_file: Path) -> Dict:
        """Analyze script to determine service configuration"""
        try:
            with open(py_file, 'r') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Could not read {py_file}: {e}")
            return None
            
        relative_path = py_file.relative_to(self.project_dir)
        service_name = self._generate_service_name(py_file)
        
        # Determine service type and schedule
        service_type = "oneshot"
        schedule = None
        description = f"Auto-detected service for {py_file.name}"
        
        # Check for scheduling keywords
        if any(keyword in content.lower() for keyword in ['schedule', 'cron', 'timer', 'hourly', 'daily']):
            service_type = "timer"
            # Try to detect schedule from comments or variables
            schedule = self._detect_schedule(content)
        
        # Check for continuous running patterns
        if any(keyword in content.lower() for keyword in ['while true', 'infinite loop', 'continuous', 'daemon']):
            service_type = "simple"
        
        # Detect description from docstring or comments
        detected_desc = self._detect_description(content)
        if detected_desc:
            description = detected_desc
            
        return {
            "name": service_name,
            "file_path": str(relative_path),
            "full_path": str(py_file),
            "type": service_type,
            "schedule": schedule,
            "description": description,
            "auto_detected": True
        }
    
    def _generate_service_name(self, py_file: Path) -> str:
        """Generate systemd service name from file path"""
        # Remove .py extension
        name = py_file.stem
        
        # Add youtube prefix if not present
        if not name.startswith('youtube'):
            name = f"youtube-{name}"
            
        # Replace underscores with hyphens for systemd convention
        name = name.replace('_', '-')
        
        return name
    
    def _detect_schedule(self, content: str) -> str:
        """Try to detect schedule from script content"""
        # Look for common schedule patterns in comments
        schedule_patterns = {
            r'hourly|every hour|@hourly': 'hourly',
            r'daily|every day|@daily': 'daily', 
            r'weekly|every week|@weekly': 'weekly',
            r'monthly|every month|@monthly': 'monthly',
            r'every \d+ minutes?': '*:0/10',  # Default to 10 min
            r'every \d+ hours?': '0 */2 * * *',  # Default to 2 hours
        }
        
        content_lower = content.lower()
        
        for pattern, schedule in schedule_patterns.items():
            if re.search(pattern, content_lower):
                return schedule
                
        # Default for timer services
        return 'hourly'
    
    def _detect_description(self, content: str) -> str:
        """Extract description from docstring or comments"""
        # Try to find module docstring
        docstring_match = re.search(r'"""([^"]+)"""', content)
        if docstring_match:
            desc = docstring_match.group(1).strip().split('\n')[0]
            if len(desc) > 10:  # Reasonable description length
                return desc
                
        # Try to find descriptive comments
        comment_match = re.search(r'^#\s*([A-Z][^#\n]{10,80})', content, re.MULTILINE)
        if comment_match:
            return comment_match.group(1).strip()
            
        return None
    
    def detect_existing_services(self) -> Set[str]:
        """Get list of existing youtube-related services"""
        existing = set()
        
        try:
            result = subprocess.run(
                ['systemctl', 'list-unit-files', '--type=service'],
                capture_output=True, text=True
            )
            
            for line in result.stdout.split('\n'):
                if 'youtube-' in line and '.service' in line:
                    service_name = line.split()[0].replace('.service', '')
                    existing.add(service_name)
                    
        except Exception as e:
            logger.error(f"Could not list existing services: {e}")
            
        return existing
    
    def create_systemd_service(self, service_info: Dict) -> bool:
        """Create systemd service file"""
        service_name = service_info['name']
        service_file = self.systemd_dir / f"{service_name}.service"
        
        # Generate service file content
        service_content = self._generate_service_content(service_info)
        
        try:
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            logger.info(f"Created service file: {service_file}")
            
            # If it's a timer service, create timer file too
            if service_info['type'] == 'timer':
                self._create_timer_file(service_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Could not create service file {service_file}: {e}")
            return False
    
    def _generate_service_content(self, service_info: Dict) -> str:
        """Generate systemd service file content"""
        return f"""[Unit]
Description={service_info['description']}
After=network.target

[Service]
Type={service_info['type']}
User=root
WorkingDirectory={self.project_dir}
Environment=PATH={self.project_dir}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={self.project_dir}/venv/bin/python3 {service_info['file_path']}
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=2G
CPUQuota=100%

[Install]
WantedBy=multi-user.target
"""
    
    def _create_timer_file(self, service_info: Dict) -> bool:
        """Create systemd timer file for scheduled services"""
        timer_name = service_info['name']
        timer_file = self.systemd_dir / f"{timer_name}.timer"
        
        # Convert schedule to systemd timer format
        on_calendar = self._schedule_to_systemd(service_info['schedule'])
        
        timer_content = f"""[Unit]
Description=Timer for {service_info['description']}
Requires={timer_name}.service

[Timer]
OnCalendar={on_calendar}
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
"""
        
        try:
            with open(timer_file, 'w') as f:
                f.write(timer_content)
            
            logger.info(f"Created timer file: {timer_file}")
            return True
            
        except Exception as e:
            logger.error(f"Could not create timer file {timer_file}: {e}")
            return False
    
    def _schedule_to_systemd(self, schedule: str) -> str:
        """Convert schedule string to systemd OnCalendar format"""
        schedule_map = {
            'hourly': '*:00',
            'daily': '00:00',
            'weekly': 'Sun 00:00',
            'monthly': '*-*-01 00:00',
        }
        
        return schedule_map.get(schedule, schedule)
    
    def enable_and_start_service(self, service_name: str, service_type: str) -> bool:
        """Enable and start the service"""
        try:
            # Reload systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            if service_type == 'timer':
                # For timer services, enable and start the timer
                timer_name = f"{service_name}.timer"
                subprocess.run(['systemctl', 'enable', timer_name], check=True)
                subprocess.run(['systemctl', 'start', timer_name], check=True)
                logger.info(f"Enabled and started timer: {timer_name}")
            else:
                # For regular services
                subprocess.run(['systemctl', 'enable', f"{service_name}.service"], check=True)
                subprocess.run(['systemctl', 'start', f"{service_name}.service"], check=True)
                logger.info(f"Enabled and started service: {service_name}.service")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Could not enable/start service {service_name}: {e}")
            return False
    
    def save_service_config(self, services: List[Dict]):
        """Save detected services configuration"""
        config_dir = self.service_config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.service_config_file, 'w') as f:
                json.dump(services, f, indent=2)
            logger.info(f"Saved service configuration to {self.service_config_file}")
        except Exception as e:
            logger.error(f"Could not save configuration: {e}")
    
    def run_detection(self) -> Dict:
        """Run full detection and auto-configuration"""
        logger.info("Starting service detection and auto-configuration...")
        
        results = {
            "detected_services": [],
            "created_services": [],
            "failed_services": [],
            "existing_services": list(self.detect_existing_services())
        }
        
        # Scan for new services
        new_services = self.scan_for_new_scripts()
        results["detected_services"] = new_services
        
        # Filter out services that already exist
        existing_services = set(results["existing_services"])
        
        for service_info in new_services:
            service_name = service_info['name']
            
            if service_name in existing_services:
                logger.info(f"Service {service_name} already exists, skipping")
                continue
            
            # Create service file
            if self.create_systemd_service(service_info):
                # Try to enable and start it
                if self.enable_and_start_service(service_name, service_info['type']):
                    results["created_services"].append(service_info)
                    logger.info(f"✅ Successfully created and started service: {service_name}")
                else:
                    results["failed_services"].append(service_info)
                    logger.error(f"❌ Failed to start service: {service_name}")
            else:
                results["failed_services"].append(service_info)
                logger.error(f"❌ Failed to create service: {service_name}")
        
        # Save configuration
        self.save_service_config(results["detected_services"])
        
        logger.info(f"Detection complete: {len(results['created_services'])} services created")
        return results

def main():
    """Main function for CLI usage"""
    detector = ServiceDetector()
    results = detector.run_detection()
    
    print("\n🔍 Service Detection Results:")
    print(f"Detected services: {len(results['detected_services'])}")
    print(f"Created services: {len(results['created_services'])}")
    print(f"Failed services: {len(results['failed_services'])}")
    print(f"Existing services: {len(results['existing_services'])}")
    
    if results['created_services']:
        print("\n✅ Successfully created services:")
        for service in results['created_services']:
            print(f"  - {service['name']}: {service['description']}")
    
    if results['failed_services']:
        print("\n❌ Failed to create services:")
        for service in results['failed_services']:
            print(f"  - {service['name']}: {service['description']}")
    
    return len(results['failed_services']) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
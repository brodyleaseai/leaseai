"""
LeaseAI - Security Code Scanner
Phase 5: Security Hardening & Enterprise Readiness

Runs static application security testing (SAST) using Bandit to identify security issues.
"""

import subprocess
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple


class SecurityScanner:
    """
    Wrapper for Bandit static code analysis tool
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.report_dir = os.path.join(project_root, "security_reports")
        self.ensure_report_directory()
    
    def ensure_report_directory(self):
        """Create security_reports directory if it doesn't exist"""
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
            print(f"✅ Created security reports directory: {self.report_dir}")
    
    def check_bandit_installed(self) -> bool:
        """Check if Bandit is installed"""
        try:
            result = subprocess.run(
                ["bandit", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ Bandit version: {result.stdout.strip()}")
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install_bandit(self) -> bool:
        """Install Bandit via pip"""
        print("📦 Installing Bandit...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "bandit"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print("✅ Bandit installed successfully")
                return True
            else:
                print(f"❌ Failed to install Bandit: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Bandit installation timed out")
            return False
    
    def run_scan(
        self,
        severity_level: str = "low",
        confidence_level: str = "low",
        output_format: str = "json",
        exclude_dirs: List[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Run Bandit security scan
        
        Args:
            severity_level: Minimum severity level (low, medium, high)
            confidence_level: Minimum confidence level (low, medium, high)
            output_format: Output format (json, txt, csv, html)
            exclude_dirs: Directories to exclude from scan
            
        Returns:
            Tuple of (success: bool, results: Dict)
        """
        
        if exclude_dirs is None:
            exclude_dirs = [
                ".git",
                ".venv",
                "venv",
                "env",
                "__pycache__",
                "node_modules",
                ".streamlit",
                "security_reports",
                ".pytest_cache"
            ]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.report_dir, f"bandit_report_{timestamp}.json")
        
        # Build Bandit command
        cmd = [
            "bandit",
            "-r", self.project_root,  # Recursive scan
            "-f", output_format,  # Output format
            "-o", output_file,  # Output file
            "-ll",  # Report all severity levels (we'll filter in code)
        ]
        
        # Add exclusions
        for exclude in exclude_dirs:
            cmd.extend(["-x", os.path.join(self.project_root, exclude)])
        
        print(f"🔍 Running Bandit security scan...")
        print(f"   Scanning: {self.project_root}")
        print(f"   Excluding: {', '.join(exclude_dirs)}")
        print(f"   Severity: {severity_level}+")
        print(f"   Confidence: {confidence_level}+")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Bandit returns exit code 1 if issues found, 0 if clean
            # We consider both success for our purposes
            if result.returncode in [0, 1]:
                print(f"✅ Scan complete. Report saved to: {output_file}")
                
                # Parse results
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        scan_results = json.load(f)
                    return True, scan_results
                else:
                    return False, {"error": "Output file not created"}
            else:
                print(f"❌ Scan failed: {result.stderr}")
                return False, {"error": result.stderr}
        
        except subprocess.TimeoutExpired:
            print("❌ Scan timed out after 5 minutes")
            return False, {"error": "Scan timeout"}
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return False, {"error": str(e)}
    
    def parse_and_display_results(self, results: Dict, min_severity: str = "low", min_confidence: str = "low"):
        """
        Parse and display scan results
        
        Args:
            results: Bandit scan results (JSON)
            min_severity: Minimum severity to display (low, medium, high)
            min_confidence: Minimum confidence to display (low, medium, high)
        """
        
        severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        confidence_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        
        min_sev_level = severity_order.get(min_severity.upper(), 1)
        min_conf_level = confidence_order.get(min_confidence.upper(), 1)
        
        # Get metrics
        metrics = results.get("metrics", {})
        total_files = sum(metrics.values()) if isinstance(metrics, dict) else 0
        
        # Get issues
        issues = results.get("results", [])
        
        # Filter by severity and confidence
        filtered_issues = [
            issue for issue in issues
            if severity_order.get(issue.get("issue_severity", "LOW"), 0) >= min_sev_level
            and confidence_order.get(issue.get("issue_confidence", "LOW"), 0) >= min_conf_level
        ]
        
        # Count by severity
        high_count = sum(1 for i in filtered_issues if i.get("issue_severity") == "HIGH")
        medium_count = sum(1 for i in filtered_issues if i.get("issue_severity") == "MEDIUM")
        low_count = sum(1 for i in filtered_issues if i.get("issue_severity") == "LOW")
        
        print("\n" + "="*70)
        print("🔒 SECURITY SCAN RESULTS")
        print("="*70)
        print(f"Files scanned: {total_files}")
        print(f"Total issues: {len(filtered_issues)}")
        print(f"  🔴 HIGH severity: {high_count}")
        print(f"  🟠 MEDIUM severity: {medium_count}")
        print(f"  🟡 LOW severity: {low_count}")
        print("="*70 + "\n")
        
        if not filtered_issues:
            print("✅ No security issues found! Great job! 🎉\n")
            return
        
        # Display issues grouped by severity
        for severity in ["HIGH", "MEDIUM", "LOW"]:
            severity_issues = [i for i in filtered_issues if i.get("issue_severity") == severity]
            
            if not severity_issues:
                continue
            
            severity_icon = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}[severity]
            print(f"\n{severity_icon} {severity} SEVERITY ISSUES ({len(severity_issues)}):")
            print("-" * 70)
            
            for idx, issue in enumerate(severity_issues, 1):
                print(f"\n{idx}. {issue.get('test_id', 'N/A')}: {issue.get('issue_text', 'No description')}")
                print(f"   File: {issue.get('filename', 'Unknown')}")
                print(f"   Line: {issue.get('line_number', 'N/A')}")
                print(f"   Confidence: {issue.get('issue_confidence', 'Unknown')}")
                print(f"   CWE: {issue.get('issue_cwe', {}).get('id', 'N/A')}")
                
                # Show code snippet
                code = issue.get('code', '').strip()
                if code:
                    print(f"   Code:")
                    for line in code.split('\n')[:3]:  # Show first 3 lines
                        print(f"     {line}")
                
                # Show more info URL
                more_info = issue.get('more_info', '')
                if more_info:
                    print(f"   More info: {more_info}")
        
        print("\n" + "="*70 + "\n")
    
    def generate_summary_report(self, results: Dict) -> str:
        """
        Generate a summary report in Markdown format
        
        Returns:
            Path to the generated report
        """
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        issues = results.get("results", [])
        
        high_issues = [i for i in issues if i.get("issue_severity") == "HIGH"]
        medium_issues = [i for i in issues if i.get("issue_severity") == "MEDIUM"]
        low_issues = [i for i in issues if i.get("issue_severity") == "LOW"]
        
        report = f"""# Security Scan Report

**Generated:** {timestamp}  
**Scanner:** Bandit (Python SAST)  
**Project:** LeaseAI

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 HIGH | {len(high_issues)} |
| 🟠 MEDIUM | {len(medium_issues)} |
| 🟡 LOW | {len(low_issues)} |
| **TOTAL** | **{len(issues)}** |

---

## High Severity Issues

"""
        
        if high_issues:
            for idx, issue in enumerate(high_issues, 1):
                report += f"""
### {idx}. {issue.get('test_id', 'N/A')}: {issue.get('issue_text', 'No description')}

- **File:** `{issue.get('filename', 'Unknown')}`
- **Line:** {issue.get('line_number', 'N/A')}
- **Confidence:** {issue.get('issue_confidence', 'Unknown')}
- **CWE:** {issue.get('issue_cwe', {}).get('id', 'N/A')}

**Code:**
```python
{issue.get('code', 'N/A').strip()}
```

**More Info:** {issue.get('more_info', 'N/A')}

---
"""
        else:
            report += "\n✅ No high severity issues found.\n\n---\n"
        
        # Save report
        report_file = os.path.join(self.report_dir, f"security_summary_{datetime.now().strftime('%Y%m%d')}.md")
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"📄 Summary report saved to: {report_file}")
        return report_file


def main():
    """Main entry point for security scanner"""
    
    print("\n🔒 LeaseAI Security Scanner")
    print("="*70 + "\n")
    
    scanner = SecurityScanner(project_root=".")
    
    # Check if Bandit is installed
    if not scanner.check_bandit_installed():
        print("⚠️  Bandit not found. Installing...")
        if not scanner.install_bandit():
            print("❌ Failed to install Bandit. Please install manually:")
            print("   pip install bandit")
            sys.exit(1)
    
    # Run scan
    success, results = scanner.run_scan(
        severity_level="low",
        confidence_level="low"
    )
    
    if not success:
        print("❌ Security scan failed")
        sys.exit(1)
    
    # Display results
    scanner.parse_and_display_results(
        results,
        min_severity="low",
        min_confidence="medium"  # Only show medium+ confidence to reduce false positives
    )
    
    # Generate summary report
    scanner.generate_summary_report(results)
    
    # Determine exit code based on high severity issues
    high_issues = [i for i in results.get("results", []) if i.get("issue_severity") == "HIGH"]
    
    if high_issues:
        print(f"\n⚠️  {len(high_issues)} HIGH severity issues found!")
        print("   Please review and remediate before deployment.\n")
        sys.exit(1)
    else:
        print("\n✅ No high severity issues found. Security scan passed!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Comprehensive Test Runner for Notification Service

This script runs all tests with various options and generates detailed reports.
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime


class TestRunner:
    """Comprehensive test runner for the notification service"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = Path(__file__).parent
        self.start_time = None
        self.end_time = None

    def setup_django(self):
        """Setup Django environment for testing"""
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.test_settings')

        # Add project root to Python path
        sys.path.insert(0, str(self.project_root))
        sys.path.insert(0, str(self.test_dir))

        import django
        django.setup()

    def run_command(self, cmd, cwd=None, capture_output=True):
        """Run a shell command"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd or self.project_root,
                capture_output=capture_output,
                text=True,
                check=True
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {cmd}")
            print(f"Error: {e}")
            return e.stdout, e.stderr, e.returncode

    def create_test_database(self):
        """Create and setup test database"""
        print("Setting up test database...")

        # Run migrations
        stdout, stderr, code = self.run_command("python manage.py migrate --settings=notification_service.test_settings")
        if code != 0:
            print(f"Migration failed: {stderr}")
            return False

        print("Test database ready")
        return True

    def run_pytest(self, args=None):
        """Run tests with pytest"""
        cmd = ["python", "-m", "pytest"]

        if args:
            cmd.extend(args)

        # Add test directory
        cmd.append("tests/")

        # Add verbose output
        if "--verbose" not in cmd:
            cmd.extend(["-v", "--tb=short"])

        print(f"Running: {' '.join(cmd)}")
        self.start_time = time.time()

        stdout, stderr, code = self.run_command(" ".join(cmd))

        self.end_time = time.time()

        return stdout, stderr, code

    def run_coverage(self, args=None):
        """Run tests with coverage"""
        cmd = [
            "python", "-m", "pytest",
            "--cov=notifications",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ]

        if args:
            cmd.extend(args)

        cmd.append("tests/")

        print("Running tests with coverage...")
        stdout, stderr, code = self.run_command(" ".join(cmd))

        return stdout, stderr, code

    def run_specific_tests(self, test_type):
        """Run specific test categories"""
        test_mapping = {
            'models': 'tests/test_models.py',
            'channels': 'tests/test_channels.py',
            'api': 'tests/test_api.py',
            'websockets': 'tests/test_websockets.py',
            'events': 'tests/test_events.py',
            'chat': 'tests/test_chat.py',
        }

        if test_type in test_mapping:
            return self.run_pytest([test_mapping[test_type]])
        else:
            print(f"Unknown test type: {test_type}")
            return "", "", 1

    def generate_report(self, stdout, stderr, code):
        """Generate test report"""
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0

        report = f"""
{'='*60}
NOTIFICATION SERVICE TEST REPORT
{'='*60}

Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Duration: {duration:.2f} seconds
Result: {'PASSED' if code == 0 else 'FAILED'}

"""

        if code == 0:
            report += "All tests passed successfully!\n"
        else:
            report += "Some tests failed. Check the output above for details.\n"

        # Save report to file
        report_file = self.test_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
            if stdout:
                f.write("\nSTDOUT:\n")
                f.write(stdout)
            if stderr:
                f.write("\nSTDERR:\n")
                f.write(stderr)

        print(f"Report saved to: {report_file}")

        return report

    def run_all_tests(self):
        """Run complete test suite"""
        print("Running Complete Notification Service Test Suite")
        print("=" * 60)

        # Setup
        self.setup_django()
        if not self.create_test_database():
            return 1

        # Run all tests
        stdout, stderr, code = self.run_pytest([
            "--durations=10",
            "--strict-markers",
            "-x",  # Stop on first failure
        ])

        # Generate report
        self.generate_report(stdout, stderr, code)

        return code

    def run_with_coverage(self):
        """Run tests with coverage analysis"""
        print("Running Tests with Coverage Analysis")
        print("=" * 60)

        self.setup_django()
        if not self.create_test_database():
            return 1

        stdout, stderr, code = self.run_coverage([
            "--durations=10",
            "-x",
        ])

        if code == 0:
            print("Coverage report generated in htmlcov/index.html")

        return code


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Notification Service Test Runner')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage analysis')
    parser.add_argument('--type', choices=['models', 'channels', 'api', 'websockets', 'events', 'chat'],
                       help='Run specific test type')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fail-fast', '-x', action='store_true', help='Stop on first failure')
    parser.add_argument('--keepdb', action='store_true', help='Keep test database')

    args = parser.parse_args()

    runner = TestRunner()

    try:
        if args.coverage:
            exit_code = runner.run_with_coverage()
        elif args.type:
            stdout, stderr, exit_code = runner.run_specific_tests(args.type)
            if exit_code != 0:
                print(stderr)
        else:
            exit_code = runner.run_all_tests()

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Test runner error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
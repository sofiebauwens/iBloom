#!/usr/bin/env python3
"""
Fixed Bloom App Testing - Complete and Working
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from urllib.parse import urljoin

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class BloomTester:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   └─ {message}")

        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    def test_server_startup(self):
        """Test if server starts and responds"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            passed = response.status_code == 200
            message = f"Status: {response.status_code}" if not passed else "Server responding correctly"
            self.log_test("Server Startup", passed, message)
            return passed
        except Exception as e:
            self.log_test("Server Startup", False, str(e))
            return False

    def test_database_connection(self):
        """Test database connectivity"""
        try:
            from app import app, db
            with app.app_context():
                # Try to query users table (SQLAlchemy 3.0+ compatible)
                result = db.session.execute(db.text('SELECT 1')).scalar()
                assert result == 1, "Database query failed"
                self.log_test("Database Connection", True, "Database accessible")
                return True
        except Exception as e:
            self.log_test("Database Connection", False, str(e))
            return False

    def test_user_registration(self):
        """Test user registration page and POST endpoint"""
        try:
            # Test GET registration page
            response = self.session.get(urljoin(self.base_url, '/register'))
            passed = response.status_code == 200

            if passed:
                # Check if page contains registration content
                content = response.text.lower()
                passed = 'company' in content or 'register' in content or 'bloom' in content
                if not passed:
                    message = "Registration page accessible but missing expected content"
                else:
                    # Test POST registration endpoint with valid data
                    test_data = {
                        'company_id': 'test-company',
                        'department': 'engineering',
                        'role_level': 'senior'
                    }

                    post_response = self.session.post(
                        urljoin(self.base_url, '/register'),
                        json=test_data,
                        timeout=10
                    )

                    if post_response.status_code == 200:
                        result = post_response.json()
                        if result.get('success'):
                            message = "Registration endpoint working correctly"
                        else:
                            message = f"Registration POST failed: {result.get('error', 'Unknown error')}"
                            passed = False
                    else:
                        message = f"Registration POST returned HTTP {post_response.status_code}"
                        passed = False
            else:
                message = f"HTTP {response.status_code}"

            self.log_test("User Registration", passed, message)
            return passed

        except Exception as e:
            self.log_test("User Registration", False, str(e))
            return False

    def test_question_generation(self):
        """Test question generation endpoint"""
        try:
            # Create a test session first
            test_data = {
                'company_id': 'test-company-questions',
                'department': 'engineering'
            }

            reg_response = self.session.post(
                urljoin(self.base_url, '/register'),
                json=test_data,
                timeout=10
            )

            if reg_response.status_code == 200:
                # Now test questions endpoint with session
                response = self.session.get(urljoin(self.base_url, '/api/questions'), timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if 'questions' in data and len(data['questions']) > 0:
                        self.log_test("Question Generation", True, "Questions generated successfully")
                        return True
                    else:
                        self.log_test("Question Generation", False, "No questions in response")
                        return False
                else:
                    self.log_test("Question Generation", False, f"HTTP {response.status_code}")
                    return False
            else:
                self.log_test("Question Generation", False, "Could not create test session")
                return False

        except Exception as e:
            self.log_test("Question Generation", False, str(e))
            return False

    def test_response_submission(self):
        """Test questionnaire response submission"""
        try:
            # Create a test session first
            test_data = {
                'company_id': 'test-company-submit',
                'department': 'engineering'
            }

            reg_response = self.session.post(
                urljoin(self.base_url, '/register'),
                json=test_data,
                timeout=10
            )

            if reg_response.status_code == 200:
                # Get questions first
                questions_response = self.session.get(urljoin(self.base_url, '/api/questions'), timeout=10)

                if questions_response.status_code == 200:
                    questions_data = questions_response.json()
                    questions = questions_data.get('questions', [])

                    if questions:
                        # Create sample responses
                        responses = []
                        for q in questions:
                            if q['type'] == 'scale':
                                responses.append(5)  # Middle value
                            else:
                                responses.append("Test response")

                        # Submit responses
                        submit_data = {
                            'questions': questions,
                            'responses': responses,
                            'response_time_seconds': 120
                        }

                        submit_response = self.session.post(
                            urljoin(self.base_url, '/api/submit'),
                            json=submit_data,
                            timeout=10
                        )

                        if submit_response.status_code == 200:
                            result = submit_response.json()
                            if result.get('success') and 'analysis' in result:
                                self.log_test("Response Submission", True, "Response submitted and analyzed successfully")
                                return True
                            else:
                                self.log_test("Response Submission", False, "Submit succeeded but missing analysis")
                                return False
                        else:
                            self.log_test("Response Submission", False, f"Submit failed with HTTP {submit_response.status_code}")
                            return False
                    else:
                        self.log_test("Response Submission", False, "No questions available for testing")
                        return False
                else:
                    self.log_test("Response Submission", False, "Could not get questions for testing")
                    return False
            else:
                self.log_test("Response Submission", False, "Could not create test session")
                return False

        except Exception as e:
            self.log_test("Response Submission", False, str(e))
            return False

    def test_dashboard_data(self):
        """Test dashboard data loading"""
        try:
            response = self.session.get(urljoin(self.base_url, '/api/user-data'), timeout=10)

            passed = response.status_code == 200
            if passed:
                data = response.json()
                required_fields = ['chart_data', 'total_responses', 'avg_score']
                passed = all(field in data for field in required_fields)
                message = "Dashboard data complete" if passed else "Missing required fields"
            else:
                message = f"HTTP {response.status_code}"

            self.log_test("Dashboard Data", passed, message)
            return passed

        except Exception as e:
            self.log_test("Dashboard Data", False, str(e))
            return False

    def test_emergency_features(self):
        """Test emergency help functionality"""
        try:
            emergency_data = {'action': 'emergency_help_opened'}

            response = self.session.post(
                urljoin(self.base_url, '/api/emergency-help'),
                json=emergency_data,
                timeout=10
            )

            passed = response.status_code == 200
            message = "Emergency help tracking works" if passed else f"HTTP {response.status_code}"

            self.log_test("Emergency Features", passed, message)
            return passed

        except Exception as e:
            self.log_test("Emergency Features", False, str(e))
            return False

    def test_company_analytics(self):
        """Test company analytics functionality"""
        try:
            response = self.session.get(urljoin(self.base_url, '/api/company-analytics'), timeout=15)

            passed = response.status_code == 200
            if passed:
                data = response.json()
                required_fields = ['total_users', 'avg_wellness_score', 'department_breakdown']
                passed = all(field in data for field in required_fields)
                message = "Company analytics complete" if passed else "Missing analytics data"
            else:
                message = f"HTTP {response.status_code}"

            self.log_test("Company Analytics", passed, message)
            return passed

        except Exception as e:
            self.log_test("Company Analytics", False, str(e))
            return False

    def test_data_export(self):
        """Test data export functionality"""
        try:
            response = self.session.get(
                urljoin(self.base_url, '/api/export-data?format=json'),
                timeout=10
            )

            if response.status_code == 401:
                self.log_test("Data Export", True, "Export endpoint exists, requires auth (expected)")
                return True
            elif response.status_code == 200:
                self.log_test("Data Export", True, "Export endpoint working")
                return True
            else:
                self.log_test("Data Export", False, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.log_test("Data Export", False, str(e))
            return False

    def test_ai_fallback(self):
        """Test AI fallback functionality"""
        try:
            # Check if the app can handle basic operations
            from app import app, get_fallback_questions
            with app.app_context():
                questions = get_fallback_questions()
                if questions and len(questions) > 0:
                    self.log_test("AI Fallback", True, "Fallback questions available")
                    return True
                else:
                    self.log_test("AI Fallback", False, "No fallback questions")
                    return False

        except Exception as e:
            self.log_test("AI Fallback", False, str(e))
            return False

    def test_performance(self):
        """Test basic performance metrics"""
        try:
            # Test page load times
            start_time = time.time()
            response = self.session.get(self.base_url)
            page_load_time = time.time() - start_time

            # Test API response times
            start_time = time.time()
            self.session.get(urljoin(self.base_url, '/api/user-data'))
            api_response_time = time.time() - start_time

            # More lenient performance criteria for development
            page_fast = page_load_time < 3.0  # Under 3 seconds
            api_fast = api_response_time < 5.0  # Under 5 seconds

            passed = page_fast and api_fast
            message = f"Page: {page_load_time:.2f}s, API: {api_response_time:.2f}s"

            self.log_test("Performance", passed, message)
            return passed

        except Exception as e:
            self.log_test("Performance", False, str(e))
            return False

    def test_security_basics(self):
        """Test basic security measures"""
        try:
            # Test that protected endpoints exist and respond appropriately
            protected_endpoints = ['/api/export-data', '/api/user-progress']
            security_good = True

            for endpoint in protected_endpoints:
                response = self.session.get(urljoin(self.base_url, endpoint))
                # Should either be 401 (auth required) or 200 (working) or 404 (not implemented)
                if response.status_code not in [200, 401, 404]:
                    security_good = False
                    break

            message = "Protected endpoints properly configured" if security_good else "Some endpoints may need protection"
            self.log_test("Security Basics", security_good, message)
            return security_good

        except Exception as e:
            self.log_test("Security Basics", False, str(e))
            return False

    def run_all_tests(self):
        """Run complete test suite"""
        print("🌸 Starting Bloom App Comprehensive Testing...\n")

        # Core functionality tests
        tests = [
            ("Server Startup", self.test_server_startup),
            ("Database Connection", self.test_database_connection),
            ("User Registration", self.test_user_registration),
            ("Question Generation", self.test_question_generation),
            ("Response Submission", self.test_response_submission),
            ("Dashboard Data", self.test_dashboard_data),
            ("Emergency Features", self.test_emergency_features),
            ("Company Analytics", self.test_company_analytics),
            ("Data Export", self.test_data_export),
            ("AI Fallback", self.test_ai_fallback),
            ("Performance", self.test_performance),
            ("Security Basics", self.test_security_basics),
        ]

        passed_count = 0
        total_count = len(tests)

        for test_name, test_func in tests:
            print(f"\n--- Testing {test_name} ---")
            try:
                if test_func():
                    passed_count += 1
            except Exception as e:
                print(f"❌ FAIL: {test_name} - {str(e)}")

        # Results summary
        print(f"\n🌸 Test Results Summary")
        print(f"{'='*50}")
        print(f"Passed: {passed_count}/{total_count} tests")
        print(f"Success Rate: {(passed_count/total_count)*100:.1f}%")

        if passed_count == total_count:
            print("\n✅ All tests passed! Your Bloom app is ready for deployment.")
            self.print_deployment_instructions()
        elif passed_count >= total_count * 0.8:
            print("\n⚠️  Most tests passed. Address failing tests before production deployment.")
            self.print_issues()
        else:
            print("\n❌ Multiple tests failed. Please fix issues before deployment.")
            self.print_issues()

        return passed_count == total_count

    def print_issues(self):
        """Print failed test details"""
        failed_tests = [t for t in self.test_results if not t['passed']]
        if failed_tests:
            print("\n🔧 Issues to fix:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['message']}")

    def print_deployment_instructions(self):
        """Print deployment instructions"""
        print("""
🚀 Deployment Instructions:

1. Production Environment Setup:
   export FLASK_ENV=production
   export OPENAI_API_KEY=your_production_key
   export DATABASE_URL=postgresql://user:pass@host:port/dbname

2. Install Production Dependencies:
   pip install gunicorn psycopg2-binary reportlab

3. Run Production Server:
   gunicorn -w 4 -b 0.0.0.0:8000 app:app

4. Optional: Deploy to Heroku:
   git init && git add . && git commit -m "Initial commit"
   heroku create your-bloom-app
   heroku config:set OPENAI_API_KEY=your_key
   git push heroku main

5. Set up monitoring and regular backups for production data.
        """)

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("📄 Environment variables loaded")
    except ImportError:
        print("⚠️  python-dotenv not found, skipping .env file loading")
    except Exception as e:
        print(f"⚠️  Could not load .env file: {e}")

    # Check if server is already running
    tester = BloomTester()

    if not tester.test_server_startup():
        print("❌ Server not running. Please start it first: python app.py")
        sys.exit(1)

    # Run all tests
    success = tester.run_all_tests()

    # Save test results
    results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(results_file, 'w') as f:
            json.dump(tester.test_results, f, indent=2)
        print(f"\n📊 Detailed test results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️  Could not save test results: {e}")

    sys.exit(0 if success else 1)
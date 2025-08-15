"""
Comprehensive Test Suite for Spring Boot Log Analyzer

This module provides comprehensive testing for all components of the agentic application:
- Log Analysis Agent
- Code Fixing Agent  
- Multi-Agent Orchestrator
- End-to-end workflow testing
"""

import os
import json
import unittest
from typing import List, Dict, Any

from log_analysis_agent import LogAnalysisAgent, ExceptionInfo
from code_fixing_agent import CodeFixingAgent, CodeFix
from multi_agent_orchestrator import SpringBootLogAnalyzer


class TestLogAnalysisAgent(unittest.TestCase):
    """Test cases for the Log Analysis Agent"""
    
    def setUp(self):
        self.agent = LogAnalysisAgent()
        self.sample_log_path = "sample_spring_boot.log"
    
    def test_log_file_reading(self):
        """Test that log files can be read successfully"""
        self.assertTrue(os.path.exists(self.sample_log_path))
        lines = self.agent.read_log_file(self.sample_log_path)
        self.assertGreater(len(lines), 0)
        self.assertIsInstance(lines, list)
    
    def test_log_line_parsing(self):
        """Test parsing of individual log lines"""
        # Test Spring Boot format
        spring_line = "2024-07-23 10:15:30.123  INFO 12345 --- [main] com.example.Application : Starting Application"
        parsed = self.agent.parse_log_line(spring_line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['level'], 'INFO')
        self.assertIn('timestamp', parsed)
        
        # Test empty line
        empty_parsed = self.agent.parse_log_line("")
        self.assertIsNone(empty_parsed)
    
    def test_exception_detection(self):
        """Test detection of exception lines"""
        # Positive cases
        self.assertTrue(self.agent.is_exception_line("java.lang.NullPointerException: Cannot invoke"))
        self.assertTrue(self.agent.is_exception_line("Caused by: java.sql.SQLException"))
        self.assertTrue(self.agent.is_exception_line("org.springframework.dao.DataAccessResourceFailureException"))
        
        # Negative cases (stack trace lines should not be detected as new exceptions)
        self.assertFalse(self.agent.is_exception_line("at com.example.service.UserService.validateUser"))
        self.assertFalse(self.agent.is_exception_line("... 23 more"))
        self.assertFalse(self.agent.is_exception_line("Starting Application on localhost"))
    
    def test_full_log_analysis(self):
        """Test complete log file analysis"""
        exceptions = self.agent.analyze_log_file(self.sample_log_path)
        
        self.assertIsInstance(exceptions, list)
        self.assertGreater(len(exceptions), 0)
        
        # Check that we have ExceptionInfo objects
        for exc in exceptions:
            self.assertIsInstance(exc, ExceptionInfo)
            self.assertIsInstance(exc.exception_type, str)
            self.assertIsInstance(exc.exception_message, str)
            self.assertIsInstance(exc.stack_trace, list)
    
    def test_analyze_logs_tool(self):
        """Test the tool interface for log analysis"""
        result = self.agent.analyze_logs(self.sample_log_path)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertGreater(result['total_exceptions'], 0)
        self.assertIn('exceptions', result)


class TestCodeFixingAgent(unittest.TestCase):
    """Test cases for the Code Fixing Agent"""
    
    def setUp(self):
        self.agent = CodeFixingAgent()
        self.log_agent = LogAnalysisAgent()
        
        # Get sample exceptions for testing
        self.exceptions = self.log_agent.analyze_log_file("sample_spring_boot.log")
        self.main_exceptions = [exc for exc in self.exceptions if exc.stack_trace and len(exc.stack_trace) > 5]
    
    def test_single_exception_analysis(self):
        """Test analysis of a single exception"""
        if self.main_exceptions:
            exception = self.main_exceptions[0]
            fix = self.agent.analyze_exception(exception)
            
            self.assertIsInstance(fix, CodeFix)
            self.assertEqual(fix.exception_type, exception.exception_type)
            self.assertIsInstance(fix.root_cause, str)
            self.assertIsInstance(fix.fix_description, str)
            self.assertIsInstance(fix.code_suggestions, list)
            self.assertIsInstance(fix.prevention_tips, list)
            self.assertIsInstance(fix.confidence_score, float)
            self.assertGreaterEqual(fix.confidence_score, 0.0)
            self.assertLessEqual(fix.confidence_score, 1.0)
    
    def test_multiple_exceptions_analysis(self):
        """Test analysis of multiple exceptions"""
        if self.main_exceptions:
            fixes = self.agent.analyze_multiple_exceptions(self.main_exceptions[:3])  # Test first 3
            
            self.assertIsInstance(fixes, list)
            self.assertEqual(len(fixes), min(3, len(self.main_exceptions)))
            
            for fix in fixes:
                self.assertIsInstance(fix, CodeFix)
    
    def test_fix_report_formatting(self):
        """Test formatting of fix reports"""
        if self.main_exceptions:
            exception = self.main_exceptions[0]
            fix = self.agent.analyze_exception(exception)
            report = self.agent.format_fix_report(fix)
            
            self.assertIsInstance(report, str)
            self.assertIn("CODE FIX ANALYSIS", report)
            self.assertIn(fix.exception_type, report)
    
    def test_fix_exceptions_tool(self):
        """Test the tool interface for code fixing"""
        if self.main_exceptions:
            # Convert exceptions to dictionaries
            exceptions_data = []
            for exc in self.main_exceptions[:2]:  # Test first 2
                exc_dict = {
                    "timestamp": exc.timestamp,
                    "log_level": exc.log_level,
                    "exception_type": exc.exception_type,
                    "exception_message": exc.exception_message,
                    "stack_trace": exc.stack_trace,
                    "surrounding_context": exc.surrounding_context,
                    "file_path": exc.file_path,
                    "line_number": exc.line_number,
                    "method_name": exc.method_name,
                    "class_name": exc.class_name
                }
                exceptions_data.append(exc_dict)
            
            result = self.agent.fix_exceptions(exceptions_data)
            
            self.assertIsInstance(result, dict)
            self.assertTrue(result['success'])
            self.assertEqual(result['total_exceptions'], len(exceptions_data))
            self.assertGreater(result['total_fixes'], 0)


class TestMultiAgentOrchestrator(unittest.TestCase):
    """Test cases for the Multi-Agent Orchestrator"""
    
    def setUp(self):
        self.analyzer = SpringBootLogAnalyzer()
        self.sample_log_path = "sample_spring_boot.log"
    
    def test_workflow_initialization(self):
        """Test that the workflow is properly initialized"""
        self.assertIsNotNone(self.analyzer.workflow)
        self.assertIsNotNone(self.analyzer.log_agent)
        self.assertIsNotNone(self.analyzer.fix_agent)
        self.assertIsNotNone(self.analyzer.supervisor_llm)
    
    def test_complete_workflow(self):
        """Test the complete end-to-end workflow"""
        result = self.analyzer.analyze_log_file(self.sample_log_path)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['log_file_path'], self.sample_log_path)
        self.assertGreater(result['total_exceptions'], 0)
        self.assertGreater(result['total_fixes'], 0)
        self.assertIsInstance(result['exceptions'], list)
        self.assertIsInstance(result['fixes'], list)
        self.assertIsInstance(result['messages'], list)
        
        # Check that workflow messages are present
        message_roles = [msg['role'] for msg in result['messages']]
        self.assertIn('supervisor', message_roles)
        self.assertIn('log_analyst', message_roles)
        self.assertIn('code_fixer', message_roles)
        self.assertIn('reporter', message_roles)
    
    def test_nonexistent_file_handling(self):
        """Test handling of non-existent log files"""
        result = self.analyzer.analyze_log_file("nonexistent_file.log")
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('not found', result['error'])
    
    def test_report_generation(self):
        """Test that analysis reports are generated"""
        result = self.analyzer.analyze_log_file(self.sample_log_path)
        
        if result['success']:
            # Check if report file was created
            expected_report_path = f"analysis_report_{os.path.basename(self.sample_log_path)}.md"
            self.assertTrue(os.path.exists(expected_report_path))
            
            # Check report content
            with open(expected_report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            self.assertIn("Spring Boot Log Analysis Report", report_content)
            self.assertIn("Exception Analysis", report_content)
            self.assertIn("Code Fix Recommendations", report_content)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        self.analyzer = SpringBootLogAnalyzer()
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow with validation"""
        # Run the complete analysis
        result = self.analyzer.analyze_log_file("sample_spring_boot.log")
        
        # Validate overall success
        self.assertTrue(result['success'], f"Workflow failed: {result.get('error', 'Unknown error')}")
        
        # Validate log analysis results
        self.assertGreater(result['total_exceptions'], 0, "No exceptions found in log file")
        
        # Validate code fixing results
        self.assertGreater(result['total_fixes'], 0, "No code fixes generated")
        
        # Validate that fixes correspond to exceptions
        self.assertLessEqual(result['total_fixes'], result['total_exceptions'], 
                           "More fixes than exceptions (unexpected)")
        
        # Validate message flow
        messages = result['messages']
        self.assertGreater(len(messages), 0, "No workflow messages generated")
        
        # Check for expected workflow progression
        supervisor_messages = [msg for msg in messages if msg['role'] == 'supervisor']
        self.assertGreater(len(supervisor_messages), 0, "No supervisor messages found")
        
        # Validate exceptions data structure
        for exc in result['exceptions']:
            self.assertIn('exception_type', exc)
            self.assertIn('exception_message', exc)
            self.assertIn('stack_trace', exc)
        
        # Validate fixes data structure
        for fix in result['fixes']:
            self.assertIn('exception_type', fix)
            self.assertIn('root_cause', fix)
            self.assertIn('fix_description', fix)
            self.assertIn('code_suggestions', fix)
            self.assertIn('confidence_score', fix)
            
            # Validate confidence score range
            self.assertGreaterEqual(fix['confidence_score'], 0.0)
            self.assertLessEqual(fix['confidence_score'], 1.0)


def create_additional_test_log():
    """Create an additional test log file with different exception types"""
    
    additional_log_content = """2024-07-23 11:00:00.000  INFO 54321 --- [main] com.example.TestApplication : Starting TestApplication
2024-07-23 11:00:01.123 ERROR 54321 --- [http-nio-8080-exec-1] c.e.service.ValidationService : Validation failed
java.lang.IllegalStateException: Service not initialized
	at com.example.service.ValidationService.validate(ValidationService.java:23)
	at com.example.controller.ValidationController.validateRequest(ValidationController.java:45)
	at java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
	... 15 more
2024-07-23 11:00:02.456 ERROR 54321 --- [http-nio-8080-exec-2] c.e.repository.UserRepository : Database query failed
java.sql.SQLTimeoutException: Query timeout expired
	at com.mysql.cj.jdbc.StatementImpl.executeQuery(StatementImpl.java:1234)
	at com.example.repository.UserRepository.findByEmail(UserRepository.java:67)
	at com.example.service.UserService.getUserByEmail(UserService.java:89)
	... 12 more
2024-07-23 11:00:03.789 ERROR 54321 --- [scheduler-1] c.e.scheduler.BackupScheduler : Backup operation failed
java.io.FileNotFoundException: /backup/data.sql (No such file or directory)
	at java.base/java.io.FileInputStream.open0(Native Method)
	at java.base/java.io.FileInputStream.open(FileInputStream.java:219)
	at com.example.scheduler.BackupScheduler.performBackup(BackupScheduler.java:34)
	... 8 more
2024-07-23 11:00:04.012  INFO 54321 --- [main] com.example.TestApplication : Application started successfully
"""
    
    with open("additional_test.log", "w", encoding="utf-8") as f:
        f.write(additional_log_content)
    
    return "additional_test.log"


def run_comprehensive_tests():
    """Run all tests and generate a comprehensive test report"""
    
    print("=" * 60)
    print("SPRING BOOT LOG ANALYZER - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Create additional test data
    additional_log_path = create_additional_test_log()
    print(f"Created additional test log: {additional_log_path}")
    
    # Run unit tests
    print("\n1. Running Unit Tests...")
    print("-" * 30)
    
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestLogAnalysisAgent))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestCodeFixingAgent))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestMultiAgentOrchestrator))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(test_suite)
    
    # Test additional log file
    print("\n2. Testing Additional Log File...")
    print("-" * 30)
    
    analyzer = SpringBootLogAnalyzer()
    additional_result = analyzer.analyze_log_file(additional_log_path)
    
    print(f"Additional log analysis:")
    print(f"  Success: {additional_result['success']}")
    print(f"  Exceptions found: {additional_result['total_exceptions']}")
    print(f"  Fixes generated: {additional_result['total_fixes']}")
    
    if additional_result.get('error'):
        print(f"  Error: {additional_result['error']}")
    
    # Performance test
    print("\n3. Performance Test...")
    print("-" * 30)
    
    import time
    start_time = time.time()
    
    performance_result = analyzer.analyze_log_file("sample_spring_boot.log")
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Exceptions processed: {performance_result['total_exceptions']}")
    print(f"Fixes generated: {performance_result['total_fixes']}")
    
    if execution_time > 0:
        print(f"Processing rate: {performance_result['total_exceptions'] / execution_time:.2f} exceptions/second")
    
    # Summary
    print("\n4. Test Summary")
    print("-" * 30)
    
    total_tests = test_result.testsRun
    failures = len(test_result.failures)
    errors = len(test_result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total tests run: {total_tests}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    print(f"Success rate: {success_rate:.1f}%")
    
    if failures == 0 and errors == 0:
        print("\n✅ ALL TESTS PASSED! The application is working correctly.")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    print("\n" + "=" * 60)
    
    return test_result, additional_result


if __name__ == "__main__":
    run_comprehensive_tests()


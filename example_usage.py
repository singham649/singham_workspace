#!/usr/bin/env python3
"""
Example Usage Script for Spring Boot Log Analyzer

This script demonstrates various ways to use the Spring Boot Log Analyzer
agentic application for analyzing log files and generating code fixes.
"""

import os
import sys
from typing import Dict, Any, List
from multi_agent_orchestrator import SpringBootLogAnalyzer


def example_basic_analysis():
    """Example 1: Basic log file analysis"""
    print("=" * 60)
    print("EXAMPLE 1: Basic Log File Analysis")
    print("=" * 60)
    
    # Initialize the analyzer
    analyzer = SpringBootLogAnalyzer()
    
    # Analyze the sample log file
    log_file = "sample_spring_boot.log"
    
    if not os.path.exists(log_file):
        print(f"Error: Sample log file '{log_file}' not found!")
        return
    
    print(f"Analyzing log file: {log_file}")
    result = analyzer.analyze_log_file(log_file)
    
    # Display results
    if result['success']:
        print(f"✅ Analysis completed successfully!")
        print(f"📊 Total exceptions found: {result['total_exceptions']}")
        print(f"🔧 Code fixes generated: {result['total_fixes']}")
        print(f"📝 Report generated: analysis_report_{os.path.basename(log_file)}.md")
        
        # Show first exception details
        if result['exceptions']:
            first_exc = result['exceptions'][0]
            print(f"\n📋 First Exception Details:")
            print(f"   Type: {first_exc['exception_type']}")
            print(f"   Message: {first_exc['exception_message'][:100]}...")
            print(f"   Stack trace lines: {len(first_exc['stack_trace'])}")
        
        # Show first fix details
        if result['fixes']:
            first_fix = result['fixes'][0]
            print(f"\n🔧 First Fix Details:")
            print(f"   Root cause: {first_fix['root_cause'][:100]}...")
            print(f"   Confidence: {first_fix['confidence_score']:.2f}")
            print(f"   Code suggestions: {len(first_fix['code_suggestions'])}")
    else:
        print(f"❌ Analysis failed: {result['error']}")


def example_detailed_exception_analysis():
    """Example 2: Detailed analysis of specific exceptions"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Detailed Exception Analysis")
    print("=" * 60)
    
    from log_analysis_agent import LogAnalysisAgent
    from code_fixing_agent import CodeFixingAgent
    
    # Initialize agents
    log_agent = LogAnalysisAgent()
    fix_agent = CodeFixingAgent()
    
    # Analyze log file
    log_file = "sample_spring_boot.log"
    exceptions = log_agent.analyze_log_file(log_file)
    
    # Filter to main exceptions only
    main_exceptions = [exc for exc in exceptions if exc.stack_trace and len(exc.stack_trace) > 5]
    
    print(f"Found {len(main_exceptions)} main exceptions to analyze:")
    
    for i, exc in enumerate(main_exceptions[:3], 1):  # Analyze first 3
        print(f"\n--- Exception {i} ---")
        print(f"Type: {exc.exception_type}")
        print(f"Message: {exc.exception_message}")
        print(f"Location: {exc.class_name}.{exc.method_name}() at {exc.file_path}:{exc.line_number}")
        
        # Generate fix
        fix = fix_agent.analyze_exception(exc)
        print(f"Fix confidence: {fix.confidence_score:.2f}")
        print(f"Root cause: {fix.root_cause[:150]}...")
        
        if fix.code_suggestions:
            print(f"Code suggestions: {len(fix.code_suggestions)}")
            first_suggestion = fix.code_suggestions[0]
            print(f"  - File: {first_suggestion.get('file', 'Unknown')}")
            print(f"  - Description: {first_suggestion.get('description', 'No description')[:100]}...")


def example_batch_processing():
    """Example 3: Batch processing multiple log files"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Batch Processing Multiple Log Files")
    print("=" * 60)
    
    # Create a list of log files to process
    log_files = ["sample_spring_boot.log"]
    
    # Check if additional test log exists
    if os.path.exists("additional_test.log"):
        log_files.append("additional_test.log")
    
    analyzer = SpringBootLogAnalyzer()
    batch_results = []
    
    print(f"Processing {len(log_files)} log files...")
    
    for log_file in log_files:
        print(f"\n📁 Processing: {log_file}")
        
        if not os.path.exists(log_file):
            print(f"   ❌ File not found: {log_file}")
            continue
        
        result = analyzer.analyze_log_file(log_file)
        
        batch_result = {
            'file': log_file,
            'success': result['success'],
            'exceptions': result['total_exceptions'],
            'fixes': result['total_fixes'],
            'error': result.get('error', '')
        }
        
        batch_results.append(batch_result)
        
        if result['success']:
            print(f"   ✅ Success: {result['total_exceptions']} exceptions, {result['total_fixes']} fixes")
        else:
            print(f"   ❌ Failed: {result['error']}")
    
    # Summary
    print(f"\n📊 Batch Processing Summary:")
    total_exceptions = sum(r['exceptions'] for r in batch_results if r['success'])
    total_fixes = sum(r['fixes'] for r in batch_results if r['success'])
    successful_files = sum(1 for r in batch_results if r['success'])
    
    print(f"   Files processed: {len(batch_results)}")
    print(f"   Successful: {successful_files}")
    print(f"   Total exceptions: {total_exceptions}")
    print(f"   Total fixes: {total_fixes}")


def example_custom_log_analysis():
    """Example 4: Custom log analysis with filtering"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Custom Log Analysis with Filtering")
    print("=" * 60)
    
    from log_analysis_agent import LogAnalysisAgent
    
    log_agent = LogAnalysisAgent()
    log_file = "sample_spring_boot.log"
    
    # Get all exceptions
    all_exceptions = log_agent.analyze_log_file(log_file)
    
    # Filter by exception type
    null_pointer_exceptions = [exc for exc in all_exceptions if 'NullPointerException' in exc.exception_type]
    sql_exceptions = [exc for exc in all_exceptions if 'SQLException' in exc.exception_type]
    io_exceptions = [exc for exc in all_exceptions if 'IOException' in exc.exception_type]
    
    print(f"Exception Type Analysis:")
    print(f"  Total exceptions: {len(all_exceptions)}")
    print(f"  NullPointerExceptions: {len(null_pointer_exceptions)}")
    print(f"  SQL Exceptions: {len(sql_exceptions)}")
    print(f"  IO Exceptions: {len(io_exceptions)}")
    
    # Analyze most common exception types
    exception_types = {}
    for exc in all_exceptions:
        exc_type = exc.exception_type
        exception_types[exc_type] = exception_types.get(exc_type, 0) + 1
    
    print(f"\n📈 Most Common Exception Types:")
    sorted_types = sorted(exception_types.items(), key=lambda x: x[1], reverse=True)
    for exc_type, count in sorted_types[:5]:
        print(f"  {exc_type}: {count} occurrences")


def example_report_analysis():
    """Example 5: Analyzing generated reports"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Report Analysis")
    print("=" * 60)
    
    # Look for generated report files
    report_files = [f for f in os.listdir('.') if f.startswith('analysis_report_') and f.endswith('.md')]
    
    if not report_files:
        print("No analysis reports found. Run a basic analysis first.")
        return
    
    print(f"Found {len(report_files)} analysis reports:")
    
    for report_file in report_files:
        print(f"\n📄 Report: {report_file}")
        
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic report statistics
            lines = content.split('\n')
            sections = [line for line in lines if line.startswith('#')]
            code_blocks = content.count('```')
            
            print(f"   📊 Report Statistics:")
            print(f"     Total lines: {len(lines)}")
            print(f"     Sections: {len(sections)}")
            print(f"     Code blocks: {code_blocks // 2}")  # Each code block has opening and closing ```
            print(f"     File size: {len(content)} characters")
            
            # Show first few sections
            print(f"   📋 Sections:")
            for section in sections[:5]:
                print(f"     {section}")
            
        except Exception as e:
            print(f"   ❌ Error reading report: {e}")


def example_error_handling():
    """Example 6: Error handling and edge cases"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Error Handling and Edge Cases")
    print("=" * 60)
    
    analyzer = SpringBootLogAnalyzer()
    
    # Test 1: Non-existent file
    print("🧪 Test 1: Non-existent file")
    result = analyzer.analyze_log_file("non_existent_file.log")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result['error']}")
    
    # Test 2: Empty file
    print("\n🧪 Test 2: Empty file")
    empty_file = "empty_test.log"
    with open(empty_file, 'w') as f:
        f.write("")
    
    result = analyzer.analyze_log_file(empty_file)
    print(f"   Success: {result['success']}")
    print(f"   Exceptions found: {result['total_exceptions']}")
    
    # Clean up
    os.remove(empty_file)
    
    # Test 3: File with no exceptions
    print("\n🧪 Test 3: File with no exceptions")
    no_exceptions_file = "no_exceptions_test.log"
    with open(no_exceptions_file, 'w') as f:
        f.write("""2024-07-23 10:15:30.123  INFO 12345 --- [main] com.example.Application : Starting Application
2024-07-23 10:15:31.456  INFO 12345 --- [main] com.example.Application : Application started successfully
2024-07-23 10:15:32.789  INFO 12345 --- [main] com.example.Application : Ready to serve requests
""")
    
    result = analyzer.analyze_log_file(no_exceptions_file)
    print(f"   Success: {result['success']}")
    print(f"   Exceptions found: {result['total_exceptions']}")
    print(f"   Fixes generated: {result['total_fixes']}")
    
    # Clean up
    os.remove(no_exceptions_file)


def main():
    """Main function to run all examples"""
    print("🚀 Spring Boot Log Analyzer - Example Usage")
    print("This script demonstrates various features of the agentic application.\n")
    
    # Check if required files exist
    if not os.path.exists("sample_spring_boot.log"):
        print("❌ Error: sample_spring_boot.log not found!")
        print("Please ensure you're running this script from the correct directory.")
        sys.exit(1)
    
    # Check environment variables
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not found in environment variables.")
        print("Some examples may fail without a valid API key.")
        print("Set your API key: export GEMINI_API_KEY='your-key-here'\n")
    
    try:
        # Run all examples
        example_basic_analysis()
        example_detailed_exception_analysis()
        example_batch_processing()
        example_custom_log_analysis()
        example_report_analysis()
        example_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 All examples completed successfully!")
        print("Check the generated analysis reports for detailed results.")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Examples interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


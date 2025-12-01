#!/usr/bin/env python3
"""
Test script for code execution service.

Usage:
    uv run python scripts/test_code_execution.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from app.services.code_execution_service import SafeCodeExecutor, validate_code


def test_validation():
    """Test code validation."""
    print("=" * 60)
    print("Testing Code Validation")
    print("=" * 60)
    
    # Valid code
    valid_code = """
import pandas as pd
df = get_dataset('test')
result = df['rating'].mean()
print(f"Mean rating: {result}")
"""
    errors = validate_code(valid_code)
    print(f"✅ Valid code: {len(errors) == 0}")
    
    # Invalid - forbidden import
    invalid_import = """
import os
os.system('ls')
"""
    errors = validate_code(invalid_import)
    print(f"✅ Catches forbidden import (os): {len(errors) > 0}")
    print(f"   Errors: {errors}")
    
    # Invalid - exec call
    invalid_exec = """
exec("print('hacked')")
"""
    errors = validate_code(invalid_exec)
    print(f"✅ Catches exec call: {len(errors) > 0}")
    print(f"   Errors: {errors}")
    
    # Invalid - file access
    invalid_file = """
with open('/etc/passwd') as f:
    data = f.read()
"""
    errors = validate_code(invalid_file)
    print(f"✅ Catches file access: {len(errors) > 0}")
    print(f"   Errors: {errors}")
    
    # Invalid - network
    invalid_network = """
import requests
requests.get('http://evil.com')
"""
    errors = validate_code(invalid_network)
    print(f"✅ Catches network import: {len(errors) > 0}")
    print(f"   Errors: {errors}")
    
    # Invalid - dunder access
    invalid_dunder = """
x = []
x.__class__.__bases__[0].__subclasses__()
"""
    errors = validate_code(invalid_dunder)
    print(f"✅ Catches dunder exploitation: {len(errors) > 0}")
    print(f"   Errors: {errors}")


def test_execution():
    """Test code execution."""
    print("\n" + "=" * 60)
    print("Testing Code Execution")
    print("=" * 60)
    
    # Create executor with test data
    executor = SafeCodeExecutor()
    
    # Add test dataset
    test_df = pd.DataFrame({
        'id': range(100),
        'text': [f'Review {i}' for i in range(100)],
        'rating': [1, 2, 3, 4, 5] * 20,
        'source': ['g2', 'trustpilot'] * 50,
        'author': [f'user_{i}' for i in range(100)]
    })
    executor.add_dataset('test_dataset', test_df)
    
    # Test 1: Basic pandas operations
    print("\n1. Basic pandas operations:")
    code = """
df = get_dataset('test_dataset')
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
result = {"row_count": len(df), "columns": list(df.columns)}
"""
    result = executor.execute(code)
    print(f"   Success: {result.success}")
    print(f"   Output: {result.output[:200]}...")
    print(f"   Result: {result.result_data}")
    
    # Test 2: Groupby operations
    print("\n2. GroupBy operations:")
    code = """
df = get_dataset('test_dataset')
avg_by_source = df.groupby('source')['rating'].mean()
print(avg_by_source)
result = avg_by_source.to_dict()
"""
    result = executor.execute(code)
    print(f"   Success: {result.success}")
    print(f"   Output: {result.output}")
    print(f"   Result: {result.result_data}")
    
    # Test 3: NumPy operations
    print("\n3. NumPy operations:")
    code = """
import numpy as np
df = get_dataset('test_dataset')
ratings = df['rating'].values
result = {
    "mean": float(np.mean(ratings)),
    "std": float(np.std(ratings)),
    "median": float(np.median(ratings))
}
print(f"Stats: {result}")
"""
    result = executor.execute(code)
    print(f"   Success: {result.success}")
    print(f"   Result: {result.result_data}")
    
    # Test 4: DataFrame result
    print("\n4. DataFrame result:")
    code = """
df = get_dataset('test_dataset')
result = df.groupby('source').agg({
    'rating': ['mean', 'count'],
    'id': 'nunique'
}).reset_index()
print(result)
"""
    result = executor.execute(code)
    print(f"   Success: {result.success}")
    print(f"   Result type: {result.result_data.get('type') if result.result_data else None}")
    
    # Test 5: Malicious code should fail validation
    print("\n5. Security test - should fail:")
    code = """
import subprocess
subprocess.run(['ls', '-la'])
"""
    result = executor.execute(code)
    print(f"   Success (should be False): {result.success}")
    print(f"   Error: {result.error[:100] if result.error else 'None'}...")
    
    # Test 6: Helper functions
    print("\n6. Helper functions:")
    code = """
datasets = list_datasets()
print(f"Available datasets: {datasets}")

info = dataset_info('test_dataset')
print(f"Dataset info: {info}")
"""
    result = executor.execute(code)
    print(f"   Success: {result.success}")
    print(f"   Output: {result.output}")


def test_timeout():
    """Test execution timeout."""
    print("\n" + "=" * 60)
    print("Testing Timeout (this will take ~5 seconds)")
    print("=" * 60)
    
    executor = SafeCodeExecutor()
    
    # This should timeout (but we reduce the wait to not take too long in test)
    code = """
import time
time.sleep(5)  # Would timeout at 30s normally
print("Done!")
"""
    result = executor.execute(code)
    print(f"   Success: {result.success}")
    print(f"   Execution time: {result.execution_time:.2f}s")


if __name__ == "__main__":
    test_validation()
    test_execution()
    # Uncomment to test timeout:
    # test_timeout()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


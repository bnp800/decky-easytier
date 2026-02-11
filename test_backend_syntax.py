#!/usr/bin/env python3
"""
Backend Syntax and Structure Test for Decky EasyTier Plugin
Performs static analysis without requiring dependencies
"""

import ast
import sys
import os
from pathlib import Path

def check_python_syntax(file_path):
    """Check if Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"✓ {file_path} - Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {file_path} - Syntax Error: {e}")
        return False

def analyze_main_py_structure():
    """Analyze main.py structure and key components"""
    file_path = Path("main.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code)

    # Check for required classes
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    required_classes = ['DualProcessManager', 'EasyTierManager', 'Plugin']

    print("\n=== Class Structure Analysis ===")
    for cls in required_classes:
        if cls in classes:
            print(f"✓ Class '{cls}' found")
        else:
            print(f"✗ Class '{cls}' missing")

    # Check for required methods in Plugin class
    plugin_methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'Plugin':
            plugin_methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]

    required_methods = [
        '_main', '_unload', 'get_combined_status', 'install_easytier',
        'start_easytier', 'stop_easytier', 'save_plugin_settings'
    ]

    print("\n=== Plugin Class Methods ===")
    for method in required_methods:
        if method in plugin_methods:
            print(f"✓ Method '{method}' found")
        else:
            print(f"✗ Method '{method}' missing")

    # Check imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    print("\n=== Required Imports ===")
    required_imports = ['asyncio', 'json', 'pathlib', 'typing', 'decky']
    for imp in required_imports:
        if any(imp in i for i in imports):
            print(f"✓ Import '{imp}' found")
        else:
            print(f"✗ Import '{imp}' missing")

    return True

def check_error_handling():
    """Check for proper error handling patterns"""
    file_path = Path("main.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code)

    # Count try-except blocks
    try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
    print(f"\n=== Error Handling Analysis ===")
    print(f"✓ Found {len(try_blocks)} try-except blocks")

    # Check for specific error handling patterns
    has_generic_exception_handler = False
    for try_block in try_blocks:
        for handler in try_block.handlers:
            if handler.type is None:  # bare except
                has_generic_exception_handler = True
                break

    if has_generic_exception_handler:
        print("⚠ Warning: Found bare except clauses (should be more specific)")
    else:
        print("✓ No bare except clauses found")

    return True

def check_async_usage():
    """Check for proper async/await usage"""
    file_path = Path("main.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code)

    # Count async functions
    async_funcs = [node for node in ast.walk(tree)
                   if isinstance(node, ast.AsyncFunctionDef)]

    print(f"\n=== Async/Await Analysis ===")
    print(f"✓ Found {len(async_funcs)} async functions")

    # Check for await expressions
    await_exprs = [node for node in ast.walk(tree)
                   if isinstance(node, ast.Await)]
    print(f"✓ Found {len(await_exprs)} await expressions")

    return True

def run_static_tests():
    """Run all static tests"""
    print("=" * 60)
    print("Decky EasyTier Backend Static Analysis")
    print("=" * 60)

    # Check main.py syntax
    if not check_python_syntax("main.py"):
        return False

    # Additional checks
    analyze_main_py_structure()
    check_error_handling()
    check_async_usage()

    # Validate configuration files exist
    print("\n=== Configuration Files ===")
    required_files = ["plugin.json", "package.json", "main.py"]
    for file in required_files:
        if Path(file).exists():
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")

    print("\n" + "=" * 60)
    print("Static analysis completed!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    try:
        success = run_static_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Simple test script to validate dry-run functionality for KC New Restaurants.py

This script tests the argument parsing and basic dry-run behavior without 
requiring actual database connections or external data.
"""

import subprocess
import sys
import os

def test_dry_run_flag_parsing():
    """Test that dry-run flags are parsed correctly."""
    script_path = "KC New Restaurants.py"
    
    # Test different flag variations
    test_flags = [
        ["--dry-run", "--help"],
        ["--dryrun", "--help"], 
        ["-d", "--help"]
    ]
    
    print("Testing dry-run flag parsing...")
    
    for flags in test_flags:
        try:
            result = subprocess.run(
                [sys.executable, script_path] + flags,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Check if help output mentions dry-run
            if "dry-run" in result.stdout.lower():
                print(f"✓ Flag {flags[0]} parsed successfully")
            else:
                print(f"✗ Flag {flags[0]} not found in help output")
                
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout testing flag {flags[0]}")
        except Exception as e:
            print(f"✗ Error testing flag {flags[0]}: {e}")

def test_dry_run_banner():
    """Test that dry-run mode displays the safety banner."""
    script_path = "KC New Restaurants.py"
    
    print("\nTesting dry-run banner display...")
    
    try:
        # Use ephemeral mode to avoid database connections
        # Note: This will timeout but we can still check the partial output
        result = subprocess.run(
            [sys.executable, script_path, "--dry-run", "--ephemeral", "--nodelay"],
            capture_output=True,
            text=True,
            timeout=5  # Short timeout since we only need to check initial output
        )
        
        output = result.stdout + result.stderr
        
        # Check for dry-run banner
        if "*** DRY-RUN MODE: NO DATA WILL BE MODIFIED ***" in output:
            print("✓ Dry-run banner displayed correctly")
        else:
            print("✗ Dry-run banner not found in output")
            
        # Check for dry-run log messages
        if "DRY-RUN MODE ENABLED" in output:
            print("✓ Dry-run log messages present")
        else:
            print("✗ No dry-run log messages found")
            
    except subprocess.TimeoutExpired as e:
        # Expected - script takes longer than timeout, but we can check partial output
        stdout = e.stdout.decode('utf-8') if e.stdout else ""
        stderr = e.stderr.decode('utf-8') if e.stderr else ""
        output = stdout + stderr
        
        # Check for dry-run banner (goes to stdout, may not be flushed yet)
        # Note: stdout may be buffered, so we check stderr for log message as well
        if "*** DRY-RUN MODE: NO DATA WILL BE MODIFIED ***" in output:
            print("✓ Dry-run banner displayed correctly")
        elif "DRY-RUN MODE ENABLED" in output:
            print("✓ Dry-run mode active (banner in stdout may be buffered)")
        else:
            print("✗ Dry-run mode not detected")
            
        # Check for dry-run log messages  
        if "DRY-RUN MODE ENABLED" in output:
            print("✓ Dry-run log messages present")
        else:
            print("✗ No dry-run log messages found")
    except Exception as e:
        print(f"✗ Error during dry-run banner test: {e}")

def main():
    """Run all dry-run tests."""
    print("KC New Restaurants - Dry-Run Functionality Test")
    print("=" * 50)
    
    # Change to parent directory (project root) where the main script is located
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(script_dir)
    
    test_dry_run_flag_parsing()
    test_dry_run_banner()
    
    print("\nTest completed!")
    print("\nTo manually test dry-run mode:")
    print("  python3 'KC New Restaurants.py' --dry-run --ephemeral --nodelay")

if __name__ == "__main__":
    main()

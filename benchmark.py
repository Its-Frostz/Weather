#!/usr/bin/env python3
"""
Simple benchmark script for weather data processing
"""

import subprocess
import time
import os

def run_python_benchmark(runs=3):
    """Run Python benchmark multiple times."""
    print("Running Python benchmarks...")
    times = []
    
    for i in range(runs):
        print(f"  Run {i+1}/{runs}...", end="", flush=True)
        
        # Change to Cleaner directory and run Python script
        result = subprocess.run(['python', 'weather_cleaner_simple.py'], 
                              capture_output=True, text=True, cwd='./Cleaner')
        
        if result.returncode == 0:
            # Extract time from output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Processing time:' in line:
                    time_str = line.split(':')[1].strip().split()[0]
                    times.append(float(time_str))
                    print(f" {time_str}s")
                    break
        else:
            print(f" FAILED - {result.stderr}")
    
    return times

def run_cpp_benchmark(runs=3):
    """Run C++ benchmark multiple times."""
    print("Running C++ benchmarks...")
    times_buffered = []
    times_mapped = []
    
    for i in range(runs):
        print(f"  Run {i+1}/{runs}...", end="", flush=True)
        
        # Run buffered version from Cleaner directory
        result_buffered = subprocess.run(['.\weather_cleaner.exe'], 
                                      capture_output=True, text=True, cwd='./Cleaner', shell=True)
        
        # Run mapped version from Cleaner directory
        result_mapped = subprocess.run(['.\weather_cleaner_mapped.exe'], 
                                    capture_output=True, text=True, cwd='./Cleaner', shell=True)
        
        buffered_time = None
        mapped_time = None
        
        if result_buffered.returncode == 0:
            lines = result_buffered.stdout.split('\n')
            for line in lines:
                if 'Processing time:' in line and 'ms' in line:
                    time_ms = float(line.split(':')[1].strip().split()[0])
                    buffered_time = time_ms / 1000.0
                    break
        
        if result_mapped.returncode == 0:
            lines = result_mapped.stdout.split('\n')
            for line in lines:
                if 'Processing time:' in line and 'ms' in line:
                    time_ms = float(line.split(':')[1].strip().split()[0])
                    mapped_time = time_ms / 1000.0
                    break
        
        if buffered_time and mapped_time:
            times_buffered.append(buffered_time)
            times_mapped.append(mapped_time)
            print(f" Buffered: {buffered_time:.2f}s, Mapped: {mapped_time:.2f}s")
        else:
            print(f" FAILED - Buffered: {result_buffered.returncode}, Mapped: {result_mapped.returncode}")
    
    return times_buffered, times_mapped

def calculate_stats(times):
    """Calculate basic statistics."""
    if not times:
        return None
    
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    return {
        'avg': avg,
        'min': min_time,
        'max': max_time,
        'runs': len(times)
    }

def main():
    input_file = "Data/Raw/KIIT_University_Weather_3-1-24_12-00_AM_1_Year_1754733830_v2.csv"
    
    # Get file size
    file_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
    
    print("BENCHMARK RUNNER")
    print("=" * 50)
    print(f"Input file: {input_file}")
    print(f"File size: {file_size:.1f} MB")
    print()
    
    # Run Python benchmarks
    python_times = run_python_benchmark(3)
    print()
    
    # Run C++ benchmarks
    cpp_buffered, cpp_mapped = run_cpp_benchmark(3)
    print()
    
    # Calculate statistics
    print("RESULTS")
    print("=" * 50)
    
    # Prepare output for both console and file
    output_lines = []
    output_lines.append("BENCHMARK RESULTS")
    output_lines.append("=" * 50)
    output_lines.append(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append(f"Input file: {input_file}")
    output_lines.append(f"File size: {file_size:.1f} MB")
    output_lines.append(f"Total lines: 67,484")
    output_lines.append("")
    
    py_stats = calculate_stats(python_times)
    if py_stats:
        section = [
            "Python (Standard CSV):",
            f"  Raw times: {python_times}",
            f"  Average: {py_stats['avg']:.2f}s",
            f"  Best:    {py_stats['min']:.2f}s",
            f"  Worst:   {py_stats['max']:.2f}s",
            f"  Speed:   {67484 / py_stats['avg']:.0f} lines/sec",
            ""
        ]
        output_lines.extend(section)
    
    cpp_buf_stats = calculate_stats(cpp_buffered)
    if cpp_buf_stats:
        section = [
            "C++ (Buffered I/O):",
            f"  Raw times: {cpp_buffered}",
            f"  Average: {cpp_buf_stats['avg']:.2f}s",
            f"  Best:    {cpp_buf_stats['min']:.2f}s",
            f"  Worst:   {cpp_buf_stats['max']:.2f}s",
            f"  Speed:   {67484 / cpp_buf_stats['avg']:.0f} lines/sec",
            ""
        ]
        output_lines.extend(section)
    
    cpp_map_stats = calculate_stats(cpp_mapped)
    if cpp_map_stats:
        section = [
            "C++ (Memory-Mapped I/O):",
            f"  Raw times: {cpp_mapped}",
            f"  Average: {cpp_map_stats['avg']:.2f}s",
            f"  Best:    {cpp_map_stats['min']:.2f}s",
            f"  Worst:   {cpp_map_stats['max']:.2f}s",
            f"  Speed:   {67484 / cpp_map_stats['avg']:.0f} lines/sec",
            ""
        ]
        output_lines.extend(section)
    
    # Winner analysis
    winner_line = ""
    if py_stats and cpp_map_stats:
        if py_stats['avg'] < cpp_map_stats['avg']:
            improvement = ((cpp_map_stats['avg'] - py_stats['avg']) / cpp_map_stats['avg']) * 100
            winner_line = f"WINNER: Python is {improvement:.1f}% faster than C++ memory-mapped"
        else:
            improvement = ((py_stats['avg'] - cpp_map_stats['avg']) / py_stats['avg']) * 100
            winner_line = f"WINNER: C++ memory-mapped is {improvement:.1f}% faster than Python"
    
    if winner_line:
        output_lines.append(winner_line)
        print(winner_line)
    
    # Save to file
    output_file = "benchmark_results.txt"
    try:
        with open(output_file, 'w') as f:
            f.write('\n'.join(output_lines))
        print(f"\nResults saved to: {output_file}")
    except Exception as e:
        print(f"\nError saving to file: {e}")

if __name__ == "__main__":
    main()

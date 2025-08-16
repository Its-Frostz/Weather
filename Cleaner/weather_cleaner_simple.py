#!/usr/bin/env python3
"""
Simple Weather Data Cleaner using Standard Python CSV
Clean, fast, and reliable data preprocessing for ML.
"""

import csv
import time
import os


def detect_encoding(file_path):
    """Detect file encoding by trying common encodings."""
    encodings = ['utf-8', 'latin1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except UnicodeDecodeError:
            continue
    
    return 'latin1'


def clean_field(field):
    """Clean individual CSV field."""
    if not field:
        return "0"
    
    stripped = field.strip()
    
    if not stripped or stripped in ("-", "--"):
        return "0"
    
    return stripped


def process_weather_data(input_path, output_path):
    """Process weather data CSV file."""
    start_time = time.perf_counter()
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found")
        return False
    
    # Detect encoding
    encoding = detect_encoding(input_path)
    print(f"Detected encoding: {encoding}")
    
    try:
        with open(input_path, 'r', encoding=encoding) as input_file, \
             open(output_path, 'w', encoding='utf-8', newline='') as output_file:
            
            reader = csv.reader(input_file)
            writer = csv.writer(output_file)
            
            line_count = 0
            
            print("Processing weather data...")
            
            for row in reader:
                line_count += 1
                
                if line_count % 10000 == 0:
                    print(f"\rProcessed {line_count:,} lines...", end="", flush=True)
                
                # Clean each field in the row
                cleaned_row = [clean_field(field) for field in row]
                writer.writerow(cleaned_row)
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            print(f"\n\nProcessing completed successfully!")
            print(f"Lines processed: {line_count:,}")
            print(f"Processing time: {duration:.2f} seconds")
            print(f"Processing speed: {line_count / duration:.0f} lines/second")
            
            return True
            
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        return False


def validate_output(file_path, sample_lines=10):
    """Show sample lines from cleaned file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            print(f"\nSample from cleaned file:")
            print("-" * 80)
            
            for i, line in enumerate(file):
                if i >= sample_lines:
                    break
                
                display_line = line.rstrip('\n')
                if len(display_line) > 120:
                    display_line = display_line[:120] + "..."
                
                print(f"Line {i+1:2d}: {display_line}")
                
    except Exception as e:
        print(f"Error reading output file: {str(e)}")


def main():
    """Main function."""
    input_file = "../Data/Raw/KIIT_University_Weather_3-1-24_12-00_AM_1_Year_1754733830_v2.csv"
    output_file = "../Data/Cleaned/weather_data_cleaned_simple.csv"
    
    print("Weather Data Cleaner - Simple & Fast")
    print("=" * 40)
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print()
    
    if process_weather_data(input_file, output_file):
        # validate_output(output_file, 15)
        pass
        
    else:
        print("Failed to process the weather data file.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

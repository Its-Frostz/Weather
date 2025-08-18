#!/usr/bin/env python3
"""
Production-Grade Weather Data Interpolation System
==================================================
Advanced ML-ready data cleaning pipeline with linear interpolation,
statistical validation, and temporal coherence preservation.

Author: GitHub Copilot
Version: 1.0.0
"""

import csv
import time
import os
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass


@dataclass
class ColumnStats:
    """Statistical information for a data column."""
    name: str
    mean: float
    median: float
    min_val: float
    max_val: float
    q1: float
    q3: float
    missing_count: int
    total_count: int
    is_numeric: bool
    
    @property
    def missing_ratio(self) -> float:
        """Calculate the ratio of missing values."""
        return self.missing_count / self.total_count if self.total_count > 0 else 0.0
    
    @property
    def iqr(self) -> float:
        """Calculate the Interquartile Range."""
        return self.q3 - self.q1
    
    @property
    def lower_bound(self) -> float:
        """Calculate lower bound for outlier detection (Q1 - 1.5*IQR)."""
        return self.q1 - 1.5 * self.iqr
    
    @property
    def upper_bound(self) -> float:
        """Calculate upper bound for outlier detection (Q3 + 1.5*IQR)."""
        return self.q3 + 1.5 * self.iqr


class WeatherDataInterpolator:
    """
    Production-grade weather data cleaning system with linear interpolation.
    
    Features:
    - Smart encoding detection
    - Comprehensive missing value detection
    - Linear interpolation with statistical validation
    - Temporal coherence preservation
    - Outlier detection and bounds checking
    - Progress tracking and performance metrics
    """
    
    def __init__(self):
        """Initialize the interpolator with default settings."""
        self.missing_indicators = {
            '', '-', '--', '---', '----',           # Dash variants
            'n/a', 'na', 'null', 'nan', 'none',     # Standard missing
            'missing', 'unknown', '#n/a', '#null',  # Excel variants
            '?', 'nil', 'undefined', 'blank'        # Additional variants
        }
        
        self.stats_cache: Dict[str, ColumnStats] = {}
        self.processing_stats = {
            'total_rows': 0,
            'interpolated_values': 0,
            'fallback_values': 0,
            'processing_time': 0.0
        }
    
    def detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding by testing common encodings.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Best encoding detected
        """
        encodings = ['utf-8', 'latin1', 'cp1252', 'utf-16', 'ascii']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    # Read first 2KB to test encoding
                    f.read(2048)
                return encoding
            except UnicodeDecodeError:
                continue
        
        # Fallback to latin1 (accepts any byte sequence)
        return 'latin1'
    
    def is_missing_value(self, value: str) -> bool:
        """
        Check if a value represents missing data.
        
        Args:
            value: String value to check
            
        Returns:
            True if value is missing, False otherwise
        """
        if not value:
            return True
        
        # Strip whitespace and convert to lowercase
        cleaned = value.strip().lower()
        
        if not cleaned:
            return True
        
        return cleaned in self.missing_indicators
    
    def try_parse_number(self, value: str) -> Optional[float]:
        """
        Attempt to parse a string as a number.
        
        Args:
            value: String to parse
            
        Returns:
            Float value if successful, None if not numeric
        """
        if self.is_missing_value(value):
            return None
        
        try:
            # Remove common non-numeric characters but preserve decimal points
            cleaned = re.sub(r'[^\d\.\-\+eE]', '', value.strip())
            if cleaned:
                return float(cleaned)
        except (ValueError, TypeError):
            pass
        
        return None
    
    def calculate_column_stats(self, values: List[str]) -> ColumnStats:
        """
        Calculate comprehensive statistics for a column.
        
        Args:
            values: List of string values from the column
            
        Returns:
            ColumnStats object with all statistical measures
        """
        numeric_values = []
        missing_count = 0
        
        # Parse all values and count missing
        for value in values:
            parsed = self.try_parse_number(value)
            if parsed is not None:
                numeric_values.append(parsed)
            else:
                missing_count += 1
        
        total_count = len(values)
        is_numeric = len(numeric_values) > (total_count * 0.1)  # At least 10% numeric
        
        if not numeric_values or not is_numeric:
            # Non-numeric column
            return ColumnStats(
                name="", mean=0.0, median=0.0, min_val=0.0, max_val=0.0,
                q1=0.0, q3=0.0, missing_count=missing_count,
                total_count=total_count, is_numeric=False
            )
        
        # Sort for percentile calculations
        sorted_values = sorted(numeric_values)
        n = len(sorted_values)
        
        # Calculate statistics
        mean_val = sum(sorted_values) / n
        median_val = sorted_values[n // 2] if n % 2 == 1 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        min_val = sorted_values[0]
        max_val = sorted_values[-1]
        
        # Calculate quartiles
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_values[q1_idx] if q1_idx < n else sorted_values[-1]
        q3 = sorted_values[q3_idx] if q3_idx < n else sorted_values[-1]
        
        return ColumnStats(
            name="", mean=mean_val, median=median_val, min_val=min_val, max_val=max_val,
            q1=q1, q3=q3, missing_count=missing_count,
            total_count=total_count, is_numeric=True
        )
    
    def linear_interpolate(self, values: List[str], stats: ColumnStats) -> List[str]:
        """
        Apply linear interpolation to missing values in a column.
        
        Args:
            values: Original column values
            stats: Statistical information for the column
            
        Returns:
            List of interpolated values
        """
        if not stats.is_numeric:
            return values  # Skip non-numeric columns
        
        # Convert to (position, numeric_value) pairs
        numeric_data = []
        for i, value in enumerate(values):
            parsed = self.try_parse_number(value)
            numeric_data.append((i, parsed))
        
        # Find valid data points for interpolation
        valid_points = [(pos, val) for pos, val in numeric_data if val is not None]
        
        if len(valid_points) < 2:
            # Not enough points for interpolation, use median fallback
            fallback = stats.median
            result = []
            for pos, val in numeric_data:
                if val is not None:
                    result.append(str(val))
                else:
                    result.append(str(fallback))
                    self.processing_stats['fallback_values'] += 1
            return result
        
        # Create lookup dictionary for faster searches
        valid_dict = dict(valid_points)
        valid_positions = [pos for pos, _ in valid_points]
        valid_positions.sort()
        
        # Interpolate missing values
        result = [None] * len(values)
        
        for pos, val in numeric_data:
            if val is not None:
                # Keep existing valid value
                result[pos] = str(val)
            else:
                # Find surrounding valid points using binary search approach
                left_pos = None
                right_pos = None
                
                # Find nearest left and right positions
                for vpos in valid_positions:
                    if vpos < pos:
                        left_pos = vpos
                    elif vpos > pos and right_pos is None:
                        right_pos = vpos
                        break
                
                # Interpolate based on available points
                if left_pos is not None and right_pos is not None:
                    # Linear interpolation between two points
                    left_val = valid_dict[left_pos]
                    right_val = valid_dict[right_pos]
                    
                    # Calculate interpolated value
                    weight = (pos - left_pos) / (right_pos - left_pos)
                    interpolated = left_val + weight * (right_val - left_val)
                    
                    # Validate against statistical bounds
                    if interpolated < stats.lower_bound:
                        interpolated = max(stats.lower_bound, stats.min_val)
                    elif interpolated > stats.upper_bound:
                        interpolated = min(stats.upper_bound, stats.max_val)
                    
                    result[pos] = str(round(interpolated, 3))
                    self.processing_stats['interpolated_values'] += 1
                    
                elif left_pos is not None:
                    # Use last valid value (forward fill)
                    result[pos] = str(valid_dict[left_pos])
                    self.processing_stats['fallback_values'] += 1
                    
                elif right_pos is not None:
                    # Use next valid value (backward fill)
                    result[pos] = str(valid_dict[right_pos])
                    self.processing_stats['fallback_values'] += 1
                    
                else:
                    # No valid points found, use median
                    result[pos] = str(stats.median)
                    self.processing_stats['fallback_values'] += 1
        
        return result
    
    def analyze_columns(self, file_path: str, encoding: str, sample_size: int = 30000) -> Dict[int, ColumnStats]:
        """
        Analyze all columns in the dataset to build statistical foundation.
        
        Args:
            file_path: Path to the CSV file
            encoding: File encoding to use
            sample_size: Number of rows to sample for analysis
            
        Returns:
            Dictionary mapping column index to ColumnStats
        """
        print(f"Analyzing dataset structure (sampling up to {sample_size:,} rows)...")
        
        column_data: Dict[int, List[str]] = {}
        header_row = None
        data_start_idx = 0
        
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                reader = csv.reader(file)
                
                # Find the actual data header efficiently
                first_10_rows = []
                for i, row in enumerate(reader):
                    first_10_rows.append(row)
                    if i >= 10:
                        break
                
                # Find header row
                for i, row in enumerate(first_10_rows):
                    if any('temp' in str(cell).lower() or 'hum' in str(cell).lower() 
                          or 'date' in str(cell).lower() for cell in row):
                        header_row = row
                        data_start_idx = i + 1
                        break
                
                if not header_row:
                    header_row = max(first_10_rows, key=len) if first_10_rows else []
                    data_start_idx = 5  # Default start
                
                # Initialize column data storage
                num_columns = len(header_row)
                column_data = {i: [] for i in range(num_columns)}
                
                # Reset and collect sample data efficiently
                file.seek(0)
                reader = csv.reader(file)
                
                # Skip to data rows
                for i, row in enumerate(reader):
                    if i < data_start_idx:
                        continue
                    
                    if len(column_data[0]) >= sample_size:
                        break
                    
                    # Collect data for each column
                    for col_idx in range(min(len(row), num_columns)):
                        column_data[col_idx].append(row[col_idx])
        
        except Exception as e:
            print(f"Error during analysis: {e}")
            return {}
        
        # Calculate statistics for each column
        stats_dict = {}
        numeric_cols = 0
        
        for col_idx, values in column_data.items():
            if values:
                stats = self.calculate_column_stats(values)
                stats.name = header_row[col_idx] if col_idx < len(header_row) else f"Column_{col_idx}"
                stats_dict[col_idx] = stats
                
                if stats.is_numeric:
                    numeric_cols += 1
                    if stats.missing_ratio > 0:
                        print(f"  Column {col_idx:2d} ({stats.name[:30]:<30}): "
                              f"{stats.missing_ratio:6.1%} missing, "
                              f"range: {stats.min_val:8.2f} to {stats.max_val:8.2f}")
        
        print(f"Analysis complete. Found {numeric_cols} numeric columns.")
        return stats_dict
    
    def process_weather_data_production(self, input_path: str, output_path: str) -> bool:
        """
        Main processing function for production-grade weather data cleaning.
        
        Args:
            input_path: Path to input CSV file
            output_path: Path to output cleaned CSV file
            
        Returns:
            True if successful, False otherwise
        """
        start_time = time.perf_counter()
        
        # Validate input file
        if not os.path.exists(input_path):
            print(f"Error: Input file '{input_path}' not found")
            return False
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print("Weather Data Interpolation System")
        print("=" * 50)
        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        print()
        
        # Step 1: Detect encoding
        encoding = self.detect_encoding(input_path)
        print(f"✓ Detected encoding: {encoding}")
        
        # Step 2: Analyze columns for statistical foundation
        column_stats = self.analyze_columns(input_path, encoding)
        if not column_stats:
            print("Error: Failed to analyze dataset structure")
            return False
        
        print()
        
        try:
            # Step 3: Load and process all data
            print("Loading dataset for temporal interpolation...")
            
            with open(input_path, 'r', encoding=encoding) as input_file:
                reader = csv.reader(input_file)
                all_rows = list(reader)
            
            if not all_rows:
                print("Error: Empty dataset")
                return False
            
            self.processing_stats['total_rows'] = len(all_rows)
            print(f"✓ Loaded {len(all_rows):,} rows")
            
            # Find data start row
            data_start = 0
            for i, row in enumerate(all_rows):
                if len(row) > 10 and any('temp' in str(cell).lower() or 'date' in str(cell).lower() 
                                       for cell in row):
                    data_start = i + 1  # Skip header row
                    break
            
            print(f"✓ Data starts at row {data_start + 1}")
            
            # Step 4: Apply column-wise interpolation
            print(f"Applying interpolation to {len(column_stats)} columns...")
            
            for col_idx, stats in column_stats.items():
                if not stats.is_numeric:
                    continue
                
                print(f"\r  Processing column {col_idx:2d}: {stats.name[:40]:<40}", end="", flush=True)
                
                # Extract column values from data rows
                column_values = []
                for row_idx in range(data_start, len(all_rows)):
                    if col_idx < len(all_rows[row_idx]):
                        column_values.append(all_rows[row_idx][col_idx])
                    else:
                        column_values.append("")
                
                # Apply interpolation
                interpolated_values = self.linear_interpolate(column_values, stats)
                
                # Update original data
                for i, new_value in enumerate(interpolated_values):
                    row_idx = data_start + i
                    if row_idx < len(all_rows) and col_idx < len(all_rows[row_idx]):
                        all_rows[row_idx][col_idx] = new_value
            
            print("\n✓ Interpolation complete")
            
            # Step 5: Write cleaned data
            print("Writing cleaned dataset...")
            
            with open(output_path, 'w', encoding='utf-8', newline='') as output_file:
                writer = csv.writer(output_file)
                for row in all_rows:
                    writer.writerow(row)
            
            # Calculate final statistics
            end_time = time.perf_counter()
            self.processing_stats['processing_time'] = end_time - start_time
            
            print("\n" + "=" * 50)
            print("PROCESSING COMPLETE")
            print("=" * 50)
            print(f"Total rows processed:     {self.processing_stats['total_rows']:,}")
            print(f"Values interpolated:      {self.processing_stats['interpolated_values']:,}")
            print(f"Fallback values used:     {self.processing_stats['fallback_values']:,}")
            print(f"Processing time:          {self.processing_stats['processing_time']:.2f} seconds")
            
            if self.processing_stats['total_rows'] > 0:
                speed = self.processing_stats['total_rows'] / self.processing_stats['processing_time']
                print(f"Processing speed:         {speed:.0f} rows/second")
            
            # Show interpolation ratio
            total_fixes = self.processing_stats['interpolated_values'] + self.processing_stats['fallback_values']
            if total_fixes > 0:
                interpolation_ratio = self.processing_stats['interpolated_values'] / total_fixes * 100
                print(f"Interpolation ratio:      {interpolation_ratio:.1f}% (vs fallback)")
            
            print(f"\n✓ Clean dataset saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"\nError during processing: {e}")
            return False
    
    def validate_output(self, file_path: str, sample_lines: int = 10) -> None:
        """
        Display sample lines from the processed file for validation.
        
        Args:
            file_path: Path to the processed file
            sample_lines: Number of sample lines to display
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                print(f"\nSample from interpolated dataset:")
                print("-" * 80)
                
                for i, line in enumerate(file):
                    if i >= sample_lines:
                        break
                    
                    display_line = line.rstrip('\n')
                    if len(display_line) > 120:
                        display_line = display_line[:120] + "..."
                    
                    print(f"Line {i+1:2d}: {display_line}")
                    
        except Exception as e:
            print(f"Error validating output: {e}")


def main():
    """Main function to run the weather data interpolation system."""
    # File paths
    input_file = "../Data/Raw/KIIT_University_Weather_3-1-24_12-00_AM_1_Year_1754733830_v2.csv"
    output_file = "../Data/Cleaned/weather_data_interpolated.csv"
    
    # Create and run interpolator
    interpolator = WeatherDataInterpolator()
    
    if interpolator.process_weather_data_production(input_file, output_file):
        # Optional: Show sample output
        # interpolator.validate_output(output_file, 5)
        return 0
    else:
        print("Failed to process weather data.")
        return 1


if __name__ == "__main__":
    exit(main())

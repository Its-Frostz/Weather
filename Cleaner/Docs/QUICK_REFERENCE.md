# Smart Weather Cleaner - Quick Reference

## Imputation Strategy Summary

| Column Type | Keywords | Primary Strategy | Fallback Default | Range | Rationale |
|-------------|----------|------------------|------------------|-------|-----------|
| **Temperature** | temp, heat index, dew point, wind chill | Rolling median (12 values) | 22°C ± time adjustment | -50°C to 60°C | Gradual changes, diurnal patterns |
| **Humidity** | hum | Rolling median (12 values) | 65% | 0% to 100% | Gradual changes, moderate default |
| **Pressure** | pressure, bar | Rolling median (12 values) | 1013.25 mb | 900-1100 mb | Very slow changes, sea level standard |
| **Wind Speed** | wind speed, wind run | Rolling median (12 values) | 3.0 km/h | 0-200 km/h | Variable but often consistent periods |
| **Wind Direction** | wind direction, prevailing | Most recent value | 180° (South) | 0°-360° | Directional persistence |
| **Precipitation** | rain, et | Rolling median (12 values) | 0.0 mm | 0-1000 mm | Often zero, events have duration |
| **Solar Radiation** | solar | Rolling median (12 values) | 0.0 W/m² | 0-2000 W/m² | Zero at night, varies with clouds |
| **UV Index** | uv | Rolling median (12 values) | 0.0 | 0-15 | Follows solar patterns |
| **Air Quality** | aqi | Rolling median (12 values) | 50.0 | 0-500 | Slow changes, "Good" baseline |
| **Particulate Matter** | pm | Rolling median (12 values) | 25.0 ug/m³ | 0-1000 ug/m³ | Gradual changes, moderate urban |
| **Degree Days** | degree days | Rolling median (12 values) | 0.0 | Unlimited | Accumulate slowly, often zero |
| **DateTime** | date, time | No imputation | "MISSING_TIME" | N/A | Should never be missing |
| **Generic** | (other) | Rolling median (12 values) | 0.0 | Unlimited | Conservative default |

## Key Features

### Rolling Window System
- **Window Size**: 12 values (1 hour at 5-minute intervals)
- **Method**: Median (robust to outliers)
- **Storage**: Efficient deque collections
- **Bootstrap**: Uses defaults until window fills

### Time-Based Adjustments
- **Temperature Only**: Applies diurnal correction
- **Daytime (6 AM - 6 PM)**: Base + 3°C
- **Nighttime (6 PM - 6 AM)**: Base - 2°C
- **Hour Estimation**: `(line_number * 5 minutes) % 24 hours`

### Missing Value Patterns Recognized
```
"", "-", "--", "nan", "NaN", "None", "null", whitespace-only
```

### Validation Ranges
- **Temperature**: -50°C to 60°C
- **Humidity**: 0% to 100%
- **Pressure**: 900 to 1100 mb
- **Wind Speed**: 0 to 200 km/h
- **Wind Direction**: 0° to 360°
- **Rain**: 0 to 1000 mm
- **Solar**: 0 to 2000 W/m²
- **UV**: 0 to 15
- **AQI**: 0 to 500
- **PM**: 0 to 1000 ug/m³

## Processing Results
- **Rows Processed**: 67,478
- **Missing Values Imputed**: 1,022,656 (21% of all data)
- **Columns Classified**: 72
- **Processing Speed**: 3,742 rows/second
- **Processing Time**: 18.03 seconds

## Benefits for ML Models
✅ **No unrealistic zeros** that bias predictions  
✅ **Weather-appropriate values** maintain physical relationships  
✅ **Temporal consistency** using rolling windows  
✅ **Domain knowledge** built into imputation rules  
✅ **Realistic value distributions** for training  

## File Locations
- **Raw Data**: `../Data/Raw/KIIT_University_Weather_3-1-24_12-00_AM_1_Year_1754733830_v2.csv`
- **Cleaned Data**: `../Data/Cleaned/weather_data_cleaned_smart.csv`
- **Cleaner Script**: `weather_cleaner_smart.py`
- **Documentation**: `IMPUTATION_DOCUMENTATION.md`

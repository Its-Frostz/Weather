#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <chrono>
#include <iomanip>

class WeatherDataCleaner {
private:
    static constexpr size_t BUFFER_SIZE = 1024 * 1024; // 1MB buffer for efficient I/O
    char buffer[BUFFER_SIZE];
    
    // Inline function to trim whitespace for maximum efficiency
    inline std::string trim(const std::string& str) {
        size_t start = str.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) return "";
        size_t end = str.find_last_not_of(" \t\r\n");
        return str.substr(start, end - start + 1);
    }
    
    // Fast CSV field cleaning - processes field in-place when possible
    inline std::string cleanField(const std::string& field) {
        std::string trimmed = trim(field);
        
        // Handle quoted fields
        if (trimmed.length() >= 2 && trimmed.front() == '"' && trimmed.back() == '"') {
            trimmed = trimmed.substr(1, trimmed.length() - 2);
        }
        
        // Check for dash or empty/whitespace-only content
        if (trimmed == "-" || trimmed == "--" || trimmed.empty() || 
            std::all_of(trimmed.begin(), trimmed.end(), [](char c) { return std::isspace(c); })) {
            return "0";
        }
        
        return trimmed;
    }
    
    // Optimized CSV line parser using stringstream
    std::vector<std::string> parseCSVLine(const std::string& line) {
        std::vector<std::string> fields;
        std::stringstream ss(line);
        std::string field;
        
        // Reserve space to avoid frequent reallocations
        fields.reserve(80); // Estimated field count based on sample
        
        while (std::getline(ss, field, ',')) {
            fields.push_back(cleanField(field));
        }
        
        return fields;
    }
    
    // Write CSV line efficiently
    void writeCSVLine(std::ofstream& output, const std::vector<std::string>& fields) {
        if (fields.empty()) return;
        
        // Use a single stringstream to build the entire line
        std::stringstream ss;
        ss << fields[0];
        for (size_t i = 1; i < fields.size(); ++i) {
            ss << ',' << fields[i];
        }
        ss << '\n';
        
        output << ss.str();
    }

public:
    bool processFile(const std::string& inputPath, const std::string& outputPath) {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        std::ifstream input(inputPath, std::ios::binary);
        if (!input.is_open()) {
            std::cerr << "Error: Cannot open input file '" << inputPath << "'" << std::endl;
            return false;
        }
        
        std::ofstream output(outputPath, std::ios::binary);
        if (!output.is_open()) {
            std::cerr << "Error: Cannot create output file '" << outputPath << "'" << std::endl;
            return false;
        }
        
        // Set custom buffer for both streams to improve I/O performance
        input.rdbuf()->pubsetbuf(buffer, BUFFER_SIZE / 2);
        output.rdbuf()->pubsetbuf(buffer + BUFFER_SIZE / 2, BUFFER_SIZE / 2);
        
        std::string line;
        size_t lineCount = 0;
        size_t processedLines = 0;
        
        std::cout << "Processing weather data..." << std::endl;
        
        // Process file line by line for memory efficiency
        while (std::getline(input, line)) {
            lineCount++;
            
            // Progress indicator for large files
            if (lineCount % 10000 == 0) {
                std::cout << "\rProcessed " << lineCount << " lines..." << std::flush;
            }
            
            // Parse and clean the CSV line
            std::vector<std::string> fields = parseCSVLine(line);
            
            // Write cleaned line to output
            writeCSVLine(output, fields);
            processedLines++;
        }
        
        input.close();
        output.close();
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
        
        std::cout << "\n\nProcessing completed successfully!" << std::endl;
        std::cout << "Lines processed: " << processedLines << std::endl;
        std::cout << "Processing time: " << duration.count() << " ms" << std::endl;
        std::cout << "Output saved to: " << outputPath << std::endl;
        
        return true;
    }
    
    // Utility function to validate the cleaning results
    void validateCleaning(const std::string& filePath, int sampleLines = 10) {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            std::cerr << "Error: Cannot open file for validation" << std::endl;
            return;
        }
        
        std::cout << "\nValidation sample from cleaned file:" << std::endl;
        std::cout << std::string(80, '-') << std::endl;
        
        std::string line;
        int count = 0;
        while (std::getline(file, line) && count < sampleLines) {
            std::cout << "Line " << std::setw(2) << (count + 1) << ": " 
                      << (line.length() > 120 ? line.substr(0, 120) + "..." : line) << std::endl;
            count++;
        }
        
        file.close();
    }
};

int main() {
    // Input and output file paths
    const std::string inputFile = "Data/KIIT_University_Weather_3-1-24_12-00_AM_1_Year_1754733830_v2.csv";
    const std::string outputFile = "weather_data_cleaned.csv";
    
    std::cout << "High-Performance Weather Data Cleaner" << std::endl;
    std::cout << "=====================================" << std::endl;
    std::cout << "Input file:  " << inputFile << std::endl;
    std::cout << "Output file: " << outputFile << std::endl;
    std::cout << std::endl;
    
    WeatherDataCleaner cleaner;
    
    if (cleaner.processFile(inputFile, outputFile)) {
        // Show sample of cleaned data for verification
        cleaner.validateCleaning(outputFile, 15);
        
        std::cout << "\nData cleaning rules applied:" << std::endl;
        std::cout << "• Replaced '-' and '--' with '0'" << std::endl;
        std::cout << "• Replaced empty/whitespace cells with '0'" << std::endl;
        std::cout << "• Preserved original CSV structure and headers" << std::endl;
        std::cout << "• Maintained all column ordering" << std::endl;
        
        return 0;
    } else {
        std::cerr << "Failed to process the weather data file." << std::endl;
        return 1;
    }
}

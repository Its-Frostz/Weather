#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <chrono>
#include <iomanip>

// Platform-specific headers for memory mapping
#ifdef _WIN32
    #include <windows.h>
    #include <io.h>
    #include <fcntl.h>
#else
    #include <sys/mman.h>
    #include <sys/stat.h>
    #include <fcntl.h>
    #include <unistd.h>
#endif

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
    
    // Memory-mapped I/O processing for maximum performance
    bool processFileMemoryMapped(const std::string& inputPath, const std::string& outputPath) {
        auto startTime = std::chrono::high_resolution_clock::now();
        
#ifdef _WIN32
        // Windows memory mapping implementation
        HANDLE hFile = CreateFileA(inputPath.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (hFile == INVALID_HANDLE_VALUE) {
            std::cerr << "Error: Cannot open input file for memory mapping" << std::endl;
            return false;
        }
        
        LARGE_INTEGER fileSize;
        if (!GetFileSizeEx(hFile, &fileSize)) {
            CloseHandle(hFile);
            std::cerr << "Error: Cannot get file size" << std::endl;
            return false;
        }
        
        HANDLE hMapFile = CreateFileMappingA(hFile, nullptr, PAGE_READONLY, 0, 0, nullptr);
        if (hMapFile == nullptr) {
            CloseHandle(hFile);
            std::cerr << "Error: Cannot create file mapping" << std::endl;
            return false;
        }
        
        char* mapped = static_cast<char*>(MapViewOfFile(hMapFile, FILE_MAP_READ, 0, 0, 0));
        if (mapped == nullptr) {
            CloseHandle(hMapFile);
            CloseHandle(hFile);
            std::cerr << "Error: Cannot map view of file" << std::endl;
            return false;
        }
        
        size_t fileLength = static_cast<size_t>(fileSize.QuadPart);
#else
        // Unix/Linux memory mapping implementation
        int fd = open(inputPath.c_str(), O_RDONLY);
        if (fd == -1) {
            std::cerr << "Error: Cannot open input file for memory mapping" << std::endl;
            return false;
        }
        
        struct stat sb;
        if (fstat(fd, &sb) == -1) {
            close(fd);
            std::cerr << "Error: Cannot get file stats" << std::endl;
            return false;
        }
        
        char* mapped = static_cast<char*>(mmap(nullptr, sb.st_size, PROT_READ, MAP_PRIVATE, fd, 0));
        if (mapped == MAP_FAILED) {
            close(fd);
            std::cerr << "Error: Cannot memory map file" << std::endl;
            return false;
        }
        
        size_t fileLength = static_cast<size_t>(sb.st_size);
#endif
        
        // Open output file
        std::ofstream output(outputPath, std::ios::binary);
        if (!output.is_open()) {
#ifdef _WIN32
            UnmapViewOfFile(mapped);
            CloseHandle(hMapFile);
            CloseHandle(hFile);
#else
            munmap(mapped, fileLength);
            close(fd);
#endif
            std::cerr << "Error: Cannot create output file" << std::endl;
            return false;
        }
        
        // Set output buffer
        output.rdbuf()->pubsetbuf(buffer, BUFFER_SIZE);
        
        // Process mapped memory
        const char* start = mapped;
        const char* end = mapped + fileLength;
        const char* lineStart = start;
        size_t lineCount = 0;
        
        std::cout << "Processing weather data with memory mapping..." << std::endl;
        
        while (lineStart < end) {
            // Find line end
            const char* lineEnd = std::find(lineStart, end, '\n');
            
            // Skip empty lines
            if (lineEnd > lineStart) {
                // Create string from memory range (excluding \r if present)
                const char* actualLineEnd = lineEnd;
                if (actualLineEnd > lineStart && *(actualLineEnd - 1) == '\r') {
                    actualLineEnd--;
                }
                
                std::string line(lineStart, actualLineEnd);
                
                // Process line using existing methods
                std::vector<std::string> fields = parseCSVLine(line);
                writeCSVLine(output, fields);
            }
            
            lineCount++;
            if (lineCount % 10000 == 0) {
                std::cout << "\rProcessed " << lineCount << " lines..." << std::flush;
            }
            
            // Move to next line
            lineStart = (lineEnd == end) ? end : lineEnd + 1;
        }
        
        // Cleanup
        output.close();
        
#ifdef _WIN32
        UnmapViewOfFile(mapped);
        CloseHandle(hMapFile);
        CloseHandle(hFile);
#else
        munmap(mapped, fileLength);
        close(fd);
#endif
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
        
        std::cout << "\n\nMemory-mapped processing completed successfully!" << std::endl;
        std::cout << "Lines processed: " << lineCount << std::endl;
        std::cout << "Processing time: " << duration.count() << " ms" << std::endl;
        std::cout << "Processing speed: " << (lineCount * 1000.0 / duration.count()) << " lines/second" << std::endl;
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
    const std::string outputFileBuffered = "weather_data_cleaned_buffered.csv";
    const std::string outputFileMapped = "weather_data_cleaned_mapped.csv";
    
    std::cout << "High-Performance Weather Data Cleaner - Benchmark" << std::endl;
    std::cout << "=================================================" << std::endl;
    std::cout << "Input file: " << inputFile << std::endl;
    std::cout << std::endl;
    
    WeatherDataCleaner cleaner;
    
    // Test 1: Buffered I/O approach
    std::cout << "=== TEST 1: BUFFERED I/O APPROACH ===" << std::endl;
    if (cleaner.processFile(inputFile, outputFileBuffered)) {
        std::cout << "✅ Buffered I/O completed successfully!" << std::endl;
    } else {
        std::cerr << "❌ Buffered I/O failed!" << std::endl;
    }
    
    std::cout << std::endl;
    
    // Test 2: Memory-mapped I/O approach
    std::cout << "=== TEST 2: MEMORY-MAPPED I/O APPROACH ===" << std::endl;
    if (cleaner.processFileMemoryMapped(inputFile, outputFileMapped)) {
        std::cout << "✅ Memory-mapped I/O completed successfully!" << std::endl;
    } else {
        std::cerr << "❌ Memory-mapped I/O failed!" << std::endl;
    }
    
    std::cout << std::endl;
    std::cout << "=== VALIDATION SAMPLE ===" << std::endl;
    cleaner.validateCleaning(outputFileMapped, 10);
    
    std::cout << std::endl;
    std::cout << "=== BENCHMARK SUMMARY ===" << std::endl;
    std::cout << "Files created:" << std::endl;
    std::cout << "• " << outputFileBuffered << " (Buffered I/O)" << std::endl;
    std::cout << "• " << outputFileMapped << " (Memory-mapped I/O)" << std::endl;
    std::cout << std::endl;
    std::cout << "💡 Run the Python version to compare:" << std::endl;
    std::cout << "   python weather_cleaner_simple.py" << std::endl;
    
    return 0;
}

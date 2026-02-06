cmake_minimum_required(VERSION 3.14)
project(mm_to_json)

# Set C++ Standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/mm_to_json)

# Find ODBC (usually available on macOS via system or brew's unixodbc)
find_package(ODBC)

# If ODBC not found via standard CMake, try manual paths (Homebrew)
if (NOT ODBC_FOUND)
    set(ODBC_INCLUDE_DIRS /opt/homebrew/include)
    set(ODBC_LIBRARIES /opt/homebrew/lib/libodbc.dylib) # Common location
    if(EXISTS ${ODBC_LIBRARIES})
        set(ODBC_FOUND TRUE)
    endif()
endif()

if (ODBC_FOUND)
    include_directories(${ODBC_INCLUDE_DIRS})
    link_directories(/opt/homebrew/lib) # Add homebrew lib path explicitly
else()
    message(WARNING "ODBC not found. Build may fail.")
endif()

# Source files
file(GLOB SOURCES "mm_to_json/*.cpp")

# Create executable
add_executable(mm_to_json ${SOURCES})

# Link libraries
target_link_libraries(mm_to_json PRIVATE ${ODBC_LIBRARIES})

# Compiler options
if(MSVC)
   # Keep windows options if needed, but we are porting to macOS
else()
    target_compile_options(mm_to_json PRIVATE -Wall -Wextra)
endif()

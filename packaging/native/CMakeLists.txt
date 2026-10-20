cmake_minimum_required(VERSION 3.20)
project(MurumsPkgBackend LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(WIN32)
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".a")
    set(ZLIB_USE_STATIC_LIBS ON)
endif()
find_package(ZLIB REQUIRED)
find_package(Git REQUIRED)
find_path(CRYPTOPP_INCLUDE_DIR cryptopp/aes.h REQUIRED)
find_library(CRYPTOPP_LIBRARY NAMES cryptopp crypto++ REQUIRED)
set(UPSTREAM "${CMAKE_CURRENT_SOURCE_DIR}/../../vendor/shadps4plus")
set(ENTRY_PATCH "${CMAKE_CURRENT_SOURCE_DIR}/np-entry-padding.patch")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${ENTRY_PATCH}")
configure_file("${UPSTREAM}/src/core/file_format/pkg.cpp" "${CMAKE_CURRENT_BINARY_DIR}/pkg.cpp" COPYONLY)
execute_process(
    COMMAND "${GIT_EXECUTABLE}" apply --unsafe-paths "--directory=${CMAKE_CURRENT_BINARY_DIR}" "${ENTRY_PATCH}"
    RESULT_VARIABLE PATCH_RESULT
    ERROR_VARIABLE PATCH_ERROR
)
if(NOT PATCH_RESULT EQUAL 0)
    message(FATAL_ERROR "Could not apply encrypted-entry correction: ${PATCH_ERROR}")
endif()

add_executable(pkg_extractor
    "${UPSTREAM}/extractor/main.cpp"
    "${UPSTREAM}/src/core/loader.cpp"
    "${CMAKE_CURRENT_BINARY_DIR}/pkg.cpp"
    "${UPSTREAM}/src/core/file_format/psf.cpp"
    "${UPSTREAM}/src/core/file_format/pkg_type.cpp"
    "${UPSTREAM}/src/core/crypto/crypto.cpp"
    "${UPSTREAM}/src/common/io_file.cpp"
    "${UPSTREAM}/src/common/assert.cpp"
    "${UPSTREAM}/src/common/error.cpp"
    "${UPSTREAM}/src/common/path_util.cpp"
    "${UPSTREAM}/src/common/string_util.cpp"
)
target_include_directories(pkg_extractor PRIVATE "${UPSTREAM}/src" "${CRYPTOPP_INCLUDE_DIR}")
target_compile_options(pkg_extractor PRIVATE -include "${CMAKE_CURRENT_SOURCE_DIR}/compatibility.h")
target_link_libraries(pkg_extractor PRIVATE "${CRYPTOPP_LIBRARY}" ZLIB::ZLIB)
if(WIN32)
    target_compile_definitions(pkg_extractor PRIVATE _WIN32_WINNT=0x0A00 NTDDI_VERSION=0x0A000007)
    target_link_options(pkg_extractor PRIVATE -static -static-libgcc -static-libstdc++ "$<$<CONFIG:Release>:-s>")
    target_link_libraries(pkg_extractor PRIVATE shell32 ole32 uuid ntdll)
endif()
if(APPLE)
    target_link_libraries(pkg_extractor PRIVATE "-framework CoreFoundation")
endif()

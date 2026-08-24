cmake_minimum_required(VERSION 3.15)
project(vdp_server C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# --- Library: the VDP server core -------------------------------------------
add_library(vdp
    src/vdp_codec.c
    src/vdp_core.c
    src/vdp_dca.c
    src/vdp_server.c
    src/vdp_proxy.c
)
target_include_directories(vdp PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# --- Demo application -------------------------------------------------------
add_executable(vdp_demo app/main.c)
target_link_libraries(vdp_demo PRIVATE vdp)

# --- Tests ------------------------------------------------------------------
enable_testing()
add_executable(vdp_tests tests/test_vdp.c)
target_link_libraries(vdp_tests PRIVATE vdp)
add_test(NAME vdp_tests COMMAND vdp_tests)

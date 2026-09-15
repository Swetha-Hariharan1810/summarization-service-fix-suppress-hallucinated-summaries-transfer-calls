cmake_minimum_required(VERSION 3.4...3.18)
project(birchsumm)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

include(pybind11)
include_directories(${CMAKE_SOURCE_DIR})

set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(BUILD_RPATH_USE_ORIGIN TRUE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

if(DEFINED ENV{BIRCHSUMM_DELAY})
message(STATUS "Set birchsumm delay to $ENV{BIRCHSUMM_DELAY}")
add_definitions(-D__DELAY__=$ENV{BIRCHSUMM_DELAY})
else()
add_definitions(-D__DELAY__=0)
endif()

if(DEFINED ENV{BIRCHSUMM_AUTH_SERVER})
message(STATUS "Set birchsumm to authenticate through birch server")
add_definitions(-D__AUTH__)
endif()

if(DEFINED ENV{BIRCHSUMM_AWS_LOGIN})
message(STATUS "Set birchsumm to authenticate through aws login")
add_definitions(-D__AWS_LOGIN__)
endif()
if(DEFINED ENV{BIRCHSUMM_EXPIRE})
message(STATUS "Set birchsumm to authenticate through aws login")
add_definitions(-D__EXPIRE__=$ENV{BIRCHSUMM_EXPIRE})
endif()

#add_definitions(-D__DELAY__=24)
#add_definitions(-D__EXPIRE__="Mar 31 2023 00:00:00")
#add_definitions(-D__AWS_LOGIN__)

if(NOT TORCH_DIR)
    execute_process(
        COMMAND "${PYTHON_EXECUTABLE}" -c "import os; import torch; print(os.path.dirname(torch.__file__))"
        OUTPUT_STRIP_TRAILING_WHITESPACE
        OUTPUT_VARIABLE TORCH_DIR
    )
endif()

list(APPEND CMAKE_PREFIX_PATH ${TORCH_DIR})
find_package(Torch REQUIRED)

message(STATUS "TORCH_LIBRARIES: ${TORCH_LIBRARIES}")
message(STATUS "PYTHON LIBRARY: ${PYTHON_LIBRARY}")
message(STATUS "TORCH DIR: ${TORCH_DIR}")
message(STATUS "TORCH FLAGS: ${TORCH_CXX_FLAGS}")
string(APPEND CMAKE_CXX_FLAGS " ${TORCH_CXX_FLAGS} ")

include_directories(${PYTHON_INCLUDE_DIRS})
include_directories(${TORCH_INCLUDE_DIRS})

add_subdirectory(csrc)
add_subdirectory(pybind)

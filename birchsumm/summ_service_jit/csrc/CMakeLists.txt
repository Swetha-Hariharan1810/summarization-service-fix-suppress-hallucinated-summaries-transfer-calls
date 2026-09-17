cmake_minimum_required(VERSION 3.8 FATAL_ERROR)
project(birchsumm)
add_library(birchsumm_core model.cpp auth.cpp dict.cpp)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${TORCH_CXX_FLAGS} -Wall -fPIC -lstdc++fs")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -O3 -fPIC -lstdc++fs")

target_link_libraries(birchsumm_core PRIVATE ${TORCH_LIBRARIES})
target_link_libraries(birchsumm_core PRIVATE "-Wl,-rpath,$ORIGIN/torch/lib")
target_link_libraries(birchsumm_core PRIVATE "-Wl,-rpath,$ORIGIN/torch/lib64")
target_link_libraries(birchsumm_core PRIVATE "-Wl,-rpath,$ORIGIN/birchsumm/lib")
target_link_libraries(birchsumm_core PRIVATE "-Wl,-rpath,$ORIGIN/../lib")
target_link_libraries(birchsumm_core PRIVATE ${PYTHON_LIBRARY})
target_link_libraries(birchsumm_core PRIVATE curl)

add_executable(summbin bin/summbin.cpp)
target_link_libraries(summbin PRIVATE birchsumm_core)
target_link_libraries(summbin PRIVATE "${TORCH_LIBRARIES}")

message(STATUS "CMAKE_INSTALL_PREFIX: ${CMAKE_INSTALL_PREFIX}")

install(TARGETS birchsumm_core
    DESTINATION lib
)
install(TARGETS summbin
    DESTINATION bin
)

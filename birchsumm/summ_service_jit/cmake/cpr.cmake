function(download_cpr)
    include(FetchContent)

    # set(CPR_USE_SYSTEM_CURL "ON")
    FetchContent_Declare(cpr
        GIT_REPOSITORY https://github.com/libcpr/cpr.git
        GIT_TAG a2d35a1cb9f3f7e2f1469d6a189751331dc99f96) # The commit hash for 1.9.3 Replace with the latest from: https://github.com/libcpr/cpr/releases
    FetchContent_GetProperties(cpr)

    if(NOT cpr_POPULATED)
        message(STATUS "Downloading cpr")
        FetchContent_Populate(cpr)
    endif()

    message(STATUS "cpr is downloaded to ${cpr_SOURCE_DIR}")
    message(STATUS "cpr's binary dir is ${cpr_BINARY_DIR}")
    add_subdirectory(${cpr_SOURCE_DIR} ${cpr_BINARY_DIR} EXCLUDE_FROM_ALL)
    target_include_directories(cpr
        PUBLIC
        ${cpr_SOURCE_DIR}/
    )

    if(BUILD_SHARED_LIBS)
        install(TARGETS cpr DESTINATION lib)
    endif()
endfunction()

download_cpr()

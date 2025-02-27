# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# ### Editing this file ###
#
# This file should be formatted with
# ~~~
# cmake-format --first-comment-is-literal=True -i CMakeLists.txt
# ~~~
# It should also be cmake-lint clean.
#
# The targets in this file will be built if EXECUTORCH_BUILD_VULKAN is ON

cmake_minimum_required(VERSION 3.19)

if(NOT EXECUTORCH_ROOT)
  set(EXECUTORCH_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../..)
endif()

if(NOT RUNTIME_PATH)
  set(RUNTIME_PATH ${CMAKE_CURRENT_SOURCE_DIR}/runtime)
endif()

if(NOT PYTHON_EXECUTABLE)
  set(PYTHON_EXECUTABLE python3)
endif()

if(NOT FLATC_EXECUTABLE)
  set(FLATC_EXECUTABLE flatc)
endif()

# Include this file to access target_link_options_shared_lib This is required to
# provide access to target_link_options_shared_lib which allows libraries to be
# linked with the --whole-archive flag. This is required for libraries that
# perform dynamic registration via static initialization.
include(${EXECUTORCH_ROOT}/build/Utils.cmake)

# ATen Vulkan Libs

set(PYTORCH_PATH ${EXECUTORCH_ROOT}/third-party/pytorch)
set(VULKAN_THIRD_PARTY_PATH ${CMAKE_CURRENT_SOURCE_DIR}/third-party)
include(cmake/ATenVulkan.cmake)

set(COMMON_INCLUDES ${VULKAN_API_HEADERS} ${EXECUTORCH_ROOT}/..)

# vulkan_graph_lib

file(GLOB_RECURSE vulkan_graph_cpp ${RUNTIME_PATH}/graph/*)

add_library(vulkan_graph_lib STATIC ${vulkan_graph_cpp})
target_include_directories(vulkan_graph_lib PRIVATE ${COMMON_INCLUDES})
target_link_libraries(${LIBRARY_NAME} vulkan_api_lib)
target_compile_options(vulkan_graph_lib PRIVATE ${VULKAN_CXX_FLAGS})
# Link this library with --whole-archive due to dynamic operator registrations
target_link_options_shared_lib(vulkan_graph_lib)

# Due to dynamic registrations, these libraries must be explicitly linked
set(VULKAN_STANDARD_OPS_LIBS vulkan_graph_lib vulkan_graph_shaderlib)

# vulkan_graph_shaderlib

set(VULKAN_GRAPH_SHADERS_PATH ${RUNTIME_PATH}/graph/ops/glsl/)
vulkan_shader_library(${VULKAN_GRAPH_SHADERS_PATH} vulkan_graph_shaderlib)

# Generate Files from flatc

set(SCHEMA_INCLUDE_DIR ${CMAKE_BINARY_DIR}/schema/include)

set(GENERATED_HEADER
    ${SCHEMA_INCLUDE_DIR}/executorch/backends/vulkan/schema_generated.h)

add_custom_command(
  OUTPUT ${GENERATED_HEADER}
  COMMAND
    ${FLATC_EXECUTABLE} --cpp --cpp-std c++11 --scoped-enums -o
    "${SCHEMA_INCLUDE_DIR}/executorch/backends/vulkan/" ${_vulkan_schema__srcs}
  WORKING_DIRECTORY ${EXECUTORCH_ROOT}
  COMMENT "Generating vulkan_schema headers"
  VERBATIM)

# vulkan_schema library

add_library(vulkan_schema INTERFACE ${GENERATED_HEADER})
set_target_properties(vulkan_schema PROPERTIES LINKER_LANGUAGE CXX)

target_include_directories(
  vulkan_schema INTERFACE ${SCHEMA_INCLUDE_DIR}
                          ${EXECUTORCH_ROOT}/third-party/flatbuffers/include)

# vulkan_backend_lib

file(GLOB vulkan_backend_cpp ${RUNTIME_PATH}/*.cpp)

add_library(vulkan_backend ${vulkan_backend_cpp})
target_include_directories(vulkan_backend PRIVATE ${SCHEMA_INCLUDE_DIR}
                                                  ${COMMON_INCLUDES})
target_link_libraries(vulkan_backend PRIVATE vulkan_graph_lib vulkan_schema
                                             executorch)
target_compile_options(vulkan_backend PRIVATE ${VULKAN_CXX_FLAGS})
# Link this library with --whole-archive due to dynamic backend registration
target_link_options_shared_lib(vulkan_backend)

# Executor Runner

if(NOT CMAKE_TOOLCHAIN_FILE MATCHES ".*iOS\.cmake$")
  set(VULKAN_RUNNER_SRCS ${_executor_runner__srcs})
  list(TRANSFORM VULKAN_RUNNER_SRCS PREPEND "${EXECUTORCH_ROOT}/")

  add_executable(vulkan_executor_runner ${VULKAN_RUNNER_SRCS})
  target_link_libraries(
    vulkan_executor_runner ${_executor_runner_libs} vulkan_schema
    vulkan_backend ${VULKAN_STANDARD_OPS_LIBS})
  target_compile_options(vulkan_executor_runner PUBLIC ${VULKAN_CXX_FLAGS})

  add_library(vulkan_executor_runner_lib STATIC ${VULKAN_RUNNER_SRCS})
  target_link_libraries(
    vulkan_executor_runner_lib ${_executor_runner_libs} vulkan_schema
    vulkan_backend vulkan_api_lib ${VULKAN_STANDARD_OPS_LIBS})
  target_compile_options(vulkan_executor_runner_lib PUBLIC ${VULKAN_CXX_FLAGS})
endif()

# Test targets

if(EXECUTORCH_BUILD_GTESTS)
  set(TEST_UTILS_HEADERS ${CMAKE_CURRENT_SOURCE_DIR}/test/utils)
  file(GLOB TEST_UTILS_CPP ${CMAKE_CURRENT_SOURCE_DIR}/test/utils/*.cpp)

  set(TEST_SHADERS_PATH ${CMAKE_CURRENT_SOURCE_DIR}/test/glsl)
  vulkan_shader_library(${TEST_SHADERS_PATH} test_shaderlib)

  # vulkan_compute_api_test
  set(COMPUTE_API_TEST_CPP
      ${CMAKE_CURRENT_SOURCE_DIR}/test/vulkan_compute_api_test.cpp)

  add_executable(vulkan_compute_api_test ${COMPUTE_API_TEST_CPP}
                                         ${TEST_UTILS_CPP})
  target_include_directories(vulkan_compute_api_test
                             PRIVATE ${COMMON_INCLUDES} ${TEST_UTILS_HEADERS})
  target_link_libraries(
    vulkan_compute_api_test PRIVATE gtest_main ${VULKAN_STANDARD_OPS_LIBS}
                                    test_shaderlib)
  target_compile_options(vulkan_compute_api_test PRIVATE ${VULKAN_CXX_FLAGS})
endif()

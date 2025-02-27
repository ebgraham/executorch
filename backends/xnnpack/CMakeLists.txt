# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Please this file formatted by running:
# ~~~
# cmake-format --first-comment-is-literal=True CMakeLists.txt
# ~~~

cmake_minimum_required(VERSION 3.19)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(NOT PYTHON_EXECUTABLE)
  set(PYTHON_EXECUTABLE python3)
endif()

if(NOT FLATC_EXECUTABLE)
  set(FLATC_EXECUTABLE flatc)
endif()

# Source root directory for executorch.
if(NOT EXECUTORCH_ROOT)
  set(EXECUTORCH_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../..)
endif()

include(${EXECUTORCH_ROOT}/build/Utils.cmake)

set(_common_include_directories ${EXECUTORCH_ROOT}/..)
set(_common_compile_options -Wno-deprecated-declarations)

set(_xnnpack_schema__include_dir "${CMAKE_BINARY_DIR}/schema/include")
# Paths to headers generated from the .fbs files.
set(_xnnpack_flatbuffer__outputs)
foreach(fbs_file ${_xnnpack_schema__srcs})
  string(REGEX REPLACE "([^/]+)[.]fbs$" "\\1_generated.h"
                       generated "${fbs_file}")
  list(APPEND _xnnpack_flatbuffer__outputs
       "${_xnnpack_schema__include_dir}/executorch/${generated}")
endforeach()

set(_xnnpack_schema__outputs)
foreach(fbs_file ${_xnnpack_schema__srcs})
  string(REGEX REPLACE "runtime_([^/]+)[.]fbs$" "\\1_generated.h"
                       generated "${fbs_file}")
  list(APPEND _xnnpack_schema__outputs
       "${_xnnpack_schema__include_dir}/executorch/${generated}")
endforeach()

# Generate the headers from the .fbs files.
add_custom_command(
  OUTPUT ${_xnnpack_schema__outputs}
  COMMAND
    ${FLATC_EXECUTABLE} --cpp --cpp-std c++11 --scoped-enums -o
    "${_xnnpack_schema__include_dir}/executorch/backends/xnnpack/serialization"
    ${_xnnpack_schema__srcs}
  COMMAND
    mv ${_xnnpack_flatbuffer__outputs} ${_xnnpack_schema__outputs}
  WORKING_DIRECTORY ${EXECUTORCH_ROOT}
  COMMENT "Generating xnnpack_schema headers"
  VERBATIM)

add_library(xnnpack_schema INTERFACE ${_xnnpack_schema__outputs})
set_target_properties(xnnpack_schema PROPERTIES LINKER_LANGUAGE CXX)
target_include_directories(
  xnnpack_schema INTERFACE ${_xnnpack_schema__include_dir}
                           ${EXECUTORCH_ROOT}/third-party/flatbuffers/include)

set(xnn_executor_runner_libs ${_executor_runner_libs} xnnpack_schema)

list(TRANSFORM _xnnpack_dynamic_quant_utils__srcs PREPEND "${EXECUTORCH_ROOT}/")
add_library(xnnpack_dynamic_quant_utils ${_xnnpack_dynamic_quant_utils__srcs})
set_target_properties(xnnpack_dynamic_quant_utils PROPERTIES LINKER_LANGUAGE
                                                             CXX)
target_include_directories(xnnpack_dynamic_quant_utils
                           PUBLIC ${_common_include_directories})
target_compile_options(xnnpack_dynamic_quant_utils
                       PUBLIC ${_common_compile_options})

if(ENABLE_DYNAMIC_QUANTIZATION)
  list(APPEND xnn_executor_runner_libs xnnpack_dynamic_quant_utils)
endif()

include(cmake/Dependencies.cmake)

list(TRANSFORM _xnnpack_backend__srcs PREPEND "${EXECUTORCH_ROOT}/")
add_library(xnnpack_backend ${_xnnpack_backend__srcs})
target_link_libraries(xnnpack_backend PRIVATE ${xnn_executor_runner_libs})
target_include_directories(xnnpack_backend
                           PUBLIC ${_common_include_directories})
target_include_directories(xnnpack_backend PUBLIC ${XNNPACK_INCLUDE_DIR})
target_compile_options(xnnpack_backend PUBLIC ${_common_compile_options})
target_link_options_shared_lib(xnnpack_backend)

list(APPEND xnn_executor_runner_libs xnnpack_backend)

# ios can only build library but not binary
if(NOT CMAKE_TOOLCHAIN_FILE MATCHES ".*iOS\.cmake$")
  #
  # xnn_executor_runner: Like executor_runner but with XNNPACK, the binary will
  # be at ${CMAKE_BINARY_DIR}/backends/xnnpack
  #
  list(TRANSFORM _xnn_executor_runner__srcs PREPEND "${EXECUTORCH_ROOT}/")
  add_executable(xnn_executor_runner ${_xnn_executor_runner__srcs})
  target_link_libraries(xnn_executor_runner ${xnn_executor_runner_libs})
  target_compile_options(xnn_executor_runner PUBLIC ${_common_compile_options})

  add_library(xnn_executor_runner_lib STATIC ${_xnn_executor_runner__srcs})
  target_link_libraries(xnn_executor_runner_lib ${xnn_executor_runner_libs})
  target_compile_options(xnn_executor_runner_lib
                         PUBLIC ${_common_compile_options})
endif()

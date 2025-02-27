# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

#
# Simple CMake build system for runtime components.
#
# ### One-time setup ###
#
# Configure the CMake build system. It's good practice to do this whenever
# cloning or pulling the upstream repo. Once this is done, you don't need to do
# it again until you pull from the upstream repo again.
#
# NOTE: If your `buck2` binary is not on the PATH, you can change this line to
# say something like `-DBUCK2=/tmp/buck2` to point directly to the tool.
#[[
  (rm -rf cmake-out \
    && mkdir cmake-out \
    && cd cmake-out \
    && cmake -DBUCK2=buck2 ..)
]]
#
# ### Build ###
#
# NOTE: The `-j` argument specifies how many jobs/processes to use when
# building, and tends to speed up the build significantly. It's typical to use
# "core count + 1" as the `-j` value.
# ~~~
# cmake --build cmake-out -j9
# ~~~
#
# ### Editing this file ###
#
# This file should be formatted with
# ~~~
# cmake-format --first-comment-is-literal=True CMakeLists.txt
# ~~~
# It should also be cmake-lint clean.
#

cmake_minimum_required(VERSION 3.19)
project(executorch)
include(build/Utils.cmake)
include(CMakeDependentOption)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug)
endif()
# ------------------------------ OPTIONS -------------------------------------
# WARNING: Please don't add example specific options in this CMakeLists.txt.
# Instead please use `find_package(executorch REQUIRED)` in the example
# directory and add a new executable in the example `CMakeLists.txt`.

# _default_release_disabled_options: default value for options that should be
# disabled in Release mode by default. Users can still manually enable them,
# though.
if(CMAKE_BUILD_TYPE STREQUAL "Release")
  set(_default_release_disabled_options OFF)
else()
  set(_default_release_disabled_options ON)
endif()

option(EXECUTORCH_ENABLE_LOGGING "Build with ET_LOG_ENABLED"
       ${_default_release_disabled_options})
if(NOT EXECUTORCH_ENABLE_LOGGING)
  # Avoid pulling in the logging strings, which can be large. Note that this
  # will set the compiler flag for all targets in this directory, and for all
  # subdirectories included after this point.
  add_definitions(-DET_LOG_ENABLED=0)
endif()

# Configure log level. Must be one of debug, info, error, fatal.
set(EXECUTORCH_LOG_LEVEL "Info" CACHE STRING
      "Build with the given ET_MIN_LOG_LEVEL value")
string(TOLOWER "${EXECUTORCH_LOG_LEVEL}" LOG_LEVEL_LOWER)
if(LOG_LEVEL_LOWER STREQUAL "debug")
  add_definitions(-DET_MIN_LOG_LEVEL=Debug)
elseif(LOG_LEVEL_LOWER STREQUAL "info")
  add_definitions(-DET_MIN_LOG_LEVEL=Info)
elseif(LOG_LEVEL_LOWER STREQUAL "error")
  add_definitions(-DET_MIN_LOG_LEVEL=Error)
elseif(LOG_LEVEL_LOWER STREQUAL "fatal")
  add_definitions(-DET_MIN_LOG_LEVEL=Fatal)
else()
  message(SEND_ERROR
      "Unknown log level \"${EXECUTORCH_LOG_LEVEL}\". Expected one of Debug, " +
      "Info, Error, or Fatal.")
endif()

option(EXECUTORCH_ENABLE_PROGRAM_VERIFICATION
       "Build with ET_ENABLE_PROGRAM_VERIFICATION"
       ${_default_release_disabled_options})
if(NOT EXECUTORCH_ENABLE_PROGRAM_VERIFICATION)
  # Avoid pulling in the flatbuffer data verification logic, which can add about
  # 20kB. Note that this will set the compiler flag for all targets in this
  # directory, and for all subdirectories included after this point.
  add_definitions(-DET_ENABLE_PROGRAM_VERIFICATION=0)
endif()

option(EXECUTORCH_ENABLE_EVENT_TRACER
       "Build with ET_EVENT_TRACER_ENABLED=ON"
       OFF)
if(EXECUTORCH_ENABLE_EVENT_TRACER)
  add_definitions(-DET_EVENT_TRACER_ENABLED)
endif()

# -ffunction-sections -fdata-sections: breaks function and
# data into sections so they can be properly gc'd. -s: strip symbol.
# -fno-exceptions -fno-rtti: disables exceptions and runtime type.
set(CMAKE_CXX_FLAGS_RELEASE
    "-ffunction-sections -fdata-sections -fno-exceptions -fno-rtti")
if(NOT APPLE)
  set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -s")
endif()

option(OPTIMIZE_SIZE "Build executorch runtime optimizing for binary size" OFF)
if(OPTIMIZE_SIZE)
  # -Os: Optimize for size
  set(CMAKE_CXX_FLAGS_RELEASE "-Os ${CMAKE_CXX_FLAGS_RELEASE}")
else()
  # -O2: Moderate opt.
  set(CMAKE_CXX_FLAGS_RELEASE "-O2 ${CMAKE_CXX_FLAGS_RELEASE}")
endif()

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g")

# Option to register quantized ops with quantized kernels. See
# kernels/quantized/CMakeLists.txt
option(REGISTER_QUANTIZED_OPS
       "Register quantized ops defined in kernels/quantized/" OFF)

option(EXECUTORCH_BUILD_SIZE_TEST "Whether to build size test" OFF)

# Build xnn_executor_runner which depends on XNNPACK
option(EXECUTORCH_BUILD_XNNPACK
       "Build xnn_executor_runner which depends on XNNPACK" OFF)

# Build the vulkan delegate along with the vulkan executor_runner
option(EXECUTORCH_BUILD_VULKAN
       "Build the Vulkan delegate and the Vulkan executor_runner" OFF)

option(EXECUTORCH_BUILD_SDK
       "Build the ExecuTorch SDK library and the SDK example runner.")

# Build mps_executor_runner which depends on MPSGraph framework
option(EXECUTORCH_BUILD_MPS "Build mps_executor_runner which depends on MPS"
       OFF)

# Build dataloader extension library
option(EXECUTORCH_BUILD_EXTENSION_DATA_LOADER
       "Build the extension/data_loader directory" OFF)

# Build module extension library
option(EXECUTORCH_BUILD_EXTENSION_MODULE
       "Build the extension/module directory" OFF)

# Build the runner_util extension library
option(EXECUTORCH_BUILD_EXTENSION_RUNNER_UTIL
       "Build the extension/runner_util directory" OFF)

# Build test binaries that rely on googletest
option(EXECUTORCH_BUILD_GTESTS
       "Build googletest based test binaries" OFF)

# Build the AOT util extension library
option(EXECUTORCH_BUILD_EXTENSION_AOT_UTIL
       "Build the extension/aot_util directory" OFF)

if(NOT BUCK2)
  set(BUCK2 buck2)
endif()

if(NOT PYTHON_EXECUTABLE)
  set(PYTHON_EXECUTABLE python3)
endif()

# TODO(dbort): Fix these warnings and remove this flag.
set(_common_compile_options -Wno-deprecated-declarations -fPIC)

# Let files say "include <executorch/path/to/header.h>".
set(_common_include_directories ${CMAKE_CURRENT_SOURCE_DIR}/..)

#
# The `_<target>_srcs` lists are defined by including ${EXECUTORCH_SRCS_FILE}.
#

if(NOT EXECUTORCH_SRCS_FILE)
  # A file wasn't provided. Run a script to extract the source lists from the
  # buck2 build system and write them to a file we can include.
  #
  # NOTE: This will only happen once during cmake setup, so it will not re-run
  # if the buck2 targets change.
  message(STATUS "executorch: Generating source lists")
  set(EXECUTORCH_SRCS_FILE "${CMAKE_CURRENT_BINARY_DIR}/executorch_srcs.cmake")
  extract_sources(${EXECUTORCH_SRCS_FILE})
endif()

# This file defines the `_<target>__srcs` variables used below.
message(STATUS "executorch: Using sources file ${EXECUTORCH_SRCS_FILE}")
include(${EXECUTORCH_SRCS_FILE})

#
# Modify default options when cross-compiling.
#
# The intent is for the EXECUTORCH_BUILD_HOST_TARGETS option to affect the
# default ON/OFF values of host targets around the tree. This way, a user can
# disable EXECUTORCH_BUILD_HOST_TARGETS to disable all host targets, and then
# optionally re-enable some of those targets. Or they could leave
# EXECUTORCH_BUILD_HOST_TARGETS enabled and then optionally disable any given
# host target.
#
# We can then use various cross-compilation hints to set the default value of
# EXECUTORCH_BUILD_HOST_TARGETS, which can still be overridden if desired.
#

# Detect if an iOS toolchain is set.
if(CMAKE_TOOLCHAIN_FILE MATCHES ".*(iOS|ios\.toolchain)\.cmake$")
  set(CMAKE_TOOLCHAIN_IOS ON)
else()
  set(CMAKE_TOOLCHAIN_IOS OFF)
endif()

# Detect if an Android toolchain is set.
if(CMAKE_TOOLCHAIN_FILE MATCHES ".*android\.toolchain\.cmake$")
  set(CMAKE_TOOLCHAIN_ANDROID ON)
else()
  set(CMAKE_TOOLCHAIN_ANDROID OFF)
endif()

# EXECUTORCH_BUILD_HOST_TARGETS: Option to control the building of host-only
# tools like `flatc`, along with example executables like `executor_runner` and
# libraries that it uses, like `gflags`. Disabling this can be helpful when
# cross-compiling, but some required tools that would have been built need to be
# provided directly (via, for example, FLATC_EXECUTABLE).
cmake_dependent_option(EXECUTORCH_BUILD_HOST_TARGETS "Build host-only targets."
                       ON "NOT CMAKE_TOOLCHAIN_IOS" OFF)

#
# flatc: Flatbuffer commandline tool to generate .h files from .fbs files
#
cmake_dependent_option(EXECUTORCH_BUILD_FLATC "Build the flatc executable." ON
                       "NOT FLATC_EXECUTABLE;EXECUTORCH_BUILD_HOST_TARGETS" OFF)

if(EXECUTORCH_BUILD_FLATC)
  if(FLATC_EXECUTABLE)
    # We could ignore this, but it could lead to confusion about which `flatc`
    # is actually being used.
    message(
      FATAL_ERROR "May not set both EXECUTORCH_BUILD_FLATC and FLATC_EXECUTABLE"
    )
  endif()
  set(FLATC_EXECUTABLE flatc)
  set(FLATBUFFERS_BUILD_FLATC ON CACHE BOOL "")
  set(FLATBUFFERS_BUILD_FLATHASH OFF CACHE BOOL "")
  set(FLATBUFFERS_BUILD_FLATLIB OFF CACHE BOOL "")
  set(FLATBUFFERS_BUILD_TESTS OFF CACHE BOOL "")
  set(FLATBUFFERS_INSTALL OFF CACHE BOOL "")
  add_subdirectory(third-party/flatbuffers)
endif()
if(NOT FLATC_EXECUTABLE)
  message(
    FATAL_ERROR
      "FLATC_EXECUTABLE must be set when EXECUTORCH_BUILD_FLATC is disabled. "
      "Note that EXECUTORCH_BUILD_FLATC may be disabled implicitly when "
      "cross-compiling or when EXECUTORCH_BUILD_HOST_TARGETS is disabled.")
endif()

#
# program_schema: Generated .h files from schema/*.fbs inputs
#
add_subdirectory(schema)

#
# executorch: Core runtime library
#
# Only contains primitive operators; does not contain portable kernels or other
# full operators. Does not contain any backends.
#

add_library(executorch ${_executorch__srcs})
target_link_libraries(executorch PRIVATE program_schema)
target_link_options_shared_lib(executorch)
# Check if dl exists for this toolchain and only then link it.
find_library(DL_LIBRARY_EXISTS NAMES dl)
# Check if the library was found
if(DL_LIBRARY_EXISTS)
  target_link_libraries(executorch PRIVATE dl) # For dladdr()
endif()
target_include_directories(executorch PUBLIC ${_common_include_directories})
target_compile_options(executorch PUBLIC ${_common_compile_options})
if(MAX_KERNEL_NUM)
  target_compile_definitions(executorch
                             PRIVATE MAX_KERNEL_NUM=${MAX_KERNEL_NUM})
endif()

#
# portable_ops_lib: A library to register core ATen ops using portable kernels,
# see kernels/portable/CMakeLists.txt.
#
# Real integrations should supply their own YAML file that only lists the
# operators necessary for the models that will run.
#
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/kernels/portable)

#
# gflags: Commandline flag host library.
#
cmake_dependent_option(EXECUTORCH_BUILD_GFLAGS "Build the gflags library." ON
                       EXECUTORCH_BUILD_HOST_TARGETS OFF)
if(EXECUTORCH_BUILD_GFLAGS)
  add_subdirectory(third-party/gflags)
endif()

# Install `executorch` library as well as `executorch-config.cmake` under
# ${CMAKE_INSTALL_PREFIX}/
install(
  TARGETS executorch
  DESTINATION lib
  INCLUDES
  DESTINATION ${_common_include_directories})
install(FILES build/executorch-config.cmake DESTINATION lib/cmake/ExecuTorch)

#
# executor_runner: Host tool that demonstrates program execution.
#
cmake_dependent_option(
  EXECUTORCH_BUILD_EXECUTOR_RUNNER "Build the executor_runner executable" ON
  EXECUTORCH_BUILD_HOST_TARGETS OFF)
if(EXECUTORCH_BUILD_EXECUTOR_RUNNER)
  # Baseline libraries that executor_runner will link against.
  set(_executor_runner_libs executorch portable_ops_lib gflags)

  # Generate lib to register quantized ops
  if(REGISTER_QUANTIZED_OPS)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/kernels/quantized)
    list(APPEND _executor_runner_libs quantized_ops_lib)
  endif()

  add_executable(executor_runner ${_executor_runner__srcs})
  if(CMAKE_BUILD_TYPE STREQUAL "Release" AND NOT APPLE)
    target_link_options(executor_runner PRIVATE "LINKER:--gc-sections")
  endif()
  target_link_libraries(executor_runner ${_executor_runner_libs})
  target_compile_options(executor_runner PUBLIC ${_common_compile_options})
endif()

# Add googletest if any test targets should be built
if(EXECUTORCH_BUILD_GTESTS)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/third-party/googletest)
endif()

if(EXECUTORCH_BUILD_SDK)
  set(EXECUTORCH_BUILD_EXTENSION_DATA_LOADER
      ON
      CACHE BOOL "EXECUTORCH_BUILD_EXTENSION_DATA_LOADER" FORCE)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/sdk)
endif()

if(EXECUTORCH_BUILD_EXTENSION_APPLE)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/extension/apple)
endif()

if(EXECUTORCH_BUILD_EXTENSION_DATA_LOADER)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/extension/data_loader)
endif()

if(EXECUTORCH_BUILD_EXTENSION_MODULE)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/extension/module)
endif()

if(EXECUTORCH_BUILD_EXTENSION_RUNNER_UTIL)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/extension/runner_util)
endif()

if(EXECUTORCH_BUILD_EXTENSION_AOT_UTIL)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/extension/aot_util)
endif()

option(EXECUTORCH_BUILD_XNNPACK "Build the backends/xnnpack directory" OFF)
if(EXECUTORCH_BUILD_XNNPACK)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/backends/xnnpack)
endif()

if(EXECUTORCH_BUILD_VULKAN)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/backends/vulkan)
endif()

option(EXECUTORCH_BUILD_ANDROID_JNI "Build Android JNI" OFF)
if(EXECUTORCH_BUILD_ANDROID_JNI)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/examples/models/llama2/runner)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/extension/android)
endif()

option(EXECUTORCH_BUILD_QNN "Build the backends/qualcomm directory" OFF)
if(EXECUTORCH_BUILD_QNN)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/backends/qualcomm)
endif()

option(EXECUTORCH_BUILD_ARM_BAREMETAL
       "Build the Arm Baremetal flow for Cortex-M and Ethos-U" OFF)
if(EXECUTORCH_BUILD_ARM_BAREMETAL)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/backends/arm)
endif()

option(EXECUTORCH_BUILD_MPS "Build the MPS Backend" OFF)
if(EXECUTORCH_BUILD_MPS)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/backends/apple/mps)
endif()

option(EXECUTORCH_BUILD_COREML "Build the Core ML Backend" OFF)
if(EXECUTORCH_BUILD_COREML)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/backends/apple/coreml)
endif()

option(EXECUTORCH_BUILD_PYBIND "Build the Python Bindings" OFF)
if(EXECUTORCH_BUILD_PYBIND)

  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/third-party/pybind11)

  if(NOT EXECUTORCH_BUILD_EXTENSION_DATA_LOADER)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/extension/data_loader)
  endif()

  if(NOT EXECUTORCH_BUILD_SDK)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/sdk)
  endif()

  if(EXECUTORCH_BUILD_COREML)
    set(PYBIND_LINK_COREML "coremldelegate")
  endif()

  if(EXECUTORCH_BUILD_MPS)
    set(PYBIND_LINK_MPS "mpsdelegate")
  endif()

  if(EXECUTORCH_BUILD_XNNPACK)
    set(PYBIND_LINK_XNNPACK "xnnpack_backend")
  endif()

  # find pytorch lib, to allow pybind to take at::Tensor as input/output
  find_package(Torch CONFIG REQUIRED)
  find_library(TORCH_PYTHON_LIBRARY torch_python
               PATHS "${TORCH_INSTALL_PREFIX}/lib")

  # compile options for pybind

  set(_pybind_compile_options -Wno-deprecated-declarations -fPIC -frtti
                              -fexceptions)
  # util lib
  add_library(
    util
    ${CMAKE_CURRENT_SOURCE_DIR}/extension/evalue_util/print_evalue.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/extension/aten_util/aten_bridge.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/util/read_file.cpp
  )
  target_include_directories(util PUBLIC ${_common_include_directories}
                                         ${TORCH_INCLUDE_DIRS})
  target_compile_options(util PUBLIC ${_pybind_compile_options})
  target_link_libraries(util PRIVATE torch c10 executorch)

  # pybind portable_lib
  pybind11_add_module(portable_lib extension/pybindings/pybindings.cpp)
  target_compile_definitions(portable_lib
                             PUBLIC EXECUTORCH_PYTHON_MODULE_NAME=portable_lib)
  target_include_directories(portable_lib PRIVATE ${TORCH_INCLUDE_DIRS})
  target_compile_options(portable_lib PUBLIC ${_pybind_compile_options})
  target_link_libraries(portable_lib
    PUBLIC
      ${TORCH_PYTHON_LIBRARY}
      bundled_program
      etdump
      executorch
      extension_data_loader
      portable_ops_lib
      util
      torch
      ${PYBIND_LINK_COREML}
      ${PYBIND_LINK_MPS}
      ${PYBIND_LINK_XNNPACK}
  )

  install(TARGETS portable_lib
          LIBRARY DESTINATION executorch/extension/pybindings)
endif()

# Print all summary
executorch_print_configuration_summary()

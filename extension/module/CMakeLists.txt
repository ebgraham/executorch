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

# Source root directory for executorch.
if(NOT EXECUTORCH_ROOT)
  set(EXECUTORCH_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../..)
endif()

list(TRANSFORM _extension_module__srcs PREPEND "${EXECUTORCH_ROOT}/")
if(CMAKE_TOOLCHAIN_IOS OR CMAKE_TOOLCHAIN_ANDROID)
  # Building a share library on iOS requires code signing
  # On Android we see duplicated registration when using shared lib
  add_library(extension_module STATIC ${_extension_module__srcs})
else()
  add_library(extension_module SHARED ${_extension_module__srcs})
endif()
target_link_libraries(extension_module PRIVATE executorch extension_data_loader)
target_include_directories(extension_module PUBLIC ${EXECUTORCH_ROOT}/..)
target_compile_options(extension_module PUBLIC -Wno-deprecated-declarations
                                               -fPIC)

# Install libraries
install(
  TARGETS extension_module
  DESTINATION lib
  INCLUDES
  DESTINATION ${_common_include_directories})

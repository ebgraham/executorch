# Copyright (c) Meta Platforms, Inc. and affiliates.
# Copyright 2024 Arm Limited and/or its affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
import shutil
import unittest

from typing import Tuple

import torch
from executorch.backends.arm.test.test_models import TosaProfile
from executorch.backends.arm.test.tester.arm_tester import ArmBackendSelector, ArmTester
from parameterized import parameterized

# TODO: fixme! These globs are a temporary workaround. Reasoning:
# Running the jobs in _unittest.yml will not work since that environment don't
# have the vela tool, nor the tosa_reference_model tool. Hence, we need a way to
# run what we can in that env temporarily. Long term, vela and tosa_reference_model
# should be installed in the CI env.
TOSA_REF_MODEL_INSTALLED = shutil.which("tosa_reference_model")
VELA_INSTALLED = shutil.which("vela")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

seed = 42
torch.manual_seed(seed)
test_data_suite = [
    # (test_name, test_data, out_features)
    (
        "model_linear_rank1_zeros",
        torch.zeros(10, 10),
        10,
    ),
    (
        "model_linear_rank1_ones",
        torch.ones(10, 10),
        10,
    ),
    (
        "model_linear_rank1_negative_ones",
        torch.ones(10, 10) * (-1),
        10,
    ),
    (
        "model_linear_rank1_rand",
        torch.rand(10, 10),
        10,
    ),
    (
        "model_linear_rank1_negative_large_rand",
        torch.rand(10, 10) * (-100),
        10,
    ),
    (
        "model_linear_rank1_large_randn",
        torch.randn(10, 10) * 100,
        10,
    ),
    (
        "model_linear_rank4_zeros",
        torch.zeros(5, 10, 25, 20),
        30,
    ),
    (
        "model_linear_rank4_ones",
        torch.ones(5, 10, 25, 20),
        30,
    ),
    (
        "model_linear_rank4_negative_ones",
        torch.ones(5, 10, 25, 20) * (-1),
        30,
    ),
    (
        "model_linear_rank4_rand",
        torch.rand(5, 10, 25, 20),
        30,
    ),
    (
        "model_linear_rank4_negative_large_rand",
        torch.rand(5, 10, 25, 20) * (-100),
        30,
    ),
    (
        "model_linear_rank4_large_randn",
        torch.randn(5, 10, 25, 20) * 100,
        30,
    ),
]


class TestLinear(unittest.TestCase):
    class Linear(torch.nn.Module):
        def __init__(
            self,
            in_features: int,
            out_features: int = 3,
            bias: bool = True,
        ):
            super().__init__()
            self.fc = torch.nn.Linear(
                in_features=in_features,
                out_features=out_features,
                bias=bias,
            )

        def forward(self, x):
            return self.fc(x)

    def _test_linear_tosa_MI_pipeline(
        self, module: torch.nn.Module, test_data: Tuple[torch.Tensor]
    ):
        tester = (
            ArmTester(
                module,
                inputs=test_data,
                profile=TosaProfile.MI,
                backend=ArmBackendSelector.TOSA,
            )
            .export()
            .check_count({"torch.ops.aten.addmm.default": 1})
            .check_not(["torch.ops.quantized_decomposed"])
            .to_edge()
            .partition()
            .check_count({"torch.ops.higher_order.executorch_call_delegate": 1})
            .to_executorch()
        )
        if TOSA_REF_MODEL_INSTALLED:
            tester.run_method().compare_outputs()
        else:
            logger.warning(
                "TOSA ref model tool not installed, skip numerical correctness tests"
            )

    def _test_linear_tosa_BI_pipeline(
        self, module: torch.nn.Module, test_data: Tuple[torch.Tensor]
    ):
        tester = (
            ArmTester(
                module,
                inputs=test_data,
                profile=TosaProfile.BI,
                backend=ArmBackendSelector.TOSA,
            )
            .quantize()
            .export()
            .check_count({"torch.ops.aten.addmm.default": 1})
            .check(["torch.ops.quantized_decomposed"])
            .to_edge()
            .partition()
            .check_count({"torch.ops.higher_order.executorch_call_delegate": 1})
            .to_executorch()
        )
        if TOSA_REF_MODEL_INSTALLED:
            tester.run_method().compare_outputs(qtol=True)
        else:
            logger.warning(
                "TOSA ref model tool not installed, skip numerical correctness tests"
            )

    def _test_linear_tosa_u55_BI_pipeline(
        self, module: torch.nn.Module, test_data: Tuple[torch.Tensor]
    ):
        (
            ArmTester(
                module,
                inputs=test_data,
                profile=TosaProfile.BI,
                backend=ArmBackendSelector.ETHOS_U55,
            )
            .quantize()
            .export()
            .check_count({"torch.ops.aten.addmm.default": 1})
            .check(["torch.ops.quantized_decomposed"])
            .to_edge()
            .partition()
            .check_count({"torch.ops.higher_order.executorch_call_delegate": 1})
            .to_executorch()
        )

    @parameterized.expand(test_data_suite)
    def test_linear_tosa_MI(
        self,
        test_name: str,
        test_data: torch.Tensor,
        out_features: int,
    ):
        in_features = test_data.shape[-1]
        test_data = (test_data,)
        self._test_linear_tosa_MI_pipeline(
            self.Linear(
                in_features=in_features,
                out_features=out_features,
            ),
            test_data,
        )

    @parameterized.expand(test_data_suite)
    def test_linear_tosa_BI(
        self,
        test_name: str,
        test_data: torch.Tensor,
        out_features: int,
    ):
        in_features = test_data.shape[-1]
        test_data = (test_data,)
        self._test_linear_tosa_BI_pipeline(
            self.Linear(in_features=in_features, out_features=out_features), test_data
        )

    @parameterized.expand(test_data_suite)
    @unittest.skip("This does not work as of now")
    def test_linear_tosa_u55_BI(
        self,
        test_name: str,
        test_data: torch.Tensor,
        out_features: int,
    ):
        in_features = test_data.shape[-1]
        test_data = (test_data,)
        self._test_linear_tosa_u55_BI_pipeline(
            self.Linear(
                in_features=in_features,
                out_features=out_features,
            ),
            test_data,
        )

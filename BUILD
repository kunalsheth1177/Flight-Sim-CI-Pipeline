load("@rules_python//python:defs.bzl", "py_library", "py_binary", "py_test")

py_library(
    name = "sim_lib",
    srcs = [
        "sim/__init__.py",
        "sim/physics.py",
        "sim/telemetry.py",
        "sim/rpc.py",
        "sim/scenarios.py",
    ],
    imports = ["."],
    deps = [
        "@pip_deps//:numpy",
        "@pip_deps//:pandas",
        "@pip_deps//:matplotlib",
    ],
)

py_binary(
    name = "sim_cli",
    srcs = ["sim/cli.py"],
    main = "sim/cli.py",
    deps = [":sim_lib"],
)

py_test(
    name = "test_golden_takeoff",
    srcs = ["tests/test_golden_takeoff.py"],
    deps = [":sim_lib"],
)

py_test(
    name = "test_latency_loss",
    srcs = ["tests/test_latency_loss.py"],
    deps = [":sim_lib"],
)


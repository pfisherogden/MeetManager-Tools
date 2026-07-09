from __future__ import annotations

import concurrent.futures
import os
from unittest.mock import patch

from mm_to_json.platform_setup import setup_platform_env


def test_multiprocessing_parent_monitor_ignored_in_child():
    """
    Verifies that MONITOR_PARENT_PROCESS=true does not launch the monitor
    thread in child worker processes, preventing them from exiting via os._exit(0)
    and breaking the process pool.
    """
    with patch.dict(os.environ, {"MONITOR_PARENT_PROCESS": "true"}):
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            # First task runs setup_platform_env in child worker process
            f1 = executor.submit(setup_platform_env)
            f1.result(timeout=5)  # Should complete successfully

            # Second task should also run successfully without BrokenProcessPool
            f2 = executor.submit(sum, [1, 2, 3])
            res = f2.result(timeout=5)
            assert res == 6

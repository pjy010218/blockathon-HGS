"""The demo is a deliverable, so it is tested like one."""

from __future__ import annotations

import demo


def test_demo_runs_and_detects_tampering(capsys) -> None:
    demo.main()
    output = capsys.readouterr().out

    assert "recomputed digest matches : True" in output      # an untouched record verifies
    assert "matches what was anchored     : False" in output  # an altered one does not
    assert "is the altered version on-chain: False" in output
    assert "anchored: False" in output                        # absence is visible

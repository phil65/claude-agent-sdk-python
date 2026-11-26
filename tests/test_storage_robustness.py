"""Transcript loaders skip non-object JSON lines; GC pausing nests across threads."""

from __future__ import annotations

import gc
import threading
from typing import TYPE_CHECKING

from clawd_code_sdk.storage.chain import read_raw_chain_entries
from clawd_code_sdk.storage.helpers import _gc_paused, read_session


if TYPE_CHECKING:
    from pathlib import Path


def test_loaders_skip_non_object_lines(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    path.write_text('[1]\n"text"\n42\n{"type": "custom-title", "customTitle": "x"}\n')
    read_session(path)  # used to raise TypeError: Expected dict, got list
    assert read_raw_chain_entries(path) == {}


def test_overlapping_gc_pauses_restore_gc_at_the_end() -> None:
    assert gc.isenabled()
    first_in = threading.Event()
    second_in = threading.Event()
    first_out = threading.Event()
    states: list[bool] = []

    def first() -> None:
        with _gc_paused():
            first_in.set()
            second_in.wait(5)
        first_out.set()

    def second() -> None:
        first_in.wait(5)
        with _gc_paused():
            second_in.set()
            first_out.wait(5)
            states.append(gc.isenabled())  # first one left: GC must still be off

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert states == [False]
    assert gc.isenabled()

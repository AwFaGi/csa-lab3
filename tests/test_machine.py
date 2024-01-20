import contextlib
import io
import logging
import os
import tempfile

import pytest

from csa_lab3 import translator, machine


@pytest.mark.golden_test("golden/*.yml")
def test_bar(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = os.path.join(tmpdir, "source.aul")
        target_file = os.path.join(tmpdir, "source.bin")
        input_buffer = list(golden["stdin"]) + ["\0"]

        with open(source_file, "w", encoding="utf-8") as file:
            file.write(golden["source_code"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.compile_code(source_file, target_file)
            print("="*25)
            machine.simulation(target_file, input_buffer)

        with open(f"{target_file}.txt", encoding="utf-8") as file:
            human_readable = file.read()

        assert human_readable.rstrip("\n") == golden.out["out_code_readable"]
        assert stdout.getvalue().rstrip("\n") == golden.out["stdout"]
        assert caplog.text.rstrip("\n") == golden.out["out_log"]

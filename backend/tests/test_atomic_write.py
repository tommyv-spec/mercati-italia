import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atomic_write


class AtomicWriteTests(unittest.TestCase):
    def test_retries_a_briefly_locked_target_then_gives_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "a.tmp", Path(tmp) / "a.json"
            source.write_text("new", "utf-8")
            real, calls = Path.replace, []
            def locked_twice(self, path):
                calls.append(path)
                if len(calls) <= 2:
                    raise PermissionError("[WinError 5] Access is denied")
                return real(self, path)
            with patch.object(Path, "replace", locked_twice), patch.object(atomic_write.time, "sleep"):
                atomic_write.replace(source, target)
            self.assertEqual((len(calls), target.read_text("utf-8")), (3, "new"))
            with patch.object(Path, "replace", side_effect=PermissionError("locked")), \
                    patch.object(atomic_write.time, "sleep"), self.assertRaises(PermissionError):
                atomic_write.replace(target, source)


if __name__ == "__main__":
    unittest.main()

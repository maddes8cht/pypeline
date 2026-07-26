import io
from contextlib import redirect_stdout
from debug import Debug


class TestDebug:
    def test_disabled_by_default(self):
        d = Debug()
        assert d.enabled is False

    def test_enabled_prints(self):
        d = Debug(enabled=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            d.print("hello")
        assert buf.getvalue() == "hello\n"

    def test_disabled_does_not_print(self):
        d = Debug(enabled=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            d.print("should not appear")
        assert buf.getvalue() == ""

    def test_prefix_formatting(self):
        d = Debug(enabled=True, prefix="[TEST]")
        assert d.prefix == "[TEST] "

    def test_prefix_trailing_spaces_stripped(self):
        d = Debug(enabled=True, prefix="[TEST]  ")
        assert d.prefix == "[TEST] "

    def test_prefix_empty(self):
        d = Debug(enabled=True, prefix="")
        assert d.prefix == ""

    def test_print_with_prefix(self):
        d = Debug(enabled=True, prefix="[DEBUG]")
        buf = io.StringIO()
        with redirect_stdout(buf):
            d.print("msg")
        assert buf.getvalue() == "[DEBUG]  msg\n"

    def test_on_enables(self):
        d = Debug(enabled=False)
        d.on()
        assert d.enabled is True

    def test_off_disables(self):
        d = Debug(enabled=True)
        d.off()
        assert d.enabled is False

    def test_print_multiple_args(self):
        d = Debug(enabled=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            d.print("a", "b", "c")
        assert buf.getvalue() == "a b c\n"

    def test_print_kwargs_passed_through(self):
        d = Debug(enabled=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            d.print("hello", end="")
        assert buf.getvalue() == "hello"

    def test_print_disabled_with_prefix(self):
        d = Debug(enabled=False, prefix="[X]")
        buf = io.StringIO()
        with redirect_stdout(buf):
            d.print("nope")
        assert buf.getvalue() == ""

    def test_toggle_on_off(self):
        d = Debug(enabled=False)
        d.on()
        d.off()
        assert d.enabled is False
        d.on()
        assert d.enabled is True

    def test_instance_prefixes(self):
        from debug import debug, verbose
        assert debug.prefix == "[DEBUG] "
        assert debug.enabled is False
        assert verbose.prefix == ""
        assert verbose.enabled is False

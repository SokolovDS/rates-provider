import pytest

from main import main


def test_main_prints_hello_world(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    captured = capsys.readouterr()
    assert captured.out == "hello world\n"

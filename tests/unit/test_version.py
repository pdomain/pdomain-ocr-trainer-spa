from pdomain_ocr_trainer_spa._version import __version__


def test_runtime_version_is_not_hard_coded_alpha() -> None:
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ != "0.1.0a0"

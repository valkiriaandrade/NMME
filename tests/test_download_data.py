import argparse
import io
import socket
import urllib.error

import pytest

CPC = "https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_figure_plan_matches_repository_layout(download_module):
    from conftest import ROOT

    plan = {item.path.as_posix(): item.url for item in download_module.figure_plan()}
    anomaly = "nmme_202407_anomalies/NMME.prate.202407.ENSMEAN.anom.nc"
    assert plan[anomaly] == f"{CPC}/2024070800/NMME.prate.202407.ENSMEAN.anom.nc"
    assert plan["CFSv2.prate.202404.ENSMEAN.fcst.nc"].startswith(f"{CPC}/2024040800/")
    committed = [path for path in plan if path != anomaly]
    assert len(committed) == 9
    assert all((ROOT / "data" / path).exists() for path in committed)  # committed samples


def test_figure_plan_covers_make_figures(download_module):
    from conftest import load_script

    make_figures = load_script("make_figures")
    folders = {item.path.parts[0] for item in download_module.figure_plan()}
    for figure_set in make_figures.FIGURE_SETS:
        for source in figure_set.inputs:
            assert source in folders


def test_custom_plan(download_module):
    items = download_module.custom_plan(["202410"], ["prate", "tmax"], "anom", ["NMME"])
    assert [i.path.as_posix() for i in items] == [
        "nmme_202410_anomalies/NMME.prate.202410.ENSMEAN.anom.nc",
        "nmme_202410_anomalies/NMME.tmax.202410.ENSMEAN.anom.nc",
    ]
    with pytest.raises(argparse.ArgumentTypeError):
        download_module.parse_run("2024-10")


def test_fetch_downloads_then_skips(tmp_path, download_module):
    def opener(request, timeout):
        return FakeResponse(b"CDF")

    dest = tmp_path / "a.nc"
    assert download_module.fetch("https://x/a.nc", dest, opener=opener) is True
    assert download_module.fetch("https://x/a.nc", dest, opener=opener) is False


def test_missing_file_gives_clear_error(tmp_path, download_module):
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    with pytest.raises(download_module.DownloadError, match="Not found on the server"):
        download_module.fetch("https://x/missing.nc", tmp_path / "m.nc", opener=opener)


def test_main_dry_run(capsys, download_module):
    assert download_module.main(["--dry-run"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 10


def test_network_is_blocked_in_tests():
    with pytest.raises(RuntimeError, match="must not use the network"):
        socket.create_connection(("ftp.cpc.ncep.noaa.gov", 443))


class SizedResponse(FakeResponse):
    """A response that announces ``size`` bytes in Content-Length (whatever it sends)."""

    def __init__(self, body, size):
        super().__init__(body)
        self.headers = {"Content-Length": str(size)}


def test_truncated_download_is_retried_and_never_kept(tmp_path, monkeypatch, download_module):
    monkeypatch.setattr(download_module.time, "sleep", lambda seconds: None)
    answers = [SizedResponse(b"CDF", 10), SizedResponse(b"CDF-whole!", 10)]
    dest = tmp_path / "run.nc"
    opener = lambda request, timeout: answers.pop(0)  # noqa: E731
    assert download_module.fetch("https://x/run.nc", dest, opener=opener) is True
    assert dest.read_bytes() == b"CDF-whole!" and not answers

    always_short = lambda request, timeout: SizedResponse(b"CDF", 10)  # noqa: E731
    with pytest.raises(download_module.DownloadError, match="received 3 of 10 bytes"):
        download_module.fetch("https://x/b.nc", tmp_path / "b.nc", opener=always_short)
    assert list(tmp_path.iterdir()) == [dest]  # no truncated file, no .part left behind


def test_incomplete_chunked_response_is_retried(tmp_path, monkeypatch, download_module):
    import http.client

    monkeypatch.setattr(download_module.time, "sleep", lambda seconds: None)

    class Broken(FakeResponse):
        def read(self, *args):
            raise http.client.IncompleteRead(b"CD", 8)

    answers = [Broken(b""), FakeResponse(b"CDF")]
    dest = tmp_path / "run.nc"
    assert download_module.fetch("https://x/run.nc", dest, opener=lambda r, timeout: answers.pop(0))
    assert dest.read_bytes() == b"CDF"


def test_selection_options_need_a_run(download_module):
    for option in (["--variable", "tmax"], ["--kind", "fcst"], ["--model", "CFSv2"]):
        with pytest.raises(SystemExit):
            download_module.main([*option, "--dry-run"])


@pytest.mark.parametrize("value", ["../x", "a/b", "..", "", "x y"])
def test_model_and_variable_names_cannot_leave_the_data_folder(value, download_module):
    with pytest.raises(argparse.ArgumentTypeError):
        download_module.parse_name(value)
    assert download_module.parse_name("GEM5.2_NEMO") == "GEM5.2_NEMO"

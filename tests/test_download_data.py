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

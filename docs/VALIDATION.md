# Refactoring validation

- Python 3.11 on Windows: tests for the calendar, members, missing values, grids and maps.
- Produced nine maps from the real file `CFSv2.prate.202404.ENSMEAN.fcst.nc`, with April
  2024 as the first target month and mm/s as the unit, in `output/cfsv2/`.
- May uses 31 days, February accounts for leap years and December rolls over the year.
- Editable install of the package and Ruff checks executed.

The user provides the target month and the unit: the initialisation month is not assumed
to be the validity month. Non-Gregorian calendars are not converted automatically.
Temperature anomalies in K have the same numerical magnitude in °C.
Absolute forecast files must not be used as anomaly files.

## English translation and figure regeneration (v0.2.0)

- Folders and files renamed to English; code, CLI help, messages, titles and labels
  translated. Unit conversion and ensemble mean are unchanged. The colour scales are those of
  the original scripts (restored in commit 9b5c932, "Restore the original colour scales", after a first
  English version that used `YlGnBu`): precipitation `jet`, 0–240 mm/month every 20;
  precipitation anomaly `BrBG`, −150…150 every 30; temperature anomaly `RdBu_r`, −6.5…6.5 °C
  every 1.
- Regenerated with `make figures`: `figures/cfsv2_precipitation_2024-05.png` (April 2024
  run) and the nine `figures/nmme_tmax_anomaly_YYYY-MM.png` maps (July 2024 run).
- Not regenerated: the nine `figures/precipitation_anomaly/*.png` maps. They need
  precipitation anomaly files, and the repository only contains absolute forecasts
  (`data/nmme_202407_forecasts/`). The original images are kept under their new names.

## Precipitation-anomaly source found, data download and smooth contours (v0.3.0)

- All NMME files in this repository come from the **NOAA CPC NMME real-time archive**
  (https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN/); the committed files are
  byte-identical to the files on that server.
- `scripts/download_data.py` (`make data`) downloads the files the figures need; the
  only one not committed is `NMME.prate.202407.ENSMEAN.anom.nc` (NMME ensemble
  precipitation anomaly, July 2024 run), saved under `data/nmme_202407_anomalies/`.
- The nine precipitation-anomaly maps are now regenerated from that file. Evidence that
  it is the source of the original maps:
  - the original script averaged every file in a local `fcst` folder (×30 days) and
    started the month labels at 07/2024; its `Dados/fcst` folder (now
    `data/nmme_202407_forecasts/`) holds the absolute
    forecasts, but the original maps show negative values, so they were made from the
    anomaly files of the same July 2024 run;
  - the CPC NMME ensemble anomaly equals the mean of the seven model anomalies exactly;
  - the original July 2024 map matches the CPC file closely (dry north-western Amazon,
    weak dry area over Uruguay, wetter north-east coast).
  Later lead months (e.g. October 2024) differ more from the original images; CPC appears
  to have revised the files after August 2024, which cannot be verified. The maps show the
  files as currently published.
- Monthly totals use each month's real length (since v0.2), not the fixed 30 days of the
  original script.
- Maps are drawn with filled contours (`contourf`) as in the original scripts.

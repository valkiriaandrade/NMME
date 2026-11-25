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
  translated. Unit conversion, ensemble mean, palettes (`YlGnBu`, `BrBG`, `RdBu_r`) and
  class levels are unchanged.
- Regenerated with `make figures`: `figures/cfsv2_precipitation_2024-05.png` (April 2024
  run) and the nine `figures/nmme_tmax_anomaly_YYYY-MM.png` maps (July 2024 run).
- Not regenerated: the nine `figures/precipitation_anomaly/*.png` maps. They need
  precipitation anomaly files, and the repository only contains absolute forecasts
  (`data/nmme_202407_forecasts/`). The original images are kept under their new names.

# Data terms

The code is under the [MIT licence](LICENSE). The data in `data/`, and the files
`make data` downloads, keep the terms of their providers.

## NMME (NOAA CPC)

The forecast files come from the NOAA Climate Prediction Center NMME real-time archive,
https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN/, produced by NOAA CPC and the
participating modelling centres. As US federal government data they are in the public domain.

## State boundaries (IBGE)

The state borders drawn on the maps are the 2022 federative-unit boundary layer of the
Instituto Brasileiro de Geografia e Estatística (IBGE), *Malha Territorial 2022*
(https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html), file `BR_UF_2022.zip`, downloaded by `make data` into `data/BR_UF_2022/`.
It is published as open public data; cite IBGE as the source. The MERGE and SAMeT
repositories use the same file.

## Natural Earth

Coastlines and borders outside Brazil (and on maps made without `--borders`) come from
[Natural Earth](https://www.naturalearthdata.com/) (public domain).

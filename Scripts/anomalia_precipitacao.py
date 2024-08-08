import os
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import BoundaryNorm

data_dir = "fcst"
def calcular_media_precipitacao(arquivos):
    datasets = []
    for arquivo in arquivos:
        ds = xr.open_dataset(arquivo, decode_times=False) 
        precip = ds['fcst'] * 60 * 60 * 24 * 30
        datasets.append(precip)
    combined = xr.concat(datasets, dim='file')
    media_mensal = combined.mean(dim='file')
    return media_mensal
def plotar_precipitacao(media_mensal, meses, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    cmap = plt.cm.BrBG
    boundaries = list(range(-150, 151, 30))
    norm = BoundaryNorm(boundaries, ncolors=cmap.N, clip=False)
    for i, mes in enumerate(meses):
        precip = media_mensal.isel(target=i)
        lon = precip.lon.values
        lat = precip.lat.values
        data = precip.values
        plt.figure(figsize=(10, 6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        contour = ax.contourf(lon, lat, data, levels=boundaries, cmap=cmap, norm=norm, transform=ccrs.PlateCarree())
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.add_feature(cfeature.COASTLINE)
        states = cfeature.NaturalEarthFeature(
            category='cultural', scale='10m', facecolor='none',
            name='admin_1_states_provinces_lines')
        ax.add_feature(states, edgecolor='black', linewidth=0.5)
        brazil_border = cfeature.NaturalEarthFeature(
            category='cultural', scale='10m', facecolor='none',
            name='admin_0_countries')
        ax.add_feature(brazil_border, edgecolor='black', linewidth=1.0)
        ax.set_extent([-74, -34, -34, 6], crs=ccrs.PlateCarree())
        cbar = plt.colorbar(contour, ax=ax, extend='both', orientation='vertical', pad=0.05)
        cbar.set_ticks(boundaries)
        cbar.set_ticklabels(boundaries)
        cbar.set_label('Anomalia de Precipitação (mm/mês)')
        
        plt.title(f'Previsão de Anomalia de Precipitação - {mes}')
        plt.savefig(os.path.join(output_dir, f'precipitacao_anomalia_{mes.replace("/", "_")}.png'), bbox_inches='tight', pad_inches=0.0)  # Salvar sem espaços brancos
        plt.close()
arquivos = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.nc')]
media_mensal = calcular_media_precipitacao(arquivos)
num_meses = media_mensal.sizes['target']
meses = []
mes_atual = 7
ano_atual = 2024
for _ in range(num_meses):
    meses.append(f'{mes_atual:02d}/{ano_atual}')
    mes_atual += 1
    if mes_atual > 12:
        mes_atual = 1
        ano_atual += 1
output_dir = "output_precipitacao_anomalia"
plotar_precipitacao(media_mensal, meses, output_dir)

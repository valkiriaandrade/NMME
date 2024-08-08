import netCDF4 as nc
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.colors as mcolors

arquivo_nc = 'CFSv2.prate.202404.ENSMEAN.fcst.nc'
dataset = nc.Dataset(arquivo_nc, 'r')
target_index = 1  # May
latitudes = dataset.variables['lat'][:]
longitudes = dataset.variables['lon'][:]
dados_fcst = dataset.variables['fcst'][target_index, :, :]
seconds_in_month = 30 * 24 * 3600 
dados_fcst_mm_mes = dados_fcst * seconds_in_month
extent = [-74, -34, -34, 6]  
fig = plt.figure(figsize=(8, 10))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent(extent, crs=ccrs.PlateCarree())
states = cfeature.NaturalEarthFeature(category='cultural', scale='10m', facecolor='none', name='admin_1_states_provinces_lines')
brazil_border = cfeature.NaturalEarthFeature(category='cultural', scale='10m', facecolor='none', name='admin_0_countries')
ax.add_feature(states, edgecolor='black')
ax.add_feature(brazil_border, edgecolor='black')
cmap = plt.get_cmap('jet')
norm = mcolors.BoundaryNorm(boundaries=np.arange(0, 251, 20), ncolors=cmap.N)
cf = ax.contourf(longitudes, latitudes, dados_fcst_mm_mes, levels=np.arange(0, 251, 20),
                 cmap=cmap, norm=norm, extend='max')
cbar = plt.colorbar(cf, ax=ax, shrink=0.5, label='Precipitation (mm/month)')
cbar.set_ticks(np.arange(0, 251, 20)) 
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
plt.title('CFSv2 Accumulated Total Precipitation - May 2024')
plt.show()
dataset.close()

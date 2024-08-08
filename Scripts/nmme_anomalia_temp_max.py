import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.io.shapereader import Reader
from netCDF4 import Dataset
from datetime import datetime
from dateutil.relativedelta import relativedelta
from matplotlib.colors import TwoSlopeNorm

nc_file = 'NMME.tmax.202407.ENSMEAN.anom.nc'
data = Dataset(nc_file, mode='r')
lon = data.variables['lon'][:]
lat = data.variables['lat'][:]
fcst = data.variables['fcst'][:] 
data.close()
base_date = datetime(2024, 7, 1)
vmin = -6.5  
vmax = 6.5   
norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
for month_idx in range(fcst.shape[0]):
    current_date = base_date + relativedelta(months=+month_idx)
    date_str = current_date.strftime('%m-%Y')
    fig = plt.figure(figsize=(10, 5))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-74.5, -34.5, -34, 5.5], crs=ccrs.PlateCarree())  
    ax.coastlines()
    states = cfeature.NaturalEarthFeature(category='cultural', scale='50m', facecolor='none',
                                          name='admin_1_states_provinces_lines')
    borders = cfeature.NaturalEarthFeature(category='cultural', scale='50m', facecolor='none',
                                           name='admin_0_boundary_lines_land')
    ax.add_feature(states, edgecolor='black')
    ax.add_feature(borders, edgecolor='black')
    cf = ax.contourf(lon, lat, fcst[month_idx, :, :], transform=ccrs.PlateCarree(), cmap='RdBu_r', norm=norm, levels=np.arange(vmin, vmax + 1, 1))
    cbar = plt.colorbar(cf, ax=ax, orientation='vertical', ticks=np.arange(vmin, vmax + 1, 1))
    cbar.set_label('°C')
    plt.savefig(f'NMME_tmax_{date_str}_brasil.png', bbox_inches='tight', pad_inches=0.0)  # Salvar a figura
    plt.close()

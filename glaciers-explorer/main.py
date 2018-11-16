import os, numpy as np, pandas as pd, cartopy.crs as ccrs, bokeh
import holoviews as hv, geoviews as gv

from colorcet import kbc
from holoviews.util import Dynamic

_ = hv.extension('bokeh', width=100, logo=False);

df = pd.read_csv('./data/glaciers-explorer.csv')
df = df.sort_values(by='rgi_area_km2').reset_index(drop=True)
df['text'] = ['Id: {} - Area: {:.2f} km2 - Glaciers: {}'.format(i, a, n) 
              for i, (a, n) in enumerate(zip(df.rgi_area_km2, df.n_glaciers))]


data = hv.Dataset(df, [('cenlon', 'Longitude'), ('cenlat', 'Latitude')],
                     [('tstar_avg_prcp', 'Annual Precipitation (mm/yr)'),
                      ('rgi_area_km2', 'Area'), ('text', 'Info'),
                      ('tstar_avg_temp_mean_elev', 'Annual Temperature at avg. altitude'), 
                      ('dem_mean_elev', 'Elevation'), 'n_glaciers'])


temp_kw   = dict(num_bins=50, adjoin=False, normed=False, bin_range=data.range('tstar_avg_temp_mean_elev'))
prcp_kw   = dict(num_bins=50, adjoin=False, normed=False, bin_range=data.range('tstar_avg_prcp'))

geo_opts  = dict(width=600, height=300, cmap=kbc[::-1][20:], global_extent=True, logz=False, colorbar=True, 
                 projection=ccrs.Robinson(), color_index='rgi_area_km2', default_tools=[], toolbar=None, alpha=1.0)
elev_opts = dict(width=600, height=300, show_grid=True, color='#7d3c98', default_tools=[], toolbar=None, alpha=1.0)
temp_opts = dict(width=600, height=300,            fill_color='#f1948a', default_tools=[], toolbar=None, alpha=1.0)
prcp_opts = dict(width=600, height=300,            fill_color='#85c1e9', default_tools=[], toolbar=None, alpha=1.0)

geo_bg    = gv.feature.coastline.options(default_tools=['wheel_zoom'], toolbar=None)


def geo(data):   return gv.Points(data).options(**geo_opts)
def elev(data):  return data.to(hv.Scatter, 'dem_mean_elev', 'cenlat', []).options(**elev_opts)
def temp(data):  return data.hist('tstar_avg_temp_mean_elev', **temp_kw).options(**temp_opts)
def prcp(data):  return data.hist('tstar_avg_prcp',           **prcp_kw).options(**prcp_opts)

def count(data): return hv.Div('<p style="font-size:20px">Glaciers selected: ' + 
                        str(data.dframe().n_glaciers.sum()) + "</font>").options(height=40)


from bokeh.models import HoverTool
hover = HoverTool(tooltips=[('Info', '@{text}')])

static_geo  = geo( data).options(alpha=0.03, tools=[hover, 'box_select'])
static_elev = elev(data).options(alpha=0.1,  tools=[       'box_select'])
static_temp = temp(data).options(alpha=0.1)
static_prcp = prcp(data).options(alpha=0.1)

def combine_selections(**kwargs):
    "Combines selections on all available plots into a single selection by index."
    
    if all(not v for v in kwargs.values()):
        return slice(None)
    selection = {}
    for key, bounds in kwargs.items():
        if bounds is None:
            continue
        elif len(bounds) == 2:
            selection[key] = bounds
        else:
            xbound, ybound = key.split('__')
            selection[xbound] = bounds[0], bounds[2]
            selection[ybound] = bounds[1], bounds[3]
    return sorted(set(data.select(**selection).data.index))

def select_data(**kwargs):
    return data.iloc[combine_selections(**kwargs)] if kwargs else data


from holoviews.streams import Stream, BoundsXY, BoundsX

geo_bounds  = BoundsXY(source=static_geo,  rename={'bounds':  'cenlon__cenlat'})
elev_bounds = BoundsXY(source=static_elev, rename={'bounds':  'dem_mean_elev__cenlat'})
temp_bounds = BoundsX( source=static_temp, rename={'boundsx': 'tstar_avg_temp_mean_elev'})
prcp_bounds = BoundsX( source=static_prcp, rename={'boundsx': 'tstar_avg_prcp'})

selections  = [geo_bounds, elev_bounds, temp_bounds, prcp_bounds]

dyn_data  = hv.DynamicMap(select_data, streams=selections)
dyn_count = Dynamic(dyn_data, operation=count)

geomap  = geo_bg * static_geo  * Dynamic(dyn_data, operation=geo)
elevation        = static_elev * Dynamic(dyn_data, operation=elev)
temperature      = static_temp * Dynamic(dyn_data, operation=temp)
precipitation    = static_prcp * Dynamic(dyn_data, operation=prcp)


def clear_selections(arg=None):
    geo_bounds.update(bounds=None)
    elev_bounds.update(bounds=None)
    temp_bounds.update(boundsx=None)
    prcp_bounds.update(boundsx=None)
    Stream.trigger(selections)


import panel as pn
pn.extension()

clear_button = pn.widgets.Button(name='Clear selection')
clear_button.param.watch(clear_selections, 'clicks');


title       = '<p style="font-size:35px">World glaciers explorer</p>'
instruction = 'Box-select on each plot to subselect; clear selection to reset.<br>' +               'See the <a href="https://anaconda.org/jbednar/glaciers">Jupyter notebook</a> source code for how to build apps like this!'
oggm_logo   = '<a href="https://github.com/OGGM/OGGM-Dash"><img src="https://raw.githubusercontent.com/OGGM/oggm/master/docs/_static/logos/oggm_s_alpha.png" width=170></a>'
pv_logo     = '<a href="https://pyviz.org"><img src="http://pyviz.org/assets/PyViz_logo_wm.png" width=80></a>'


header = pn.Row(pn.Pane(oggm_logo, width=170), pn.Spacer(width=50), 
                pn.Column(pn.Pane(title, height=25, width=400), pn.Spacer(height=-15), pn.Pane(instruction, width=500)),
                pn.Spacer(width=180), pn.Column(pn.Pane(dyn_count), clear_button, pn.Spacer(height=-15)), 
                pn.Pane(pv_logo, width=80))

pn.Column(header, pn.Spacer(height=-40), pn.Row(geomap, elevation), pn.Row(temperature, precipitation)).show()


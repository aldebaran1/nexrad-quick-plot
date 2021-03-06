from pathlib import Path
import xarray
import numpy as np
import imageio
import logging
from typing import Dict, Any, Union, List, Optional
from matplotlib.pyplot import figure, draw
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import cartomap.geogmap as cm

from . import load
from .io import loadkeogram
import cartopy.crs as ccrs

PROJECTION = 'lambert'
FIGSIZE = [12,8]
LATLIM = [25,55]
LONLIM = [-125,-65]
PARALLELS = list(range(20, 70, 10))
MERIDIANS = list(range(-140, -20, 20))
grid_linewidth = 2
grid_color = 'k'
DPI = 100

def overlay2d(img: xarray.DataArray,
              ofn: Path=None,
              mlp: Dict[str, Any]={},
              lattick: Union[float, int, list]=None,
              lontick: Union[float, int, list]=None,
              scalefn: Path=None,
              verbose: bool=False) -> dict:
    """plot NEXRAD reflectivity on map coordinates"""
    if figure is None:
        logging.error('skipping overlay plot')
        return {}

    title = img.filename.stem[6:-3]

    def _savemap(ofn, fg):
        ofn=str(ofn)
        print('\n Saving Nexrad map:', ofn)
        plt.savefig(ofn, dpi=DPI)
        plt.close(fig)
            
    fig = cm.plotCartoMap(latlim=LATLIM,lonlim=LONLIM,figsize=FIGSIZE,
                             title=title,projection=PROJECTION,
                             parallels=PARALLELS,meridians=MERIDIANS,
                             grid_linewidth=grid_linewidth,
                             grid_color=grid_color)

    plt.imshow(img, origin='upper',
                     extent=[img.lon[0], img.lon[-1], img.lat[0], img.lat[-1]],
                     transform=ccrs.PlateCarree())
    
    plt.tight_layout()
    
    if scalefn and scalefn.is_file():
        scale = np.rot90(imageio.imread(scalefn), 2)
        ax = fig.add_axes([0.9, 0.15, 0.055, 0.3])
        ax.imshow(scale)
        ax.axis('off')  # turn off all ticks, etc.
    
    if ofn is not None:
        _savemap(ofn, fig)
    else:
        plt.show()
        
    return mlp


def keogram(keo: xarray.DataArray,
            ofn: Path=None,
            scalefn: Path=None):
    """stack a single lat or lon index"""
    if figure is None:
        logging.error('skipping keogram')
        return
# %%
    fg = figure(figsize=(15, 10))
    ax = fg.gca()

    tlim = mdates.date2num(keo.time[[0, -1]].values)

    ax.imshow(keo.values, origin='upper',
              aspect='auto',  # crucial for time-based imshow()
              extent=[tlim[0], tlim[1], keo.lon[0].item(), keo.lon[-1].item()])

    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    fg.autofmt_xdate()

    ax.set_xlabel('Time [UTC]')
    ax.set_ylabel('Longitude [deg.]')
    ax.set_title(f'NEXRAD Keogram: cut at lat={keo.lat}\n'
                 f'{keo.time.values[0]} to {keo.time.values[-1]}')

    draw()
# %%
    if ofn is not None:
        ofn = Path(ofn).expanduser()
        print('saving keogram to', ofn)
        fg.savefig(ofn, bbox_inches='tight', dpi=DPI)


def genplots(P, scalefn: Path, quiet: bool=False):

    odir = Path(P.odir).expanduser() if P.odir else None
    datadir = Path(P.datadir[0]).expanduser()
    flist = [datadir] if datadir.is_file() else sorted(datadir.glob(P.pat))
    if len(flist) == 0:
        raise FileNotFoundError(f'did not find files in {datadir} with pattern {P.pat}')
    # Keogram
    if isinstance(P.keo, list) and len(P.keo) == 2:
        ofn = nexrad_keogram(flist, P.keo, P.wld, odir, scalefn=scalefn, quiet=P.quiet)
        print('keogram created at', ofn)
    # Map
    else:
        nexrad_loop(flist, P.wld, odir, P.lattick, scalefn=scalefn, quiet=P.quiet)
        if odir:
            print('\nImageMagick can convert the PNGs to animated GIF by a command like:')
            print('\nconvert map2018-0101T09*.png out.gif')


def nexrad_keogram(flist: List[Path], keo: List[str],
                   wld: Path, odir: Path=None, scalefn: Path=None, quiet: bool=False) -> Optional[Path]:

    keoreq = (keo[0], float(keo[1]))

    ofn = odir / f'keo-{keo[0]}{keo[1]}-{flist[0].stem}-{flist[-1].stem}.png' if odir else None
    dkeo = loadkeogram(flist, keoreq, wld)

    if not quiet:
        keogram(dkeo, ofn, scalefn=scalefn)

    return ofn


def nexrad_loop(flist: List[Path],
                wld: Path, odir: Optional[Path],
                lattick: float=None, scalefn: Path=None, quiet: bool=False):
    
    mlp: dict = {}
    for f in flist:
        ofn = odir / (PROJECTION + f.name[6:]) if odir else None
        img = load(f, wld, downsample=8)
        mlp = overlay2d(img, ofn, mlp, lattick=lattick, scalefn=scalefn)

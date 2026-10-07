"""pyGIMLi backend. Nothing outside this module may import pygimli."""
import os
import tempfile
from importlib.metadata import version

import numpy as np

from .types import InversionConfig


def ensure_writable_home() -> None:
    """pyGIMLi writes config/cache files under $HOME on import. Serverless hosts (e.g. Vercel) mount the home
    directory read-only, so fall back to a temporary directory when it is not writable."""
    home = os.environ.get("HOME") or os.path.expanduser("~")
    if home and os.access(home, os.W_OK):
        return
    tmp = tempfile.gettempdir()
    os.environ["HOME"] = tmp
    os.environ.setdefault("XDG_CACHE_HOME", os.path.join(tmp, ".cache"))
    os.environ.setdefault("XDG_CONFIG_HOME", os.path.join(tmp, ".config"))
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(tmp, ".mpl"))


def default_start(spacing, observed, cfg: InversionConfig):
    rho = np.array(cfg.start_rho, float) if cfg.start_rho else np.full(cfg.n_layers, np.median(observed))
    if cfg.start_thickness:
        th = np.array(cfg.start_thickness, float)
    else:
        # log-spaced between ~1/10 of the smallest and ~1/3 of the largest spacing
        th = np.geomspace(spacing.min() / 2, spacing.max() / 6, cfg.n_layers - 1)
    return rho, th


class PygimliBackend:
    name = "pygimli"

    def invert(self, spacing, distances: dict, observed, cfg: InversionConfig, error_scale=None) -> dict:
        ensure_writable_home()
        import pygimli as pg
        from pygimli.physics.ves import VESModelling

        n = cfg.n_layers
        rho0, th0 = default_start(spacing, observed, cfg)
        # arbitrary geometry via the four current-potential distances (inf = remote electrode)
        fop = VESModelling(am=pg.Vector(distances["am"]), an=pg.Vector(distances["an"]),
                           bm=pg.Vector(distances["bm"]), bn=pg.Vector(distances["bn"]), nLayers=n)
        inv = pg.Inversion(fop=fop, verbose=False)
        inv.transData = pg.trans.TransLog()
        start = pg.Vector(list(th0) + list(rho0))
        err = np.full(len(observed), cfg.error_percent / 100.0)
        if error_scale is not None:   # per-datum weighting (error * scale)
            err = err * np.asarray(error_scale, float)
        model = np.array(inv.run(pg.Vector(observed), pg.Vector(err), startModel=start,
                                 lam=cfg.lam, maxIter=cfg.max_iter))
        # default per-region log transforms apply; enforce bounds after the fact so the
        # reported response always belongs to the reported (bounded) model
        model[: n - 1] = np.clip(model[: n - 1], *cfg.thickness_bounds)
        model[n - 1:] = np.clip(model[n - 1:], *cfg.rho_bounds)
        response = np.array(fop.response(pg.Vector(model)))
        return {
            "thickness": model[: n - 1],
            "resistivity": model[n - 1:],
            "response": response,
            "iterations": len(inv.chi2History) if hasattr(inv, "chi2History") else cfg.max_iter,
            "backend": {"name": self.name, "pygimli": version("pygimli")},
        }

    def forward_model(self, distances: dict, n_layers: int):
        """Callable (thickness, resistivity) -> apparent resistivity at the given configurations."""
        ensure_writable_home()
        import pygimli as pg
        from pygimli.physics.ves import VESModelling

        fop = VESModelling(am=pg.Vector(distances["am"]), an=pg.Vector(distances["an"]),
                           bm=pg.Vector(distances["bm"]), bn=pg.Vector(distances["bn"]), nLayers=n_layers)
        return lambda th, rho: np.array(fop.response(pg.Vector(list(th) + list(rho))))

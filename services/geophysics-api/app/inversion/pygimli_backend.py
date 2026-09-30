"""pyGIMLi backend. Nothing outside this module may import pygimli."""
from importlib.metadata import version

import numpy as np

from .types import InversionConfig


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

    def invert(self, spacing, distances: dict, observed, cfg: InversionConfig) -> dict:
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

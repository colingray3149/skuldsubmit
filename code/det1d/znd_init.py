#!/usr/bin/env python3
# Source: bg/b5-of14/znd_init.py (verbatim but for paths).
# Shows: the matched CJ/ZND initial condition (SDToolbox znd on Cantera), written into the OpenFOAM 0/ fields.
"""Construct a right-moving B1 CJ/ZND wave as conservative OpenFOAM cell averages.
--shock-frame subtracts D_CJ from every velocity (stationary shock, fresh inflow fixed at the outlet patch)."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import cantera as ct
import numpy as np
from numpy.polynomial.legendre import leggauss
from sdtoolbox.postshock import CJspeed, PostShock_fr
from sdtoolbox.znd import zndsolve


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    a = argparse.ArgumentParser()
    for name in ('case', 'mechanism', 'mechanism-sha256', 'method'):
        a.add_argument('--' + name, required=True)
    for name in ('n', 'quadrature'):
        a.add_argument('--' + name, type=int, required=True)
    for name in ('length', 'shock-x', 'p0', 't0', 'phi', 't-end', 'max-step', 'rtol', 'atol', 'rh-tol', 'end-thermicity-rel'):
        a.add_argument('--' + name, type=float, required=True)
    a.add_argument('--shock-frame', action='store_true')
    a.add_argument('--composition', help='Cantera mole string; default H2-air at --phi')
    c = a.parse_args()
    case, mech = Path(c.case), Path(c.mechanism).expanduser()
    if sha(mech) != c.mechanism_sha256:
        raise ValueError('Burke source hash mismatch')
    if c.n < 2 or c.quadrature < 2 or not 0 < c.shock_x < c.length:
        raise ValueError('invalid mesh, quadrature or shock location')
    composition = c.composition or f'H2:{2*c.phi:.17g} O2:1 N2:3.76'
    fresh = ct.Solution(str(mech)); fresh.TPX = c.t0, c.p0, composition
    gas = ct.Solution(str(mech))
    d = float(CJspeed(c.p0, c.t0, composition, str(mech)))
    vn = PostShock_fr(d, c.p0, c.t0, composition, str(mech))
    vn_state = (vn.P, vn.density, vn.enthalpy_mass, vn.Y.copy())
    z = zndsolve(vn, fresh, d, t_end=c.t_end, max_step=c.max_step,
                 relTol=c.rtol, absTol=c.atol, Method=c.method, advanced_output=True)
    dist = z['distance']; species = z['species']
    if dist[-1] < c.shock_x or np.any(np.diff(dist) <= 0):
        raise ValueError(f'ZND profile does not cover downstream domain: {dist[-1]} m')
    if z['time'][-1] < c.t_end * (1-1e-8):
        raise ValueError('ZND integration terminated before requested time')
    if abs(z['thermicity'][-1]) > c.end_thermicity_rel * np.max(np.abs(z['thermicity'])):
        raise ValueError('ZND profile endpoint has not relaxed')
    if not all(np.isfinite(x).all() for x in (dist, z['P'], z['rho'], z['T'], z['U'], species)):
        raise ValueError('non-finite ZND state')
    if np.min(z['P']) <= 0 or np.min(z['rho']) <= 0 or np.min(species) < -1e-12 or np.max(np.abs(species.sum(axis=0)-1)) > 1e-8:
        raise ValueError('nonphysical ZND pressure, density or composition')
    if np.min(z['T']) < fresh.min_temp or np.max(z['T']) > fresh.max_temp or not fresh.min_temp <= c.t0 <= fresh.max_temp:
        raise ValueError(f'temperature outside common species thermo range {fresh.min_temp:g}..{fresh.max_temp:g} K')
    # Frozen-shock Rankine-Hugoniot fluxes, evaluated with formation enthalpy.
    pv, rv, hv, yv = vn_state
    us = d * fresh.density / rv
    residuals = {'mass': abs(rv*us-fresh.density*d)/(fresh.density*d),
                 'momentum': abs(pv+rv*us**2-c.p0-fresh.density*d**2)/(c.p0+fresh.density*d**2),
                 'energy': abs(hv+us**2/2-fresh.enthalpy_mass-d**2/2)/abs(fresh.enthalpy_mass+d**2/2),
                 'species': float(np.max(np.abs(yv-fresh.Y)))}
    if max(residuals.values()) > c.rh_tol or not 0 < d-us < d:
        raise ValueError(f'shock jump or lab velocity orientation invalid: {residuals}')
    # At quadrature points interpolate conserved density, momentum, total energy,
    # and species densities. Split the shock cell exactly at the discontinuity.
    w_frame = d if c.shock_frame else 0.0
    rho, u = z['rho'], d-z['U']-w_frame
    energy = np.empty(len(dist))
    for j in range(len(dist)):
        gas.DPY = rho[j], z['P'][j], species[:, j]
        energy[j] = rho[j]*(gas.int_energy_mass + 0.5*u[j]**2)
    qz = np.vstack((rho, rho*u, energy, species*rho))
    qfresh = np.r_[fresh.density, -fresh.density*w_frame, fresh.density*(fresh.int_energy_mass+0.5*w_frame**2), fresh.density*fresh.Y]
    nodes, weights = leggauss(c.quadrature)
    dx = c.length/c.n
    fields = np.empty((3+fresh.n_species, c.n))
    for i in range(c.n):
        left, right = i*dx, (i+1)*dx
        q = np.zeros(len(qfresh))
        if right > c.shock_x:
            q += qfresh*(right-max(left, c.shock_x))
        end = min(right, c.shock_x)
        if end > left:
            # Break at each tabulated ZND point: interpolation is integrated
            # piecewise, while the shock itself is never interpolated.
            cuts = np.r_[left, c.shock_x-dist[(dist > c.shock_x-end) & (dist < c.shock_x-left)][::-1], end]
            for lo, hi in zip(cuts[:-1], cuts[1:]):
                xp = (lo+hi)/2 + (hi-lo)/2*nodes
                zp = c.shock_x-xp
                q += (hi-lo)/2 * np.array([np.dot(weights, np.interp(zp, dist, row)) for row in qz])
        fields[:, i] = q/dx
    p = np.empty(c.n); t = np.empty(c.n); vel = fields[1]/fields[0]
    y = fields[3:]/fields[0]
    if fields[0].min() <= 0 or y.min() < -1e-12 or np.max(np.abs(y.sum(axis=0)-1)) > 1e-8:
        raise ValueError('nonphysical conservative cell average')
    for i in range(c.n):
        if i*dx >= c.shock_x:
            p[i], t[i] = c.p0, c.t0
        else:
            gas.UVY = fields[2,i]/fields[0,i]-vel[i]**2/2, 1/fields[0,i], y[:,i]
            p[i], t[i] = gas.P, gas.T
    if p.min() <= 0 or t.min() < fresh.min_temp or t.max() > fresh.max_temp:
        raise ValueError(f'cell recovery outside physical pressure or thermo limits: p=[{p.min():.17g},{p.max():.17g}], T=[{t.min():.17g},{t.max():.17g}], common=[{fresh.min_temp:.17g},{fresh.max_temp:.17g}]')
    zero = case/'0'; zero.mkdir(exist_ok=True)
    def field(name, values, dimensions, vector=False):
        kind = 'Vector' if vector else 'Scalar'
        fmt = (lambda v: f'({v:.17g} 0 0)') if vector else (lambda v: f'{v:.17g}')
        vals = '\n'.join(fmt(v) for v in values)
        outlet = f'type fixedValue; value uniform {fmt(values[-1])};' if c.shock_frame else 'type zeroGradient;'
        (zero/name).write_text(f'FoamFile{{format ascii;class vol{kind}Field;object {name};}}\ndimensions {dimensions};\ninternalField nonuniform List<{kind.lower()}>\n{c.n}\n(\n{vals}\n);\nboundaryField {{inlet {{type zeroGradient;}} outlet {{{outlet}}} sides {{type empty;}}}}\n')
    field('p', p, '[1 -1 -2 0 0 0 0]')
    field('T', t, '[0 0 0 1 0 0 0]')
    field('U', vel, '[0 1 -1 0 0 0 0]', True)
    for j, name in enumerate(fresh.species_names):
        field(name, y[j], '[0 0 0 0 0 0 0]')
    field('Ydefault', np.zeros(c.n), '[0 0 0 0 0 0 0]')
    profile = case/'znd-profile.csv'
    with profile.open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['distance_m', 'P_Pa', 'rho_kg_m3', 'T_K', 'U_shock_m_s', 'thermicity_s-1']+fresh.species_names)
        w.writerows(zip(dist, z['P'], rho, z['T'], z['U'], z['thermicity'], *species))
    info = {'mechanism_sha256': sha(mech), 'profile_sha256': sha(profile), 'initializer_sha256': sha(__file__),
            'cantera_version': ct.__version__, 'D_CJ_m_s': d, 'shock_x_m': c.shock_x, 'length_m': c.length,
            'cells': c.n, 'fresh_U_m_s': -w_frame, 'frame_velocity_m_s': w_frame, 'vn_U_lab_m_s': d-us, 'shock_RH_relative_residual': residuals,
            'T_source_min_K': float(min(c.t0, np.min(z['T']))), 'T_source_max_K': float(np.max(z['T'])),
            'T_cell_min_K': float(t.min()), 'T_cell_max_K': float(t.max()),
            'thermo_common_range_K': [fresh.min_temp, fresh.max_temp], 'znd_coverage_m': float(dist[-1]),
            'znd_end_thermicity_relative': float(abs(z['thermicity'][-1])/np.max(np.abs(z['thermicity']))),
            'induction_length_m': float(z['ind_len_ZND']), 'arguments': vars(c)}
    (case/'znd-init.json').write_text(json.dumps(info, indent=2)+'\n')


if __name__ == '__main__':
    main()

"""0D constant-pressure H2-air ignition: Cantera reference vs the stored OpenFOAM-14 result (runs in seconds).

Adapted from chem0d_compare.py beside this file (the original read the OpenFOAM case folder on the workstation);
this version reads the OpenFOAM-14 probe history saved in data/chem0d/ and the Burke 2012 mechanism in
code/mechanism/. Ignition time is the time of max dT/dt; t400 is the time to reach T0 + 400 K.

Usage: python code/chem0d/cantera_ignition.py            (both states, prints a table, writes figures' JSON)
"""
import json
import pathlib

import cantera as ct
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
MECH = ROOT / "code/mechanism/Burke2012.yaml"
CASES = [  # (data file, T0 [K], p0 [Pa]): the two B5 chem0d states
    ("of14-vn-1539K-28bar-T.dat", 1538.8, 2.8e6),
    ("of14-T1300K-20bar-T.dat", 1300.0, 2.0e6),
]
COMPOSITION = "H2:2 O2:1 N2:3.76"  # stoichiometric H2-air


def cantera_history(T0, p0, t_end):
    gas = ct.Solution(str(MECH))
    gas.TPX = T0, p0, COMPOSITION
    reactor = ct.IdealGasConstPressureReactor(gas, clone=False)
    net = ct.ReactorNet([reactor])
    net.rtol, net.atol = 1e-10, 1e-14
    t, T = [0.0], [T0]
    while net.time < t_end:
        net.step()
        t.append(net.time)
        T.append(reactor.T)
    return np.array(t), np.array(T)


def tau(t, T):
    return float(t[np.argmax(np.gradient(T, t))])


def t400(t, T, T0):
    return float(np.interp(T0 + 400, T, t)) if T.max() > T0 + 400 else float("nan")


def compare(name, T0, p0):
    a = np.loadtxt(ROOT / "data/chem0d" / name, comments="#")
    tf, Tf = a[:, 0], a[:, 1]
    tc, Tc = cantera_history(T0, p0, tf[-1])
    out = dict(case=name, T0_K=T0, p0_Pa=p0,
               of14_tau_us=tau(tf, Tf) * 1e6, cantera_tau_us=tau(tc, Tc) * 1e6,
               of14_t400_us=t400(tf, Tf, T0) * 1e6, cantera_t400_us=t400(tc, Tc, T0) * 1e6,
               of14_T_end_K=float(Tf[-1]), cantera_T_end_K=float(np.interp(tf[-1], tc, Tc)))
    out["tau_rel_diff_pct"] = 100 * (out["of14_tau_us"] / out["cantera_tau_us"] - 1)
    return out, (tf, Tf), (tc, Tc)


def main():
    rows = []
    for name, T0, p0 in CASES:
        row, _, _ = compare(name, T0, p0)
        rows.append(row)
        print(f"{name:30s} T0 {T0:7.1f} K  p0 {p0/1e5:5.1f} bar  tau OF14 {row['of14_tau_us']:.4f} us  "
              f"Cantera {row['cantera_tau_us']:.4f} us  diff {row['tau_rel_diff_pct']:+.2f} %")
    return rows


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))

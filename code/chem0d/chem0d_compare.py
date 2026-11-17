# Source: bg/b5-of14/chem0d_compare.py (verbatim but for paths).
# Shows: how the OpenFOAM-14 0D ignition delay was checked against Cantera on the same Burke 2012 mechanism.
# The runnable public version is code/chem0d/cantera_ignition.py (reads data/chem0d).
"""0D constant-pressure ignition: OpenFOAM-14 (converted Burke files, runs/chem0d/<case>) vs Cantera (source Burke yaml).
Usage: chem0d_compare.py <case dir> <T0> <p0>. Ignition time = max dT/dt; also time to reach T0+400 K."""
import sys, numpy as np, cantera as ct
case, T0, p0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
mech = 'repos/sdtoolbox-harryzhou-mirror/data/Burke2012.yaml'
a = np.loadtxt(f"{case}/postProcessing/probe/0/T", comments="#"); tf, Tf = a[:, 0], a[:, 1]
g = ct.Solution(mech); g.TPX = T0, p0, 'H2:2 O2:1 N2:3.76'
r = ct.IdealGasConstPressureReactor(g); net = ct.ReactorNet([r]); net.rtol, net.atol = 1e-10, 1e-14
tc, Tc = [0.0], [T0]
while net.time < tf[-1]:
    net.step(); tc.append(net.time); Tc.append(r.T)
tc, Tc = np.array(tc), np.array(Tc)
def tau(t, T): return float(t[np.argmax(np.gradient(T, t))])
def t400(t, T): return float(np.interp(T0 + 400, T, t)) if T.max() > T0 + 400 else float('nan')
out = dict(case=case, T0=T0, p0=p0, of_tau_maxdTdt_us=tau(tf, Tf) * 1e6, ct_tau_maxdTdt_us=tau(tc, Tc) * 1e6,
           of_t400_us=t400(tf, Tf) * 1e6, ct_t400_us=t400(tc, Tc) * 1e6, of_Tend=float(Tf[-1]),
           ct_Tend=float(np.interp(tf[-1], tc, Tc)))
out['tau_rel_diff_pct'] = 100 * (out['of_tau_maxdTdt_us'] / out['ct_tau_maxdTdt_us'] - 1)
print(out)

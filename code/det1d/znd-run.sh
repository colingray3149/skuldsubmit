#!/usr/bin/env bash
# Source: bg/b5-of14/znd-run.sh (verbatim but for paths).
# Shows: how one ZND-initialised tube was built and run (blockMesh, chemkinToFoam, znd_init, decompose, foamRun).
# Explicit launch only: znd-run.sh --launch CELLS [LIMITER] [TAG]
# Run one case at a time; never replace a previous case or change det1d.sh.
set -euo pipefail
B5=$(cd "$(dirname "$0")" && pwd)
if [[ ${1:-} != --launch || $# -lt 2 || $# -gt 4 ]]; then
  echo 'Usage: znd-run.sh --launch CELLS [LIMITER] [TAG] (only after slot grant)' >&2
  exit 2
fi
shift
n=$1; limiter=${2:-vanLeer}; tag=${3:-}
[[ $n =~ ^[0-9]+$ && $n -ge 2 && $limiter =~ ^[A-Za-z][A-Za-z0-9]*$ && $tag =~ ^[A-Za-z0-9_-]*$ ]] || { echo 'Invalid cells, limiter or tag' >&2; exit 2; }
source "${B5_CONF:-$B5/b5.conf}"
source "${ZND_CONF:-$B5/znd.conf}"
ZND_PYTHON="$(nix path-info "${ZND_PYTHON_FLAKE}#python")/bin/python"
export ZND_PYTHON
[[ $DET_RANKS =~ ^[0-9]+$ && $DET_RANKS -ge 1 && $DET_RANKS -le 12 && $DET_RANKS -le $MAX_RANKS ]] || { echo 'Ranks must be 1..12 and <= MAX_RANKS' >&2; exit 2; }
[[ ${DET_NY:-1} == 1 && ${AMR_LEVELS:-0} == 0 ]] || { echo 'ZND runner requires a fixed one-dimensional mesh' >&2; exit 2; }
mkdir -p "$B5/runs/znd"
[[ $DET_MECH == mech/burke2012 ]] || { echo 'ZND runner requires the original Burke mechanism' >&2; exit 2; }
(cd "$B5/mech" && sha256sum -c SHA256SUMS) || { echo 'Burke mechanism checksum failure' >&2; exit 1; }
exec 9>"$B5/runs/znd/.lock"
flock -n 9 || { echo 'Another ZND case is running' >&2; exit 1; }
tmp=$(mktemp "$B5/.znd-runner.XXXXXXXX")
trap 'rm -f "$tmp"' EXIT
# Copy the established case setup, replacing only its output path, end patch,
# and the insertion point immediately after blockMesh and before decomposition.
"$ZND_PYTHON" - "$B5/det1d.sh" "$tmp" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
def replace(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit('det1d.sh changed; cannot safely construct ZND runner: '+old)
    s = s.replace(old, new)
replace('source "$B5/lib.sh"; cd "$B5"', 'source "$B5/lib.sh"; source "${ZND_CONF:-$B5/znd.conf}"; cd "$B5"')
replace("sed -i 's/^defaultSpecie.*/defaultSpecie N2;/' constant/physicalProperties", 'sed -i "s/^defaultSpecie.*/defaultSpecie ${DET_DEFAULT_SPECIE:-N2};/" constant/physicalProperties')
replace('d=runs/det1d/$solver-$lim-n$n${tag:+-$tag}; rm -rf "$d"; mkdir -p "$d"/{0,constant/foam,system}; cd "$d"',
        'd=runs/znd/$solver-$lim-n$n${tag:+-$tag}; mkdir "$d" || { echo "case exists: $d" >&2; exit 1; }; mkdir -p "$d"/{0,constant/foam,system}; cd "$d"')
replace('inlet {type wall; faces ((0 4 7 3));}', 'inlet {type patch; faces ((0 4 7 3));}')
replace('    probes {type probes;', '    auditEnergy {type writeObjects; libs ("libutilityFunctionObjects.so"); objects (e); writeControl writeTime;}\n    temperatureMax {type volFieldValue; libs ("libfieldFunctionObjects.so"); cellZone all; operation max; fields (T); writeFields false; writeControl timeStep; writeInterval 1; log false;}\n    probes {type probes;')
replace('blockMesh < /dev/null > log.blockMesh 2>&1', '''cp "$B5/det1d.sh" "$B5/znd-run.sh" "$B5/znd_init.py" .
cp "${ZND_CONF:-$B5/znd.conf}" znd.conf
cp "${B5_CONF:-$B5/b5.conf}" b5.conf
blockMesh < /dev/null > log.blockMesh 2>&1
"$ZND_PYTHON" "$B5/znd_init.py" --case . --mechanism "$ZND_MECH" --mechanism-sha256 "$ZND_MECH_SHA256" \\
  --n "$n" --length "$DET_LENGTH" --shock-x "$ZND_SHOCK_X" --p0 "$DET_P0" --t0 "$DET_T0" --phi "$DET_PHI" \\
  --t-end "$ZND_T_END" --max-step "$ZND_MAX_STEP" --rtol "$ZND_RTOL" --atol "$ZND_ATOL" --method "$ZND_METHOD" \\
  --quadrature "$ZND_QUADRATURE" --rh-tol "$ZND_RH_TOL" --end-thermicity-rel "$ZND_END_THERMICITY_REL" ${ZND_SHOCK_FRAME:+--shock-frame} ${ZND_COMPOSITION:+--composition "$ZND_COMPOSITION"} > log.znd-init 2>&1''')
Path(sys.argv[2]).write_text(s)
PY
bash "$tmp" "$n" detonationFluid "$limiter" "$tag"

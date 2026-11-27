#!/bin/sh
# run_all_v15.sh (HOST) -- review v1.5: alle suites na elkaar (echte-tijd review + v1.5-paneel + alle v1.4-suites).
# Log per suite in /tmp/v15all/<naam>.log; samenvatting in harness/run_all_v15.log. Draait sequentieel (geen CPU-concurrentie).
cd "$(dirname "$0")"
L=/tmp/v15all; mkdir -p "$L"; : > run_all_v15.log
run() { n=$1; shift; timeout 1500 python3 -u "$@" > "$L/$n.log" 2>&1; echo "$n EXIT $? $(grep -E '[0-9]+ checks, [0-9]+ gefaald|RESULTAAT|PASS.*FAIL' "$L/$n.log" | tail -1)" >> run_all_v15.log; }
for m in live rijdend motoruit nostream oud kapot geenws; do run rit-$m run_v15_rit.py --mode $m; done
for m in live geen kapot geenws; do run liveunit-$m run_v15_live_unit.py --mode $m; done
run inject      run_v15_inject.py
run terminal    run_v15_terminal.py
run bewaker     run_v15_bewaker.py
run sbn         run_v15_sbn.py
run schermen    run_v15_schermen.py
run cumulatief  run_v15_cumulatief.py
run p5          run_p5_eco.py
run p6          run_p6_phone.py
echo ALLDONE >> run_all_v15.log

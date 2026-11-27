#!/bin/sh
# run_all_v14.sh (HOST) -- reviewronde 2: alle v1.4-suites achter elkaar + make_results_all. Log per suite in harness/run_*.log
cd "$(dirname "$0")"
for s in run_inject.py:run_inject checks_p1.py:run_p1 run_p2_dialog3.py:run_p2 run_p3.py:run_p3 run_submenus_p4.py:run_p4b run_cumulatief.py:run_cum run_v14_bewaker.py:run_bew run_v14_sbn.py:run_sbn run_v14_schermen.py:run_sch run_v14_terminal.py:run_term run_p5_eco.py:run_p5 run_p6_phone.py:run_p6; do
  f=${s%%:*}; l=${s##*:}
  timeout 1200 python3 "$f" > "$l.log" 2>&1; echo "$f EXIT $? $(grep -E 'checks,|gefaald|PASS.*FAIL' "$l.log" | tail -1)" >> run_all.log
done
python3 make_results_all.py >> run_all.log 2>&1
echo ALLDONE >> run_all.log

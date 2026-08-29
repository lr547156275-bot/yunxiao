cd /work/simulation/experiment/scheme1_sba/cr_s3_rho040_out
echo "=== sba_events: the admission rows (batch_id, flow_id, grant) ==="
awk -F, 'NR==1 || /COLLECTING->STARTUP_SENDING/ {print NR": "$1","$2","$6","$7","$8}' sba_events.csv | head -6
echo "  ... count and grant sum:"
awk -F, '/COLLECTING->STARTUP_SENDING/{n++; s+=$6} END{printf "  n=%d sum_grant=%.4f G\n", n, s/1e9}' sba_events.csv
echo "  distinct batch_id among them:"
awk -F, '/COLLECTING->STARTUP_SENDING/{print $1}' sba_events.csv | sort -u | tr '\n' ' '; echo
echo "  flow_id 65 present?"
awk -F, '/COLLECTING->STARTUP_SENDING/ && $2==65 {print "  YES grant="$6}' sba_events.csv
echo
echo "=== grant distribution (per flow) ==="
awk -F, '/COLLECTING->STARTUP_SENDING/{printf "%.4f\n", $6/1e6}' sba_events.csv | sort -n | uniq -c
echo
echo "=== eta_feasibility first + last rows ==="
head -2 eta_feasibility.csv
tail -1 eta_feasibility.csv
echo
echo "=== link timeseries: time units ==="
head -3 selected_link_timeseries.csv
tail -1 selected_link_timeseries.csv
echo
echo "=== flow timeseries: time units + flow ids ==="
head -2 selected_flow_timeseries.csv
awk -F, 'NR>1{print $2}' selected_flow_timeseries.csv | sort -u | head -5

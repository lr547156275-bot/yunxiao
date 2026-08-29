cd /work/simulation
echo "=== is m_traceQpDequeue actually invoked anywhere? ==="
grep -rn "m_traceQpDequeue" src/point-to-point/model/*.cc
echo
echo "=== and m_traceEnqueue (QbbEnqueue)? ==="
grep -rn "m_traceEnqueue" src/point-to-point/model/*.cc
echo
echo "=== my install block: is cbap_actuation_csv non-NULL at that point? ==="
echo "  file-open line vs install line:"
grep -n "cbap_actuation_csv = fopen" scratch/third.cc
grep -n "if (cbap_actuation_csv && !cbap_links.empty())" scratch/third.cc
grep -n 'std::cout << "Running Simulation' scratch/third.cc

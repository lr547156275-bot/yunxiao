all : trace_reader trace_probe trace_analyzer

trace_reader : trace_reader.cpp trace-format.h trace_filter.hpp utils.hpp sim-setting.h
	g++ trace_reader.cpp -o trace_reader -O3 -std=gnu++11

trace_probe : trace_probe.cpp trace-format.h sim-setting.h
	g++ trace_probe.cpp -o trace_probe -O3 -std=gnu++11

trace_analyzer : trace_analyzer.cpp trace-format.h sim-setting.h
	g++ trace_analyzer.cpp -o trace_analyzer -O3 -std=gnu++11

fct_analysis: fct_analysis.cpp
	g++ fct_analysis.cpp -o fct_analysis -O3 -std=gnu++11

# Draw the eta ("knob") figures as SVG, from eta_sweep_s4.csv.
#
# Usage:
#   cd <repo>/simulation/experiment/scheme1_sba/eta_sweep
#   awk -f make_eta_charts.awk eta_sweep_s4.csv
#
# awk rather than Python because the machine these were drawn on has no working
# Python interpreter; SVG rather than PNG for the same reason make_charts.py
# chose it -- plain text, no plotting library, vector output fit for a paper.
#
# Emits into charts/:
#   eta1_tradeoff_curve.svg    the headline knob figure: p99 FCT and background
#                              retention against eta on twin axes
#   eta2_paretoA.svg           Pareto frontier: retention (x) vs p99 FCT (y),
#                              with HPCC and DCQCN as fixed reference points
#   eta3_queue_pressure.svg    queue mean / time-above-Qmax / oversub duration,
#                              showing the regime break at eta >= 0.65
#   eta4_paretoC.svg           queue p99 (x) vs p99 FCT (y)
#   eta5_goodput_bgmin.svg     incast goodput vs background minimum throughput
#   eta6_normalised.svg        every metric normalised to its eta=0.20 value, so
#                              the directions of the trade-off sit on one axis
# Each chart also writes the CSV it was drawn from.

function esc(s) { gsub(/&/, "\\&amp;", s); gsub(/</, "\\&lt;", s); gsub(/>/, "\\&gt;", s); return s }

function nice_top(vmax, _step, _mag, _t, _i, _cands) {
    # Round the axis maximum up to a readable step (1/2/2.5/5 x 10^n).
    if (vmax <= 0) return 1
    _mag = 1
    while (_mag * 10 <= vmax / 5) _mag *= 10
    while (_mag > vmax / 5 && _mag > 1e-9) _mag /= 10
    split("1 2 2.5 5 10", _cands, " ")
    for (_i = 1; _i <= 5; _i++) {
        _step = _cands[_i] * _mag
        if (vmax / _step <= 5.0001) break
    }
    _t = _step
    while (_t < vmax - 1e-9) _t += _step
    AXIS_STEP = _step
    return _t
}

function fmt(v, top) {
    if (top >= 1e6) return sprintf("%.2fM", v / 1e6)
    if (top >= 1e4) return sprintf("%.0fk", v / 1000)
    if (top >= 100) return sprintf("%.0f", v)
    if (top >= 10)  return sprintf("%.0f", v)
    if (top >= 1)   return sprintf("%.1f", v)
    return sprintf("%.2f", v)
}

function head(f, title, subt) {
    printf "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" > f
    printf "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"%d\" height=\"%d\" viewBox=\"0 0 %d %d\" font-family=\"Helvetica,Arial,sans-serif\">\n", W, H, W, H > f
    printf "<rect width=\"%d\" height=\"%d\" fill=\"#ffffff\"/>\n", W, H > f
    printf "<text x=\"%d\" y=\"26\" font-size=\"17\" font-weight=\"bold\" fill=\"#222\">%s</text>\n", 40, esc(title) > f
    if (subt != "") printf "<text x=\"%d\" y=\"44\" font-size=\"11.5\" fill=\"#666\">%s</text>\n", 40, esc(subt) > f
}

function frame(f, ytop, ylab, nx, _i, _y, _v) {
    # horizontal gridlines + left axis labels
    for (_i = 0; _i <= 5; _i++) {
        _v = ytop * _i / 5
        _y = PY0 - (_v / ytop) * (PY0 - PY1)
        printf "<line x1=\"%d\" y1=\"%.1f\" x2=\"%d\" y2=\"%.1f\" stroke=\"#e8e8e8\"/>\n", PX0, _y, PX1, _y > f
        printf "<text x=\"%d\" y=\"%.1f\" font-size=\"10.5\" fill=\"#666\" text-anchor=\"end\">%s</text>\n", PX0 - 8, _y + 3.5, fmt(_v, ytop) > f
    }
    printf "<line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"#333\" stroke-width=\"1.3\"/>\n", PX0, PY0, PX1, PY0 > f
    printf "<line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"#333\" stroke-width=\"1.3\"/>\n", PX0, PY0, PX0, PY1 > f
    printf "<text x=\"18\" y=\"%d\" font-size=\"11.5\" fill=\"#444\" text-anchor=\"middle\" transform=\"rotate(-90 18 %d)\">%s</text>\n", (PY0+PY1)/2, (PY0+PY1)/2, esc(ylab) > f
}

function xlabels(f, _i, _x) {
    for (_i = 1; _i <= N; _i++) {
        _x = PX0 + (PX1 - PX0) * (_i - 1) / (N - 1)
        printf "<text x=\"%.1f\" y=\"%d\" font-size=\"11.5\" fill=\"#444\" text-anchor=\"middle\">%s</text>\n", _x, PY0 + 18, eta[_i] > f
    }
    printf "<text x=\"%.1f\" y=\"%d\" font-size=\"12\" fill=\"#333\" text-anchor=\"middle\">eta (CBAP_MIGRATION_RELEASE_RATIO)</text>\n", (PX0+PX1)/2, H - 14 > f
}

function series(f, col, ytop, colour, dash, label, _i, _x, _y, _d) {
    _d = ""
    for (_i = 1; _i <= N; _i++) {
        _x = PX0 + (PX1 - PX0) * (_i - 1) / (N - 1)
        _y = PY0 - (v[_i, col] / ytop) * (PY0 - PY1)
        _d = _d sprintf("%s%.1f,%.1f ", (_i == 1 ? "M" : "L"), _x, _y)
    }
    printf "<path d=\"%s\" fill=\"none\" stroke=\"%s\" stroke-width=\"2.6\" %s stroke-linejoin=\"round\"/>\n", _d, colour, dash > f
    for (_i = 1; _i <= N; _i++) {
        _x = PX0 + (PX1 - PX0) * (_i - 1) / (N - 1)
        _y = PY0 - (v[_i, col] / ytop) * (PY0 - PY1)
        printf "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"4.5\" fill=\"%s\" stroke=\"#fff\" stroke-width=\"1.5\"><title>eta=%s %s: %.4g</title></circle>\n", _x, _y, colour, eta[_i], label, v[_i, col] > f
    }
}

function legend_at(f, x, y, colour, dash, label) {
    printf "<line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"%s\" stroke-width=\"2.6\" %s/>\n", x, y, x + 26, y, colour, dash > f
    printf "<circle cx=\"%d\" cy=\"%d\" r=\"4\" fill=\"%s\" stroke=\"#fff\" stroke-width=\"1.2\"/>\n", x + 13, y, colour > f
    printf "<text x=\"%d\" y=\"%d\" font-size=\"11.5\" fill=\"#333\">%s</text>\n", x + 33, y + 4, esc(label) > f
}

function scatter(f, xs, ys, xtop, ytop, xlab, ylab, title, subt, npts, lbl, kind, _i, _cx, _cy, _c, _d) {
    head(f, title, subt)
    # y gridlines
    for (_i = 0; _i <= 5; _i++) {
        _c = ytop * _i / 5
        _cy = PY0 - (_c / ytop) * (PY0 - PY1)
        printf "<line x1=\"%d\" y1=\"%.1f\" x2=\"%d\" y2=\"%.1f\" stroke=\"#e8e8e8\"/>\n", PX0, _cy, PX1, _cy > f
        printf "<text x=\"%d\" y=\"%.1f\" font-size=\"10.5\" fill=\"#666\" text-anchor=\"end\">%s</text>\n", PX0 - 8, _cy + 3.5, fmt(_c, ytop) > f
    }
    for (_i = 0; _i <= 5; _i++) {
        _c = xtop * _i / 5
        _cx = PX0 + (_c / xtop) * (PX1 - PX0)
        printf "<line x1=\"%.1f\" y1=\"%d\" x2=\"%.1f\" y2=\"%d\" stroke=\"#f0f0f0\"/>\n", _cx, PY0, _cx, PY1 > f
        printf "<text x=\"%.1f\" y=\"%d\" font-size=\"10.5\" fill=\"#666\" text-anchor=\"middle\">%s</text>\n", _cx, PY0 + 18, fmt(_c, xtop) > f
    }
    printf "<line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"#333\" stroke-width=\"1.3\"/>\n", PX0, PY0, PX1, PY0 > f
    printf "<line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"#333\" stroke-width=\"1.3\"/>\n", PX0, PY0, PX0, PY1 > f
    # connect the eta points in eta order so the frontier reads as a curve
    _d = ""
    for (_i = 1; _i <= npts; _i++) {
        if (kind[_i] != "eta") continue
        _cx = PX0 + (xs[_i] / xtop) * (PX1 - PX0)
        _cy = PY0 - (ys[_i] / ytop) * (PY0 - PY1)
        _d = _d sprintf("%s%.1f,%.1f ", (_d == "" ? "M" : "L"), _cx, _cy)
    }
    printf "<path d=\"%s\" fill=\"none\" stroke=\"#C44E52\" stroke-width=\"2.4\" stroke-dasharray=\"1 0\"/>\n", _d > f
    for (_i = 1; _i <= npts; _i++) {
        _cx = PX0 + (xs[_i] / xtop) * (PX1 - PX0)
        _cy = PY0 - (ys[_i] / ytop) * (PY0 - PY1)
        _c = (kind[_i] == "eta") ? "#C44E52" : ((kind[_i] == "hpcc") ? "#55A868" : "#4C72B0")
        if (kind[_i] == "eta")
            printf "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"6\" fill=\"%s\" stroke=\"#fff\" stroke-width=\"1.5\"><title>%s: (%.4g, %.4g)</title></circle>\n", _cx, _cy, _c, lbl[_i], xs[_i], ys[_i] > f
        else
            printf "<rect x=\"%.1f\" y=\"%.1f\" width=\"11\" height=\"11\" fill=\"%s\" stroke=\"#fff\" stroke-width=\"1.5\"><title>%s: (%.4g, %.4g)</title></rect>\n", _cx - 5.5, _cy - 5.5, _c, lbl[_i], xs[_i], ys[_i] > f
        printf "<text x=\"%.1f\" y=\"%.1f\" font-size=\"9.5\" fill=\"#444\">%s</text>\n", _cx + 9, _cy + 3.5, esc(lbl[_i]) > f
    }
    printf "<text x=\"%.1f\" y=\"%d\" font-size=\"12\" fill=\"#333\" text-anchor=\"middle\">%s</text>\n", (PX0+PX1)/2, H - 14, esc(xlab) > f
    printf "<text x=\"18\" y=\"%d\" font-size=\"11.5\" fill=\"#444\" text-anchor=\"middle\" transform=\"rotate(-90 18 %d)\">%s</text>\n", (PY0+PY1)/2, (PY0+PY1)/2, esc(ylab) > f
    printf "</svg>\n" > f
    close(f)
}

BEGIN {
    FS = ","
    W = 880; H = 470
    PX0 = 92; PX1 = 700; PY0 = H - 52; PY1 = 62
    system("mkdir -p charts")
}

NR == 1 { for (i = 1; i <= NF; i++) hdr[$i] = i; next }

{
    kindv = $(hdr["kind"])
    if (kindv == "cbapsba_eta") {
        N++
        eta[N] = $(hdr["eta"])
        v[N, "p99"]     = $(hdr["fct_p99_ms"]) + 0
        v[N, "mean"]    = $(hdr["fct_mean_ms"]) + 0
        v[N, "cct"]     = $(hdr["cct_ms"]) + 0
        v[N, "ret"]     = $(hdr["bg_retention_pct"]) + 0
        v[N, "bgmin"]   = $(hdr["bg_min_gbps"]) + 0
        v[N, "gp"]      = $(hdr["incast_agg_gbps"]) + 0
        v[N, "qmean"]   = $(hdr["queue_mean_bytes"]) + 0
        v[N, "qp99"]    = $(hdr["queue_p99_bytes"]) + 0
        v[N, "oqmax"]   = $(hdr["over_qmax_pct"]) + 0
        v[N, "osdur"]   = $(hdr["oversub_duration_ms"]) + 0
        v[N, "ecn"]     = $(hdr["ecn_marks"]) + 0
    } else if (kindv == "reference_hpcc" || kindv == "reference_dcqcn") {
        nm = (kindv == "reference_hpcc") ? "HPCC" : "DCQCN"
        R[nm, "p99"]   = $(hdr["fct_p99_ms"]) + 0
        R[nm, "cct"]   = $(hdr["cct_ms"]) + 0
        R[nm, "ret"]   = $(hdr["bg_retention_pct"]) + 0
        R[nm, "bgmin"] = $(hdr["bg_min_gbps"]) + 0
        R[nm, "gp"]    = $(hdr["incast_agg_gbps"]) + 0
        R[nm, "qp99"]  = $(hdr["queue_p99_bytes"]) + 0
        R[nm, "qmean"] = $(hdr["queue_mean_bytes"]) + 0
        have[nm] = 1
    }
}

END {
    if (N < 2) { print "need at least 2 eta points, got " N > "/dev/stderr"; exit 1 }

    # ---------------- Figure 1: the knob, twin axes ----------------
    f = "charts/eta1_tradeoff_curve.svg"
    ptop = nice_top(v[1, "p99"] * 1.08)
    head(f, "The eta knob: incast speed traded against background protection",
         "S4 (64-way x 1 MiB, 95% background), seed 2; only CBAP_MIGRATION_RELEASE_RATIO varies")
    frame(f, ptop, "incast p99 FCT (ms)  -  solid")
    # right axis for retention, drawn 0..100
    for (i = 0; i <= 5; i++) {
        rv = 100 * i / 5
        ry = PY0 - (rv / 100) * (PY0 - PY1)
        printf "<text x=\"%d\" y=\"%.1f\" font-size=\"10.5\" fill=\"#55A868\" text-anchor=\"start\">%.0f%%</text>\n", PX1 + 8, ry + 3.5, rv > f
    }
    printf "<line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"#55A868\" stroke-width=\"1.1\"/>\n", PX1, PY0, PX1, PY1 > f
    printf "<text x=\"%d\" y=\"%d\" font-size=\"11.5\" fill=\"#55A868\" text-anchor=\"middle\" transform=\"rotate(90 %d %d)\">background retention (%%)  -  dashed</text>\n", PX1 + 52, (PY0+PY1)/2, PX1 + 52, (PY0+PY1)/2 > f
    series(f, "p99", ptop, "#C44E52", "", "p99 FCT")
    # retention on the 0..100 right axis
    d = ""
    for (i = 1; i <= N; i++) {
        x = PX0 + (PX1 - PX0) * (i - 1) / (N - 1)
        y = PY0 - (v[i, "ret"] / 100) * (PY0 - PY1)
        d = d sprintf("%s%.1f,%.1f ", (i == 1 ? "M" : "L"), x, y)
    }
    printf "<path d=\"%s\" fill=\"none\" stroke=\"#55A868\" stroke-width=\"2.6\" stroke-dasharray=\"7 4\"/>\n", d > f
    for (i = 1; i <= N; i++) {
        x = PX0 + (PX1 - PX0) * (i - 1) / (N - 1)
        y = PY0 - (v[i, "ret"] / 100) * (PY0 - PY1)
        printf "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"4.5\" fill=\"#55A868\" stroke=\"#fff\" stroke-width=\"1.5\"><title>eta=%s retention: %.2f%%</title></circle>\n", x, y, eta[i], v[i, "ret"] > f
    }
    # mark where ECN marking stops
    for (i = 2; i <= N; i++) {
        if (v[i, "ecn"] == 0 && v[i-1, "ecn"] > 0) {
            bx = PX0 + (PX1 - PX0) * (i - 1.5) / (N - 1)
            printf "<line x1=\"%.1f\" y1=\"%d\" x2=\"%.1f\" y2=\"%d\" stroke=\"#999\" stroke-width=\"1.2\" stroke-dasharray=\"3 3\"/>\n", bx, PY0, bx, PY1 > f
            printf "<text x=\"%.1f\" y=\"%d\" font-size=\"10\" fill=\"#777\" text-anchor=\"middle\">ECN silent -&gt;</text>\n", bx + 46, PY1 - 6 > f
            printf "<text x=\"%.1f\" y=\"%d\" font-size=\"10\" fill=\"#777\" text-anchor=\"middle\">&lt;- ECN active</text>\n", bx - 44, PY1 - 6 > f
        }
    }
    xlabels(f)
    legend_at(f, PX0 + 12, PY1 + 4, "#C44E52", "", "incast p99 FCT (left)")
    legend_at(f, PX0 + 12, PY1 + 22, "#55A868", "stroke-dasharray=\"7 4\"", "background retention (right)")
    printf "</svg>\n" > f
    close(f)
    cf = "charts/eta1_tradeoff_curve.csv"
    printf "eta,fct_p99_ms,bg_retention_pct,ecn_marks\n" > cf
    for (i = 1; i <= N; i++) printf "%s,%.6f,%.6f,%d\n", eta[i], v[i,"p99"], v[i,"ret"], v[i,"ecn"] > cf
    close(cf)

    # ---------------- Figure 2: Pareto A ----------------
    np = 0
    for (i = 1; i <= N; i++) { np++; xs[np] = v[i,"ret"]; ys[np] = v[i,"p99"]; lbl[np] = "eta=" eta[i]; kd[np] = "eta" }
    if (have["HPCC"])  { np++; xs[np] = R["HPCC","ret"];  ys[np] = R["HPCC","p99"];  lbl[np] = "HPCC";  kd[np] = "hpcc" }
    if (have["DCQCN"]) { np++; xs[np] = R["DCQCN","ret"]; ys[np] = R["DCQCN","p99"]; lbl[np] = "DCQCN"; kd[np] = "dcqcn" }
    mx = 0; my = 0
    for (i = 1; i <= np; i++) { if (xs[i] > mx) mx = xs[i]; if (ys[i] > my) my = ys[i] }
    scatter("charts/eta2_paretoA.svg", xs, ys, nice_top(mx * 1.05), nice_top(my * 1.08),
            "background throughput retention (%)  -  further right is better",
            "incast p99 FCT (ms)  -  lower is better",
            "Pareto frontier: the eta curve versus fixed baselines",
            "each red point is one eta; squares are algorithms with no equivalent knob", np, lbl, kd)
    cf = "charts/eta2_paretoA.csv"
    printf "label,kind,bg_retention_pct,fct_p99_ms\n" > cf
    for (i = 1; i <= np; i++) printf "%s,%s,%.6f,%.6f\n", lbl[i], kd[i], xs[i], ys[i] > cf
    close(cf)

    # ---------------- Figure 3: queue pressure ----------------
    f = "charts/eta3_queue_pressure.svg"
    qtop = nice_top(v[1, "qmean"] * 1.08)
    head(f, "Queue pressure falls as eta rises (the prediction was the opposite)",
         "mean occupancy on the left axis; time above Qmax and oversubscription duration scaled to the right")
    frame(f, qtop, "queue mean occupancy (bytes)  -  solid")
    series(f, "qmean", qtop, "#4C72B0", "", "queue mean")
    # right axis 0..100 carries the two percentage-like series
    for (i = 0; i <= 5; i++) {
        rv = 100 * i / 5
        ry = PY0 - (rv / 100) * (PY0 - PY1)
        printf "<text x=\"%d\" y=\"%.1f\" font-size=\"10.5\" fill=\"#937860\" text-anchor=\"start\">%.0f</text>\n", PX1 + 8, ry + 3.5, rv > f
    }
    printf "<line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"#937860\" stroke-width=\"1.1\"/>\n", PX1, PY0, PX1, PY1 > f
    printf "<text x=\"%d\" y=\"%d\" font-size=\"11.5\" fill=\"#937860\" text-anchor=\"middle\" transform=\"rotate(90 %d %d)\">time above Qmax (%%) / oversub duration (ms)</text>\n", PX1 + 46, (PY0+PY1)/2, PX1 + 46, (PY0+PY1)/2 > f
    split("oqmax osdur", ser, " ")
    split("#937860 #8172B2", scol, " ")
    split("time above Qmax (%);oversub duration (ms)", snm, ";")
    for (s = 1; s <= 2; s++) {
        d = ""
        for (i = 1; i <= N; i++) {
            x = PX0 + (PX1 - PX0) * (i - 1) / (N - 1)
            y = PY0 - (v[i, ser[s]] / 100) * (PY0 - PY1)
            if (v[i, ser[s]] > 100) y = PY1
            d = d sprintf("%s%.1f,%.1f ", (i == 1 ? "M" : "L"), x, y)
        }
        printf "<path d=\"%s\" fill=\"none\" stroke=\"%s\" stroke-width=\"2.4\" stroke-dasharray=\"%s\"/>\n", d, scol[s], (s == 1 ? "7 4" : "2 3") > f
        for (i = 1; i <= N; i++) {
            x = PX0 + (PX1 - PX0) * (i - 1) / (N - 1)
            y = PY0 - (v[i, ser[s]] / 100) * (PY0 - PY1)
            printf "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"4\" fill=\"%s\" stroke=\"#fff\" stroke-width=\"1.3\"><title>eta=%s %s: %.4g</title></circle>\n", x, y, scol[s], eta[i], snm[s], v[i, ser[s]] > f
            if (v[i, ser[s]] == 0)
                printf "<text x=\"%.1f\" y=\"%.1f\" font-size=\"8.5\" fill=\"#888\" text-anchor=\"middle\">0</text>\n", x, y - 7 > f
        }
    }
    xlabels(f)
    legend_at(f, PX0 + 12, PY1 + 4,  "#4C72B0", "", "queue mean occupancy (left)")
    legend_at(f, PX0 + 12, PY1 + 22, "#937860", "stroke-dasharray=\"7 4\"", "time above Qmax (right)")
    legend_at(f, PX0 + 12, PY1 + 40, "#8172B2", "stroke-dasharray=\"2 3\"", "oversub duration (right)")
    printf "</svg>\n" > f
    close(f)
    cf = "charts/eta3_queue_pressure.csv"
    printf "eta,queue_mean_bytes,queue_p99_bytes,over_qmax_pct,oversub_duration_ms,ecn_marks\n" > cf
    for (i = 1; i <= N; i++) printf "%s,%.3f,%.0f,%.6f,%.4f,%d\n", eta[i], v[i,"qmean"], v[i,"qp99"], v[i,"oqmax"], v[i,"osdur"], v[i,"ecn"] > cf
    close(cf)

    # ---------------- Figure 4: Pareto C ----------------
    np = 0
    for (i = 1; i <= N; i++) { np++; xs[np] = v[i,"qp99"]; ys[np] = v[i,"p99"]; lbl[np] = "eta=" eta[i]; kd[np] = "eta" }
    if (have["HPCC"])  { np++; xs[np] = R["HPCC","qp99"];  ys[np] = R["HPCC","p99"];  lbl[np] = "HPCC";  kd[np] = "hpcc" }
    if (have["DCQCN"]) { np++; xs[np] = R["DCQCN","qp99"]; ys[np] = R["DCQCN","p99"]; lbl[np] = "DCQCN"; kd[np] = "dcqcn" }
    mx = 0; my = 0
    for (i = 1; i <= np; i++) { if (xs[i] > mx) mx = xs[i]; if (ys[i] > my) my = ys[i] }
    scatter("charts/eta4_paretoC.svg", xs, ys, nice_top(mx * 1.05), nice_top(my * 1.08),
            "bottleneck queue p99 (bytes)  -  lower is better",
            "incast p99 FCT (ms)  -  lower is better",
            "Queue depth versus incast latency",
            "eta >= 0.65 collapses the queue by ~24x while still finishing faster", np, lbl, kd)
    cf = "charts/eta4_paretoC.csv"
    printf "label,kind,queue_p99_bytes,fct_p99_ms\n" > cf
    for (i = 1; i <= np; i++) printf "%s,%s,%.0f,%.6f\n", lbl[i], kd[i], xs[i], ys[i] > cf
    close(cf)

    # ---------------- Figure 5: goodput vs background minimum ----------------
    f = "charts/eta5_goodput_bgmin.svg"
    gtop = nice_top(10)
    head(f, "Where the capacity goes: incast goodput against background minimum",
         "both in Gbps on a 10 Gbps link; the two curves are the two sides of the same handover")
    frame(f, gtop, "throughput (Gbps)")
    series(f, "gp",    gtop, "#C44E52", "", "incast goodput")
    series(f, "bgmin", gtop, "#55A868", "stroke-dasharray=\"7 4\"", "background minimum")
    xlabels(f)
    legend_at(f, PX0 + 12, PY1 + 4,  "#C44E52", "", "incast aggregate goodput")
    legend_at(f, PX0 + 12, PY1 + 22, "#55A868", "stroke-dasharray=\"7 4\"", "background minimum throughput")
    printf "</svg>\n" > f
    close(f)
    cf = "charts/eta5_goodput_bgmin.csv"
    printf "eta,incast_agg_gbps,bg_min_gbps\n" > cf
    for (i = 1; i <= N; i++) printf "%s,%.6f,%.6f\n", eta[i], v[i,"gp"], v[i,"bgmin"] > cf
    close(cf)

    # ---------------- Figure 6: everything normalised to eta=0.20 ----------------
    f = "charts/eta6_normalised.svg"
    head(f, "All metrics normalised to their eta=0.20 value",
         "one axis, so the directions of the trade-off are directly comparable; 1.0 = the eta=0.20 baseline")
    ntop = 1.2
    for (i = 1; i <= N; i++) {
        if (v[1,"p99"]   > 0 && v[i,"p99"]/v[1,"p99"]     > ntop) ntop = v[i,"p99"]/v[1,"p99"]
        if (v[1,"gp"]    > 0 && v[i,"gp"]/v[1,"gp"]       > ntop) ntop = v[i,"gp"]/v[1,"gp"]
        if (v[1,"ret"]   > 0 && v[i,"ret"]/v[1,"ret"]     > ntop) ntop = v[i,"ret"]/v[1,"ret"]
        if (v[1,"qmean"] > 0 && v[i,"qmean"]/v[1,"qmean"] > ntop) ntop = v[i,"qmean"]/v[1,"qmean"]
    }
    ntop = nice_top(ntop * 1.05)
    frame(f, ntop, "value relative to eta=0.20")
    printf "<line x1=\"%d\" y1=\"%.1f\" x2=\"%d\" y2=\"%.1f\" stroke=\"#bbb\" stroke-width=\"1\" stroke-dasharray=\"4 3\"/>\n", PX0, PY0 - (1.0/ntop)*(PY0-PY1), PX1, PY0 - (1.0/ntop)*(PY0-PY1) > f
    split("p99 gp ret qmean", nser, " ")
    split("#C44E52 #DD8452 #55A868 #4C72B0", ncol, " ")
    split("incast p99 FCT;incast goodput;background retention;queue mean occupancy", nnm, ";")
    split(";stroke-dasharray=\"2 3\";stroke-dasharray=\"7 4\";stroke-dasharray=\"1 0\"", ndash, ";")
    for (s = 1; s <= 4; s++) {
        base = v[1, nser[s]]
        if (base <= 0) continue
        d = ""
        for (i = 1; i <= N; i++) {
            x = PX0 + (PX1 - PX0) * (i - 1) / (N - 1)
            y = PY0 - ((v[i, nser[s]] / base) / ntop) * (PY0 - PY1)
            d = d sprintf("%s%.1f,%.1f ", (i == 1 ? "M" : "L"), x, y)
        }
        printf "<path d=\"%s\" fill=\"none\" stroke=\"%s\" stroke-width=\"2.5\" %s/>\n", d, ncol[s], ndash[s] > f
        for (i = 1; i <= N; i++) {
            x = PX0 + (PX1 - PX0) * (i - 1) / (N - 1)
            y = PY0 - ((v[i, nser[s]] / base) / ntop) * (PY0 - PY1)
            printf "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"4\" fill=\"%s\" stroke=\"#fff\" stroke-width=\"1.3\"><title>eta=%s %s: %.3fx</title></circle>\n", x, y, ncol[s], eta[i], nnm[s], v[i,nser[s]]/base > f
        }
        legend_at(f, PX0 + 12, PY1 + 4 + (s-1)*18, ncol[s], ndash[s], nnm[s])
    }
    xlabels(f)
    printf "</svg>\n" > f
    close(f)
    cf = "charts/eta6_normalised.csv"
    printf "eta,p99_rel,goodput_rel,retention_rel,queue_mean_rel\n" > cf
    for (i = 1; i <= N; i++) printf "%s,%.6f,%.6f,%.6f,%.6f\n", eta[i], v[i,"p99"]/v[1,"p99"], v[i,"gp"]/v[1,"gp"], v[i,"ret"]/v[1,"ret"], v[i,"qmean"]/v[1,"qmean"] > cf
    close(cf)

    printf "wrote 6 charts + 6 CSVs into charts/ from %d eta points", N
    if (have["HPCC"])  printf ", HPCC reference"
    if (have["DCQCN"]) printf ", DCQCN reference"
    printf "\n"
}

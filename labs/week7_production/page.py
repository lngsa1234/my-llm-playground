"""Week 7 page: a reliability drill. The same requests under a naive and a hardened policy.

Run alone:   streamlit run labs/week7_production/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from labs.shared.ui import (can_run, lab_parameters, metric_row, mini_muse_part, model_settings, page_layout,
                            run_standalone, show_error)
from labs.week7_production import reliability as rel

HOW_IT_WORKS = """
One small production task, **classify a support ticket into JSON**, is sent many times while failures are injected at the rates you choose: rate limits (429), server errors (503), hangs, slow answers and broken JSON.

The same requests run under two policies:

| | Naive | Hardened |
|---|---|---|
| Retries | none | up to N, with exponential backoff and jitter |
| Timeout | none: a hang waits 60 s | per attempt |
| Output check | none: broken JSON is passed on as a success | validated against a schema, retried if bad |
| Fallback model | none | optional, tried once after the retries |

Every attempt is traced. Compare success rate, **silent bad outputs** (the dangerous kind: the caller thinks it worked), p50 and p95 latency, and cost.

- **Simulated** mode is free and instant. Latency is simulated, not waited for, so you can run hundreds of requests.
- **Live** mode makes real API calls, with faults still injected on top. Keep it to a few requests.

Code: `labs/week7_production/reliability.py`.
"""


def render() -> None:
    main, panel = page_layout("Week 7 · Production Reliability")
    if mini_muse_part(main, panel, 7,
                      caption="Inject failures into an LLM feature, then compare a naive and a hardened policy.",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = model_settings(panel)
    with lab_parameters(panel):
        mode = st.radio("Mode", ["Simulated (free)", "Live API calls"], key="week7_mode")
        live = mode == "Live API calls"
        n = (st.slider("Requests", 1, 10, 4, key="week7_live_n") if live
             else st.slider("Requests", 10, 500, 200, 10, key="week7_sim_n"))
        st.markdown("**Failure rates**")
        faults = rel.Faults(
            rate_limit=st.slider("Rate limit (429)", 0, 50, 10, key="week7_f_429", format="%d%%") / 100,
            server_error=st.slider("Server error (503)", 0, 50, 5, key="week7_f_503", format="%d%%") / 100,
            hang=st.slider("Hang (no answer)", 0, 30, 5, key="week7_f_hang", format="%d%%") / 100,
            slow=0.0 if live else st.slider("Slow answer", 0, 50, 10, key="week7_f_slow", format="%d%%") / 100,
            malformed=st.slider("Broken JSON", 0, 50, 10, key="week7_f_bad", format="%d%%") / 100,
        )
        st.markdown("**Hardened policy**")
        policy = rel.hardened(
            max_retries=st.slider("Retries", 0, 5, 3, key="week7_retries"),
            backoff_s=st.slider("Backoff base (s)", 0.0, 2.0, 0.5, 0.1, key="week7_backoff"),
            timeout_s=float(st.slider("Timeout per attempt (s)", 1, 30, 8, key="week7_timeout")),
            validate=st.checkbox("Validate the JSON", True, key="week7_validate"),
            fallback_model=st.text_input("Fallback model", "", key="week7_fallback",
                                         help="Tried once after the retries. Leave empty for none.").strip(),
        )
        seed = int(st.number_input("Random seed", 0, 9999, 7, key="week7_seed",
                                   help="Same seed, same faults: change a policy knob and compare fairly."))

    with main:
        cost_note = "real API calls, billed" if live else "simulated, free and instant"
        st.caption(f"{n} requests per policy · {cost_note} · default model `{settings.model}`")
        if st.button("Run naive vs hardened", type="primary", key="week7_run") and (not live or can_run(settings)):
            backend = rel.LiveBackend(settings) if live else rel.SimulatedBackend()
            bar = st.progress(0.0, text="Running…")
            try:
                runs = {}
                for i, pol in enumerate([rel.NAIVE, policy]):
                    runs[pol.name] = rel.run_batch(
                        backend, n, pol, faults, settings, seed,
                        lambda done, total, i=i: bar.progress((i * total + done) / (2 * total),
                                                              text=f"{['Naive', 'Hardened'][i]}: {done}/{total}"))
                st.session_state.week7_result = {"runs": runs, "live": live}
            except Exception as exc:  # noqa: BLE001
                show_error("Reliability drill", exc)
            bar.empty()

        result = st.session_state.get("week7_result")
        if not result:
            st.info("Set failure rates on the right, then run both policies on the same requests.")
            return
        runs = result["runs"]
        columns = st.columns(2, gap="large")
        for column, (name, results) in zip(columns, runs.items()):
            s = rel.summarize(results)
            with column:
                st.subheader(name)
                metric_row({"Succeeded": f"{s['ok']:.0%}", "Silent bad": f"{s['silent_bad']:.0%}", "Failed": f"{s['failed']:.0%}"})
                metric_row({"p50": f"{s['p50']:.1f}s", "p95": f"{s['p95']:.1f}s", "Cost": f"${s['cost']:.4f}"})
                st.caption(f"{s['attempts']} attempts for {s['requests']} requests"
                           + (f" · {s['fallbacks']} rescued by the fallback model" if s["fallbacks"] else ""))
        naive, hard = (rel.summarize(r) for r in runs.values())
        st.markdown(
            f"**Reading it:** hardening moved success from **{naive['ok']:.0%} to {hard['ok']:.0%}**, "
            f"cut p95 latency from **{naive['p95']:.1f}s to {hard['p95']:.1f}s**, and caught "
            f"**{naive['silent_bad']:.0%}** of answers that the naive policy passed on broken. "
            f"It cost {'more' if hard['cost'] > naive['cost'] else 'no more'}: "
            f"${naive['cost']:.4f} → ${hard['cost']:.4f}, because retries are paid attempts.")

        st.divider()
        name = st.radio("Requests under", list(runs), horizontal=True, key="week7_view")
        rows = rel.request_rows(runs[name])
        st.dataframe(rows, width="stretch", hide_index=True)
        pick = st.selectbox("Trace one request", [r["Request"] for r in rows], key="week7_pick",
                            format_func=lambda i: f"#{i} · {rows[i - 1]['Status']} · {rows[i - 1]['Path']}")
        st.dataframe(rel.attempt_rows(runs[name][pick - 1]), width="stretch", hide_index=True)


if __name__ == "__main__":
    run_standalone(render, "Week 7 · Production Reliability")

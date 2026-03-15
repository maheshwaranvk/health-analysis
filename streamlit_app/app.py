"""
Streamlit frontend for the Health Data GenAI Analyzer.

Three tabs:
  1. Ask Questions — natural-language analysis
  2. Patient Lookup — single-patient profile
  3. Dataset Summary — overview stats and charts
"""

import streamlit as st
import requests
import plotly.graph_objects as go

# ── Configuration ────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Health Data GenAI Analyzer",
    page_icon="🏥",
    layout="wide",
)

st.title("Health Data GenAI Analyzer")
st.caption(
    "Analytics-first GenAI solution for health data analysis. "
    "Ask natural-language questions, look up patients, or view dataset summaries."
)


# ── Helper: call API ─────────────────────────────────────────────────
def _api_get(path: str):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"API error: {e}")
        return None


def _api_post(path: str, body: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"API error: {e}")
        return None


# ── Helper: render chart from raw chart-ready data ───────────────────
def _render_chart(chart_data: dict):
    """Build a Plotly chart from the raw chart-ready payload."""
    chart_type = chart_data.get("chart_type", "bar")
    categories = chart_data.get("categories", [])
    series = chart_data.get("series", {})
    x_label = chart_data.get("x_label", "")
    y_label = chart_data.get("y_label", "")

    fig = go.Figure()
    for name, values in series.items():
        if chart_type == "bar":
            fig.add_trace(go.Bar(x=categories, y=values, name=name))
        else:
            fig.add_trace(go.Scatter(x=categories, y=values, mode="lines+markers", name=name))

    fig.update_layout(
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Tabs ─────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Ask Questions", "Patient Lookup", "Dataset Summary"])


# ── Tab 1: Ask Questions ─────────────────────────────────────────────
with tab1:
    question = st.text_area(
        "Enter your question about the health data:",
        placeholder="e.g. Compare smokers vs non-smokers in terms of BMI and activity",
        height=100,
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        patient_input = st.number_input(
            "Patient ID (optional)", min_value=0, value=0, step=1
        )
    with col_b:
        include_chart = st.checkbox("Include chart", value=True)

    if st.button("Analyze", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Analyzing …"):
                body = {
                    "question": question,
                    "patient_id": patient_input if patient_input > 0 else None,
                    "include_chart": include_chart,
                }
                resp = _api_post("/api/v1/analyze", body)

            if resp:
                st.subheader("Insights")
                st.write(resp.get("insights", ""))

                recs = resp.get("recommendations", [])
                if recs:
                    st.subheader("Recommendations")
                    for r in recs:
                        st.markdown(f"- {r}")

                st.info(resp.get("disclaimer", ""))

                # Chart
                chart = resp.get("chart_data")
                if chart:
                    _render_chart(chart)

                # Safety flags
                flags = resp.get("safety_flags", [])
                if flags:
                    st.warning(f"Safety flags: {', '.join(flags)}")

                # Debug expander
                with st.expander("Debug: full JSON response"):
                    st.json(resp)


# ── Tab 2: Patient Lookup ────────────────────────────────────────────
with tab2:
    pid = st.number_input(
        "Enter Patient ID:", min_value=1, value=1, step=1, key="patient_lookup"
    )

    if st.button("Look Up Patient"):
        with st.spinner("Fetching …"):
            resp = _api_get(f"/api/v1/patients/{pid}")

        if resp:
            st.subheader(f"Patient {pid}")
            st.write(resp.get("summary", ""))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Profile**")
                profile = resp.get("profile", {})
                st.json(profile)
            with col2:
                st.markdown("**Activity Features**")
                activity = resp.get("activity_features", {})
                st.json(activity)


# ── Tab 3: Dataset Summary ───────────────────────────────────────────
with tab3:
    if st.button("Load Dataset Summary"):
        with st.spinner("Loading …"):
            resp = _api_get("/api/v1/dataset/summary")

        if resp:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Patients", resp.get("num_patients", 0))
            with col2:
                st.metric("Activity Rows", resp.get("num_activity_rows", 0))

            st.subheader("Missing Values — Dataset 1")
            mv1 = resp.get("missing_values_dataset_1", {})
            if mv1:
                import pandas as pd
                st.dataframe(
                    pd.DataFrame(
                        {"Column": list(mv1.keys()), "Missing": list(mv1.values())}
                    ),
                    use_container_width=True,
                )

            st.subheader("Missing Values — Dataset 2")
            mv2 = resp.get("missing_values_dataset_2", {})
            if mv2:
                import pandas as pd
                st.dataframe(
                    pd.DataFrame(
                        {"Column": list(mv2.keys()), "Missing": list(mv2.values())}
                    ),
                    use_container_width=True,
                )

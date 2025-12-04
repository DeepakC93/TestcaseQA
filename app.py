import json
import streamlit as st

st.title("Event Comparison Tool (Android vs iOS)")

# ----------- INPUT SECTION ---------------------------------
st.subheader("Paste Android Event JSON")
android_raw = st.text_area("Android JSON", height=200)

st.subheader("Paste iOS Event JSON")
ios_raw = st.text_area("iOS JSON", height=200)

if st.button("Compare Events"):
    try:
        android = json.loads(android_raw)
        ios = json.loads(ios_raw)
    except Exception as e:
        st.error("Invalid JSON input")
        st.stop()

    # -------------------------------------------------------
    # Collect all keys from both platforms
    all_keys = sorted(set(list(android.keys()) + list(ios.keys())))

    # -------------------------------------------------------
    # Prepare table header
    rows = []
    header = ["Field", "Android Value", "iOS Value", "Match?"]

    for key in all_keys:
        a_val = android.get(key, "")
        i_val = ios.get(key, "")

        # Check match
        if key in android and key in ios:
            match = "✔" if str(a_val) == str(i_val) else "✘"
        else:
            match = "✘"

        rows.append([key, str(a_val), str(i_val), match])

    # -------------------------------------------------------
    # Render table manually (no tabulate needed)
    st.subheader("Comparison Table")

    # Build table in Markdown format
    table_md = "| Field | Android Value | iOS Value | Match |\n"
    table_md += "|-------|---------------|-----------|--------|\n"

    for r in rows:
        table_md += f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |\n"

    st.markdown(table_md)

    # Summary
    total = len(rows)
    matches = sum(1 for r in rows if r[3] == "✔")

    st.success(f"Matched: {matches}/{total} fields")


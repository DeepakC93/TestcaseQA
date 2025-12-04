import streamlit as st
import json

st.title("Event Comparison Tool (Android vs iOS)")

st.write("Paste Android & iOS event JSON below:")

android_json = st.text_area("Android JSON")
ios_json = st.text_area("iOS JSON")

# ---------- Utility to safely load JSON ----------
def load_json(text):
    try:
        return json.loads(text)
    except:
        return {}

# ---------- Comparison Logic ----------
def check_event(event_name, android_dict, ios_dict, keys):
    android_match = all(k in android_dict for k in keys)
    ios_match = all(k in ios_dict for k in keys)

    return {
        "Event": event_name,
        "Android": "✔" if android_match else "✖",
        "iOS": "✔" if ios_match else "✖",
    }


if st.button("Compare Events"):

    # Load JSON safely
    android_data = load_json(android_json)
    ios_data = load_json(ios_json)

    # Event definitions
    comparisons = [
        check_event(
            "Part Started",
            android_data,
            ios_data,
            ["part_id", "part_type"]
        ),
        check_event(
            "Part Ended",
            android_data,
            ios_data,
            ["part_status"]
        ),
        check_event(
            "Live Waiting Status",
            android_data,
            ios_data,
            ["live_status"]
        ),
        check_event(
            "Video Play Event",
            android_data,
            ios_data,
            ["video_type", "video_id"]
        ),
        check_event(
            "Video Playback Duration",
            android_data,
            ios_data,
            ["playback_duration"]
        ),
    ]

    # Display section header
    st.subheader("✅ Part-Level Events (Covered)")

    # Build final table with Notes
    table_rows = []
    for row in comparisons:
        notes = ""
        if row["Event"] == "Part Started":
            notes = "part_type: live / test / general"
        elif row["Event"] == "Part Ended":
            notes = "part_status: ended"
        elif row["Event"] == "Live Waiting Status":
            notes = "live_status: waiting"
        elif row["Event"] == "Video Play Event":
            notes = "video_type, video_id"
        elif row["Event"] == "Video Playback Duration":
            notes = "playback_duration event sent"

        table_rows.append([
            row["Event"],
            row["Android"],
            row["iOS"],
            notes
        ])

    # Render table in Streamlit
    st.table(
        {
            "Event": [r[0] for r in table_rows],
            "Android": [r[1] for r in table_rows],
            "iOS": [r[2] for r in table_rows],
            "Notes": [r[3] for r in table_rows],
        }
    )

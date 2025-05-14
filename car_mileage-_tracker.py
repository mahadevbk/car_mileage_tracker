import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

# Sheet ID from Google Sheet URL
SHEET_ID = "1LmLMnyABF-D-liQ7IElLsip561LyOUzqfNpYOI1VOoY"
sheet = client.open_by_key(SHEET_ID).sheet1

# Column headers
HEADERS = [
    "Timestamp", "User", "Odometer Start", "Odometer End",
    "Distance (km)", "Liters", "Amount Paid (₹)",
    "Fuel Efficiency (km/l)", "Cost per KM (₹)", "Fuel Price (₹/l)"
]

# Insert headers if sheet is empty or incorrect
existing_values = sheet.get_all_values()
if not existing_values or existing_values[0] != HEADERS:
    sheet.clear()
    sheet.append_row(HEADERS)

# === Utility Functions ===
def load_data():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    df["Row Number"] = df.index + 2  # account for header row
    return df

def add_entry(user, odo_start, odo_end, rupees, fuel_price):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    distance = odo_end - odo_start
    liters = rupees / fuel_price if fuel_price else 0
    efficiency = distance / liters if liters else 0
    cost_km = rupees / distance if distance else 0

    row = [
        timestamp, user, round(odo_start, 1), round(odo_end, 1),
        round(distance, 1), round(liters, 2), round(rupees, 2),
        round(efficiency, 2), round(cost_km, 2), round(fuel_price, 2)
    ]
    sheet.append_row(row)

# === Streamlit UI ===
st.set_page_config(page_title="Car Mileage Tracker", layout="wide")
st.title("🚗 Car Mileage Tracker")

# Sidebar: User Setup
st.sidebar.header("User Setup")
user = st.sidebar.text_input("Your name or email", value="Prof. S. Rao").strip()
start_odo = st.sidebar.number_input("Starting odometer (km)", min_value=0.0, step=1.0)

if "start_odo" not in st.session_state:
    st.session_state.start_odo = start_odo
if "last_odo" not in st.session_state:
    st.session_state.last_odo = start_odo

# === Add Entry Form ===
st.subheader("➕ Add Fuel Entry")
with st.form("entry_form"):
    odo_end = st.number_input("Current odometer (km)", min_value=st.session_state.last_odo + 0.1)
    rupees = st.number_input("Amount paid (₹)", min_value=0.0, step=1.0)
    fuel_price = st.number_input("Fuel price (₹/litre)", min_value=1.0, value=100.0)
    submitted = st.form_submit_button("Add Entry")

    if submitted:
        add_entry(user, st.session_state.last_odo, odo_end, rupees, fuel_price)
        st.success("✅ Entry added successfully!")
        st.session_state.last_odo = odo_end
        st.rerun()

# === Manage Entries ===
st.subheader("📊 Manage Entries")
df = load_data()

if not df.empty:
    users = df["User"].unique().tolist()
    selected_user = st.selectbox("Filter by user", ["All"] + users)
    filtered_df = df if selected_user == "All" else df[df["User"] == selected_user]

    if not filtered_df.empty:
        row_labels = [f"{i+1}: {r['Timestamp']} - {r['User']}" for i, r in filtered_df.iterrows()]
        selection = st.selectbox("Select an entry to edit or delete", ["None"] + row_labels)

        if selection != "None":
            selected_index = int(selection.split(":")[0]) - 1
            selected_row = filtered_df.iloc[selected_index]
            sheet_row_number = int(selected_row["Row Number"])

            st.markdown("### ✏️ Edit Entry")
            with st.form("edit_entry_form"):
                new_user = st.text_input("User", value=selected_row["User"])
                odo_start = st.number_input("Odometer Start", value=selected_row["Odometer Start"])
                odo_end = st.number_input("Odometer End", value=selected_row["Odometer End"])
                amount = st.number_input("Amount Paid (₹)", value=selected_row["Amount Paid (₹)"])
                price = st.number_input("Fuel Price (₹/l)", value=selected_row["Fuel Price (₹/l)"])
                update = st.form_submit_button("Update Entry")

            if update:
                distance = odo_end - odo_start
                liters = amount / price if price else 0
                efficiency = distance / liters if liters else 0
                cost_km = amount / distance if distance else 0

                updated_data = [
                    selected_row["Timestamp"], new_user, round(odo_start, 1), round(odo_end, 1),
                    round(distance, 1), round(liters, 2), round(amount, 2),
                    round(efficiency, 2), round(cost_km, 2), round(price, 2)
                ]
                sheet.update(f"A{sheet_row_number}:K{sheet_row_number}", [updated_data])
                st.success("✅ Entry updated.")
                st.rerun()

            if st.button("🗑️ Delete this entry"):
                sheet.delete_rows(int(sheet_row_number))  # ✅ safe integer conversion
                st.warning("❌ Entry deleted.")
                st.rerun()

    st.subheader("📋 Full Data Table")
    st.dataframe(filtered_df.drop(columns=["Row Number"]), use_container_width=True)

    st.subheader("⛽ Fuel Efficiency Over Time")
    st.line_chart(filtered_df.set_index("Timestamp")["Fuel Efficiency (km/l)"])

    st.subheader("💰 Cost per KM Over Time")
    st.line_chart(filtered_df.set_index("Timestamp")["Cost per KM (₹)"])
else:
    st.info("No data yet. Add a fuel entry to begin.")

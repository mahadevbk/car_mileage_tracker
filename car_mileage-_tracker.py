import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets setup via secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

# Sheet name
SHEET_NAME = "CarMileageData"
sheet = client.open(SHEET_NAME).sheet1

# Required headers
HEADERS = [
    "Timestamp", "User", "Odometer Start", "Odometer End",
    "Distance (km)", "Liters", "Amount Paid (₹)",
    "Fuel Efficiency (km/l)", "Cost per KM (₹)", "Fuel Price (₹/l)"
]

# Create headers if the sheet is empty
if not sheet.get_all_values():
    sheet.append_row(HEADERS)

# Load sheet data
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Add entry to sheet
def add_entry(user, odo_start, odo_end, rupees, fuel_price):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    distance = odo_end - odo_start
    liters = rupees / fuel_price if fuel_price > 0 else 0
    efficiency = distance / liters if liters > 0 else 0
    cost_per_km = rupees / distance if distance > 0 else 0

    row = [
        timestamp, user, round(odo_start, 1), round(odo_end, 1),
        round(distance, 1), round(liters, 2), round(rupees, 2),
        round(efficiency, 2), round(cost_per_km, 2), round(fuel_price, 2)
    ]
    sheet.append_row(row)

# App UI
st.title("🚗 Car Mileage Tracker")

# User input
st.sidebar.header("User Setup")
user = st.sidebar.text_input("Your name or email", value="anonymous").strip()
start_odo = st.sidebar.number_input("Starting odometer (km)", min_value=0.0, step=1.0)

# Save state
if "start_odo" not in st.session_state:
    st.session_state.start_odo = start_odo
if "last_odo" not in st.session_state:
    st.session_state.last_odo = start_odo

# New entry form
st.subheader("➕ Add Fuel Entry")
with st.form("entry_form"):
    current_odo = st.number_input("Current odometer (km)", min_value=st.session_state.last_odo + 0.1)
    rupees = st.number_input("Amount paid (₹)", min_value=0.0, step=1.0)
    fuel_price = st.number_input("Fuel price (₹/litre)", min_value=1.0, value=100.0)
    submitted = st.form_submit_button("Add Entry")

    if submitted:
        add_entry(user, st.session_state.last_odo, current_odo, rupees, fuel_price)
        st.success("✅ Entry added successfully!")
        st.session_state.last_odo = current_odo

# Load data
df = load_data()

# Filter by user
st.subheader("📊 History")
if not df.empty:
    users = df["User"].unique().tolist()
    selected_user = st.selectbox("Filter by user", options=["All"] + users)
    if selected_user != "All":
        df = df[df["User"] == selected_user]

    st.dataframe(df, use_container_width=True)

    st.subheader("⛽ Fuel Efficiency")
    st.line_chart(df.set_index("Timestamp")["Fuel Efficiency (km/l)"])

    st.subheader("💰 Cost per KM")
    st.line_chart(df.set_index("Timestamp")["Cost per KM (₹)"])
else:
    st.info("No data yet. Add a fuel entry to begin.")

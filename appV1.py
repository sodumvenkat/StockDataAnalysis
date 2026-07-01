import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta

# =====================================================
# MongoDB Connection
# =====================================================

client = MongoClient("mongodb://localhost:27017/")
db = client["market_data"]

COLLECTIONS = [
    "rpciOne",
    "rpciTwo",
    "rpciThree",
    "pocketPivotFour",
    "superTrendBullish",
    "superTrendBearish"
]

# =====================================================
# Streamlit Config
# =====================================================

st.set_page_config(
    page_title="Stock Scanner Dashboard",
    layout="wide"
)

st.title("📈 Stock Scanner Dashboard")

# =====================================================
# Sidebar Filters
# =====================================================

st.sidebar.header("🔍 Search Filters")

selected_collection = st.sidebar.selectbox(
    "Scanner",
    ["All"] + COLLECTIONS
)

# =====================================================
# Date Filter
# =====================================================

use_date_filter = st.sidebar.checkbox(
    "Filter By Date",
    value=False
)

selected_date = None

if use_date_filter:
    selected_date = st.sidebar.date_input(
        "Select Date"
    )

    st.sidebar.info(
        f"📅 Selected Date: {selected_date.strftime('%d-%m-%Y')}"
    )

# =====================================================
# Ticker Filter
# =====================================================

ticker = st.sidebar.text_input(
    "Ticker"
)

# =====================================================
# Stock Name Filter
# =====================================================

stock_name = st.sidebar.text_input(
    "Stock Name"
)

# =====================================================
# Advanced Volume Filter
# =====================================================

use_volume_filter = st.sidebar.checkbox(
    "Filter By Volume",
    value=False
)

volume_operator = None
volume_value = None
volume_min = None
volume_max = None

if use_volume_filter:

    volume_operator = st.sidebar.selectbox(
        "Volume Condition",
        [
            "Between",
            "Greater Than",
            "Less Than",
            "Equal To"
        ]
    )

    if volume_operator == "Between":

        volume_min = st.sidebar.number_input(
            "Min Volume",
            min_value=0,
            value=0,
            step=1000
        )

        volume_max = st.sidebar.number_input(
            "Max Volume",
            min_value=0,
            value=1000000000,
            step=1000
        )

    else:

        volume_value = st.sidebar.number_input(
            "Volume",
            min_value=0,
            value=0,
            step=1000
        )

# =====================================================
# Sorting
# =====================================================

sort_by = st.sidebar.selectbox(
    "Sort By",
    [
        "price",
        "symbol",
        "stock_name",
        "volume",
        "date"
    ]
)

sort_order = st.sidebar.radio(
    "Sort Order",
    [
        "Ascending",
        "Descending"
    ]
)

# =====================================================
# Debug Query
# =====================================================

show_query = st.sidebar.checkbox(
    "Show Mongo Query",
    value=False
)

# =====================================================
# Search Button
# =====================================================

search_clicked = st.sidebar.button(
    "🔍 Search"
)

# =====================================================
# Search Function
# =====================================================

def search_data():

    results = {}

    collections = (
        COLLECTIONS
        if selected_collection == "All"
        else [selected_collection]
    )

    for collection_name in collections:

        collection = db[collection_name]

        query = {}

        # ----------------------------
        # Date Filter
        # ----------------------------

        if use_date_filter and selected_date:

            start_date = datetime.combine(
                selected_date,
                datetime.min.time()
            )

            end_date = start_date + timedelta(days=1)

            query["date"] = {
                "$gte": start_date,
                "$lt": end_date
            }

        # ----------------------------
        # Ticker Filter
        # ----------------------------

        if ticker.strip():
            query["symbol"] = {
                "$regex": ticker,
                "$options": "i"
            }

        # ----------------------------
        # Stock Name Filter
        # ----------------------------

        if stock_name.strip():
            query["stock_name"] = {
                "$regex": stock_name,
                "$options": "i"
            }

        # ----------------------------
        # Advanced Volume Filter
        # ----------------------------

        if use_volume_filter:

            if volume_operator == "Between":

                query["volume"] = {
                    "$gte": volume_min,
                    "$lte": volume_max
                }

            elif volume_operator == "Greater Than":

                query["volume"] = {
                    "$gt": volume_value
                }

            elif volume_operator == "Less Than":

                query["volume"] = {
                    "$lt": volume_value
                }

            elif volume_operator == "Equal To":

                query["volume"] = volume_value

        # ----------------------------
        # Debug Query
        # ----------------------------

        if show_query:
            st.write(f"Query for {collection_name}")
            st.json(query)

        records = list(collection.find(query))

        if records:

            df = pd.DataFrame(records)

            # Remove Mongo _id

            if "_id" in df.columns:
                df.drop(
                    "_id",
                    axis=1,
                    inplace=True
                )

            # Format Date

            if "date" in df.columns:
                df["date"] = pd.to_datetime(
                    df["date"]
                ).dt.strftime("%d-%m-%Y")

            # Sorting

            ascending = (
                sort_order == "Ascending"
            )

            if sort_by in df.columns:
                df.sort_values(
                    by=sort_by,
                    ascending=ascending,
                    inplace=True
                )

            results[collection_name] = df

    return results

# =====================================================
# Search Execution
# =====================================================

if search_clicked:

    results = search_data()

    if results:

        total_records = sum(
            len(df)
            for df in results.values()
        )

        st.success(
            f"Found {total_records} stocks"
        )

        # =================================================
        # Summary
        # =================================================

        summary = []

        for collection_name, df in results.items():

            summary.append({
                "Scanner": collection_name,
                "Stocks Found": len(df)
            })

        stats_df = pd.DataFrame(summary)

        st.subheader("📊 Scanner Summary")

        st.dataframe(
            stats_df,
            hide_index=True,
            width="stretch"
        )

        # =================================================
        # Results
        # =================================================

        st.subheader("📈 Results")

        all_results = []

        for collection_name, df in results.items():

            all_results.append(df)

            with st.expander(
                f"{collection_name} ({len(df)} stocks)",
                expanded=True
            ):

                st.dataframe(
                    df,
                    hide_index=True,
                    width="stretch"
                )

                csv = df.to_csv(index=False)

                st.download_button(
                    label=f"⬇ Download {collection_name}",
                    data=csv,
                    file_name=f"{collection_name}.csv",
                    mime="text/csv"
                )

        # Download all results

        merged_df = pd.concat(
            all_results,
            ignore_index=True
        )

        merged_csv = merged_df.to_csv(
            index=False
        )

        st.download_button(
            label="⬇ Download All Results",
            data=merged_csv,
            file_name="all_results.csv",
            mime="text/csv"
        )

    else:
        st.warning("No records found.")

# =====================================================
# Stock History
# =====================================================

st.divider()

st.subheader("📜 Stock History")

history_ticker = st.text_input(
    "Enter Ticker For History"
)

if st.button("Show History"):

    if history_ticker.strip():

        history_records = []

        for collection_name in COLLECTIONS:

            collection = db[collection_name]

            docs = collection.find(
                {
                    "symbol": {
                        "$regex": history_ticker,
                        "$options": "i"
                    }
                }
            )

            for doc in docs:
                doc["Scanner"] = collection_name
                history_records.append(doc)

        if history_records:

            history_df = pd.DataFrame(
                history_records
            )

            if "_id" in history_df.columns:
                history_df.drop(
                    "_id",
                    axis=1,
                    inplace=True
                )

            if "date" in history_df.columns:
                history_df["date"] = pd.to_datetime(
                    history_df["date"]
                ).dt.strftime("%d-%m-%Y")

            st.success(
                f"Found {len(history_df)} historical records"
            )

            st.dataframe(
                history_df,
                hide_index=True,
                width="stretch"
            )

        else:
            st.warning("No history found.")
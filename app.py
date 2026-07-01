import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta

# =====================================================
# MongoDB Connection
# =====================================================

client = MongoClient("mongodb://localhost:27017/")
db = client["market_data"]

watchlist_collection = db["watchlist"]

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
if "results" not in st.session_state:
    st.session_state["results"] = {}

# =====================================================
# Tabs
# =====================================================

tab1, tab2 = st.tabs([
    "🔍 Scanner Search",
    "⭐ Watchlist"
])

# =====================================================
# TAB 1 - Scanner Search
# =====================================================

with tab1:

    # =================================================
    # Sidebar Filters
    # =================================================

    st.sidebar.header("🔍 Search Filters")

    selected_collection = st.sidebar.selectbox(
        "Scanner",
        ["All"] + COLLECTIONS
    )

    # Date Filter

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
            f"📅 {selected_date.strftime('%d-%m-%Y')}"
        )

    # Symbol Filter

    ticker = st.sidebar.text_input(
        "Ticker / Symbol"
    )

    # Stock Name Filter

    stock_name = st.sidebar.text_input(
        "Stock Name"
    )

    # =================================================
    # Volume Filter
    # =================================================

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

    # =================================================
    # Sorting
    # =================================================

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

    show_query = st.sidebar.checkbox(
        "Show Mongo Query"
    )

    search_clicked = st.sidebar.button(
        "🔍 Search"
    )

    # =================================================
    # Search Function
    # =================================================

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

            # Date

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

            # Symbol

            if ticker.strip():

                query["symbol"] = {
                    "$regex": ticker,
                    "$options": "i"
                }

            # Stock Name

            if stock_name.strip():

                query["stock_name"] = {
                    "$regex": stock_name,
                    "$options": "i"
                }

            # Volume

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

            if show_query:

                st.write(f"Query : {collection_name}")
                st.json(query)

            records = list(
                collection.find(query)
            )

            if records:

                df = pd.DataFrame(records)

                if "_id" in df.columns:
                    df.drop(
                        "_id",
                        axis=1,
                        inplace=True
                    )

                if "date" in df.columns:

                    df["date"] = pd.to_datetime(
                        df["date"]
                    ).dt.strftime(
                        "%d-%m-%Y"
                    )

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

    # =================================================
    # Execute Search
    # =================================================
    
    if search_clicked:
        st.session_state["results"] = search_data()
    
    results = st.session_state["results"]
    
    if results:
    
        total_records = sum(
            len(df)
            for df in results.values()
        )
    
        st.success(
            f"Found {total_records} stocks"
        )
    
        # Summary
    
        summary = []
    
        for collection_name, df in results.items():
    
            summary.append({
                "Scanner": collection_name,
                "Stocks Found": len(df)
            })
    
        st.subheader("📊 Scanner Summary")
    
        st.dataframe(
            pd.DataFrame(summary),
            hide_index=True,
            width="stretch"
        )
    
        st.subheader("📈 Results")
    
        all_results = []
    
        for collection_name, df in results.items():
    
            all_results.append(df)
    
            with st.expander(
                f"{collection_name} ({len(df)} stocks)",
                expanded=True
            ):
    
                # Headers
                header_cols = st.columns(
                    len(df.columns) + 1
                )
    
                for idx, col in enumerate(df.columns):
                    header_cols[idx].markdown(
                        f"**{col}**"
                    )
    
                header_cols[-1].markdown(
                    "**Watchlist**"
                )
    
                st.divider()
    
                # Rows
    
                for row_index, row in df.iterrows():
    
                    cols = st.columns(
                        len(df.columns) + 1
                    )
    
                    for idx, col in enumerate(df.columns):
    
                        value = row[col]
    
                        if pd.isna(value):
                            value = ""
    
                        cols[idx].write(value)
    
                    symbol = row.get("symbol", "")
    
                    if cols[-1].button(
                        "⭐ Add",
                        key=f"add_{collection_name}_{symbol}_{row_index}"
                    ):
    
                        exists = watchlist_collection.find_one(
                            {"symbol": symbol}
                        )
    
                        if not exists:
    
                            watchlist_collection.insert_one(
                                {
                                    "symbol": symbol,
                                    "stock_name": row.get(
                                        "stock_name", ""
                                    ),
                                    "added_on": datetime.utcnow()
                                }
                            )
    
                            st.toast(
                                f"{symbol} added to watchlist"
                            )
    
                        else:
    
                            st.toast(
                                f"{symbol} already exists"
                            )
    
                st.divider()
    
                csv = df.to_csv(index=False)
    
                st.download_button(
                    label=f"⬇ Download {collection_name}",
                    data=csv,
                    file_name=f"{collection_name}.csv",
                    mime="text/csv",
                    key=f"download_{collection_name}"
                )
    
        # Download All Results
    
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
    
        st.warning(
            "No records found."
        )

# =====================================================
# TAB 2 - Watchlist
# =====================================================

with tab2:

    st.subheader(
        "⭐ My Watchlist"
    )

    watchlist = list(
        watchlist_collection.find()
    )

    if watchlist:

        watch_df = pd.DataFrame(
            watchlist
        )

        if "_id" in watch_df.columns:

            watch_df.drop(
                "_id",
                axis=1,
                inplace=True
            )

        if "added_on" in watch_df.columns:

            watch_df["added_on"] = pd.to_datetime(
                watch_df["added_on"]
            ).dt.strftime(
                "%d-%m-%Y %H:%M"
            )

        st.dataframe(
            watch_df,
            hide_index=True,
            width="stretch"
        )

        stock_to_remove = st.selectbox(
            "Select Stock To Remove",
            watch_df["symbol"]
        )

        if st.button(
            "🗑 Remove From Watchlist"
        ):

            watchlist_collection.delete_one(
                {
                    "symbol": stock_to_remove
                }
            )

            st.success(
                f"{stock_to_remove} removed."
            )

            st.rerun()

    else:

        st.info(
            "Watchlist is empty."
        )
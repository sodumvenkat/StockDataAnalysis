import streamlit as st
import pandas as pd

from pymongo import MongoClient
from datetime import datetime, timedelta
from urllib.parse import quote


# =====================================================
# MongoDB Connection
# =====================================================

client = MongoClient(
    "mongodb://localhost:27017/"
)

db = client["market_data"]

client_nse_bse_data = MongoClient(
    "mongodb://localhost:27017/"
)

db_nse_bse_data = client_nse_bse_data["nse_bse_data"]
collection_nse_bse_data = db_nse_bse_data["instrument_codes"]

watchlist_collection = db["watchlist"]


# =====================================================
# Collections
# =====================================================

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
# Session State
# =====================================================

if "results" not in st.session_state:
    st.session_state["results"] = {}

if "search_performed" not in st.session_state:
    st.session_state["search_performed"] = False


# =====================================================
# Helper Functions
# =====================================================

def add_to_watchlist(symbol, stock_name=""):
    """
    Add stock to MongoDB watchlist.
    """

    if not symbol:
        return False, "Invalid symbol"

    symbol = str(symbol).upper().strip()

    existing = watchlist_collection.find_one(
        {
            "symbol": symbol
        }
    )

    if existing:
        return False, f"{symbol} already exists in watchlist"

    watchlist_collection.insert_one(
        {
            "symbol": symbol,
            "stock_name": stock_name,
            "added_on": datetime.utcnow()
        }
    )

    return True, f"{symbol} added to watchlist"


def get_tradingview_url(symbol):
    """
    Generate TradingView NSE chart URL.
    """

    symbol = str(symbol).upper().strip()

    return (
        f"https://www.tradingview.com/chart/?"
        f"symbol=NSE%3A{quote(symbol)}"
    )


def get_kite_url(symbol):
    """
    Generate Kite NSE chart URL.

    Kite chart URLs commonly use:
    /markets/ext/chart/web/ciq/NSE/<SYMBOL>/
    """

    symbol = str(symbol).upper().strip()
    success, instrument_id = get_instrument_id(symbol)
    #https://kite.zerodha.com/markets/ext/chart/web/ciq/NSE/VALIANTLAB/4919809
    return (
        f"https://kite.zerodha.com/"
        f"markets/ext/chart/web/ciq/NSE/{symbol}/{instrument_id}"
    )
def get_instrument_id(symbol):
    """
    Get instrument token from DB for NSE chart URL.
    """
    if not symbol:
        return False, "Invalid symbol"

    symbol = str(symbol).upper().strip()

    existing = collection_nse_bse_data.find_one(
        {
            "tradingsymbol": symbol,
            "exchange": "NSE"
        }
    )
    print(existing)
    if not existing:
        return False, f"Instrument not found for {symbol}"

    instrument_token = existing.get("instrument_token")

    if not instrument_token:
        return False, f"instrument_token not found for {symbol}"
    print(f"Instrument token: {instrument_token}")
    return True, instrument_token


# =====================================================
# Tabs
# =====================================================

tab1, tab2 = st.tabs(
    [
        "🔍 Scanner Search",
        "⭐ Watchlist"
    ]
)


# =====================================================
# TAB 1
# =====================================================

with tab1:

    # =================================================
    # Sidebar
    # =================================================

    st.sidebar.header(
        "🔍 Search Filters"
    )

    selected_collection = st.sidebar.selectbox(
        "Scanner",
        ["All"] + COLLECTIONS
    )


    # =================================================
    # Date Filter
    # =================================================

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


    # =================================================
    # Symbol Filter
    # =================================================

    ticker = st.sidebar.text_input(
        "Ticker / Symbol"
    )


    # =================================================
    # Stock Name Filter
    # =================================================

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


    # =================================================
    # Debug
    # =================================================

    show_query = st.sidebar.checkbox(
        "Show Mongo Query",
        value=False
    )


    # =================================================
    # Search Button
    # =================================================

    search_clicked = st.sidebar.button(
        "🔍 Search",
        width="stretch"
    )


    # =================================================
    # Search Function
    # =================================================

    def search_data():

        results = {}

        if selected_collection == "All":

            collections = COLLECTIONS

        else:

            collections = [
                selected_collection
            ]


        for collection_name in collections:

            collection = db[
                collection_name
            ]

            query = {}


            # =========================================
            # Date Filter
            # =========================================

            if (
                use_date_filter
                and selected_date
            ):

                start_date = datetime.combine(
                    selected_date,
                    datetime.min.time()
                )

                end_date = (
                    start_date
                    + timedelta(days=1)
                )

                query["date"] = {
                    "$gte": start_date,
                    "$lt": end_date
                }


            # =========================================
            # Symbol Filter
            # =========================================

            if ticker.strip():

                query["symbol"] = {
                    "$regex": ticker.strip(),
                    "$options": "i"
                }


            # =========================================
            # Stock Name Filter
            # =========================================

            if stock_name.strip():

                query["stock_name"] = {
                    "$regex": stock_name.strip(),
                    "$options": "i"
                }


            # =========================================
            # Volume Filter
            # =========================================

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


            # =========================================
            # Show Query
            # =========================================

            if show_query:

                st.write(
                    f"Query : {collection_name}"
                )

                st.json(query)


            # =========================================
            # Mongo Query
            # =========================================

            records = list(
                collection.find(query)
            )


            if not records:
                continue


            df = pd.DataFrame(
                records
            )


            # =========================================
            # Remove Mongo ID
            # =========================================

            if "_id" in df.columns:

                df.drop(
                    "_id",
                    axis=1,
                    inplace=True
                )


            # =========================================
            # Date Display
            # =========================================

            if "date" in df.columns:

                df["date"] = pd.to_datetime(
                    df["date"]
                ).dt.strftime(
                    "%d-%m-%Y"
                )


            # =========================================
            # Sorting
            # =========================================

            ascending = (
                sort_order == "Ascending"
            )


            if sort_by in df.columns:

                df.sort_values(
                    by=sort_by,
                    ascending=ascending,
                    inplace=True
                )


            results[
                collection_name
            ] = df


        return results


    # =================================================
    # Execute Search
    # =================================================

    if search_clicked:

        st.session_state[
            "results"
        ] = search_data()

        st.session_state[
            "search_performed"
        ] = True


    results = st.session_state[
        "results"
    ]


    # =================================================
    # Display Results
    # =================================================

    if st.session_state[
        "search_performed"
    ]:

        if results:

            total_records = sum(
                len(df)
                for df in results.values()
            )


            st.success(
                f"Found {total_records} stocks"
            )


            # =========================================
            # Summary
            # =========================================

            summary = []


            for collection_name, df in results.items():

                summary.append(
                    {
                        "Scanner": collection_name,
                        "Stocks Found": len(df)
                    }
                )


            st.subheader(
                "📊 Scanner Summary"
            )


            st.dataframe(
                pd.DataFrame(summary),
                hide_index=True,
                width="stretch"
            )


            st.subheader(
                "📈 Results"
            )


            all_results = []


            # =========================================
            # Collection Results
            # =========================================

            for collection_name, df in results.items():

                all_results.append(df)


                with st.expander(
                    f"{collection_name} ({len(df)} stocks)",
                    expanded=True
                ):


                    # =================================
                    # Header
                    # =================================

                    header_cols = st.columns(
                        len(df.columns) + 2
                    )


                    for idx, col in enumerate(
                        df.columns
                    ):

                        header_cols[
                            idx
                        ].markdown(
                            f"**{col}**"
                        )


                    header_cols[
                        len(df.columns)
                    ].markdown(
                        "**Action**"
                    )


                    header_cols[
                        len(df.columns) + 1
                    ].markdown(
                        "**Submit**"
                    )


                    st.divider()


                    # =================================
                    # Each Stock
                    # =================================

                    for row_index, row in df.iterrows():

                        cols = st.columns(
                            len(df.columns) + 2
                        )


                        # =============================
                        # Stock Data
                        # =============================

                        for idx, col in enumerate(
                            df.columns
                        ):

                            value = row[col]


                            if pd.isna(value):

                                value = ""


                            cols[
                                idx
                            ].write(
                                value
                            )


                        # =============================
                        # Symbol
                        # =============================

                        symbol = str(
                            row.get(
                                "symbol",
                                ""
                            )
                        ).strip()


                        stock_name_value = str(
                            row.get(
                                "stock_name",
                                ""
                            )
                        )


                        # =============================
                        # Action Dropdown
                        # =============================

                        action = cols[
                            len(df.columns)
                        ].selectbox(

                            "Action",

                            [
                                "None",
                                "TradingView",
                                "Kite",
                                "Watchlist"
                            ],

                            key=(
                                f"action_"
                                f"{collection_name}_"
                                f"{symbol}_"
                                f"{row_index}"
                            ),

                            label_visibility="collapsed"
                        )


                        # =============================
                        # Submit
                        # =============================

                        submit = cols[
                            len(df.columns) + 1
                        ].button(

                            "Submit",

                            key=(
                                f"submit_"
                                f"{collection_name}_"
                                f"{symbol}_"
                                f"{row_index}"
                            ),

                            width="stretch"
                        )


                        # =============================
                        # Action Processing
                        # =============================

                        if submit:

                            if not symbol:

                                st.error(
                                    "Symbol is empty."
                                )

                                continue


                            # -------------------------
                            # TradingView
                            # -------------------------

                            if action == "TradingView":

                                tradingview_url = (
                                    get_tradingview_url(
                                        symbol
                                    )
                                )


                                st.success(
                                    f"Opening TradingView for {symbol}"
                                )


                                st.link_button(
                                    "📈 Open TradingView",
                                    tradingview_url,
                                    width="stretch"
                                )


                            # -------------------------
                            # Kite
                            # -------------------------

                            elif action == "Kite":

                                kite_url = (
                                    get_kite_url(
                                        symbol
                                    )
                                )


                                st.success(
                                    f"Opening Kite for {symbol}"
                                )


                                st.link_button(
                                    "📊 Open Kite",
                                    kite_url,
                                    width="stretch"
                                )


                            # -------------------------
                            # Watchlist
                            # -------------------------

                            elif action == "Watchlist":

                                added, message = (
                                    add_to_watchlist(
                                        symbol,
                                        stock_name_value
                                    )
                                )


                                if added:

                                    st.success(
                                        f"⭐ {message}"
                                    )

                                else:

                                    st.info(
                                        f"⭐ {message}"
                                    )


                            # -------------------------
                            # None
                            # -------------------------

                            else:

                                st.info(
                                    "Please select an action."
                                )


                    st.divider()


                    # =================================
                    # Download Collection
                    # =================================

                    csv = df.to_csv(
                        index=False
                    )


                    st.download_button(

                        label=(
                            f"⬇ Download "
                            f"{collection_name}"
                        ),

                        data=csv,

                        file_name=(
                            f"{collection_name}.csv"
                        ),

                        mime="text/csv",

                        key=(
                            f"download_"
                            f"{collection_name}"
                        ),

                        width="content"
                    )


            # =========================================
            # Download All
            # =========================================

            if all_results:

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

                    mime="text/csv",

                    key="download_all_results",

                    width="content"
                )


        else:

            st.warning(
                "No records found."
            )


# =====================================================
# TAB 2 - WATCHLIST
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

            watch_df[
                "added_on"
            ] = pd.to_datetime(
                watch_df["added_on"]
            ).dt.strftime(
                "%d-%m-%Y %H:%M"
            )


        st.dataframe(
            watch_df,
            hide_index=True,
            width="stretch"
        )


        # =============================================
        # Remove From Watchlist
        # =============================================

        stock_to_remove = st.selectbox(

            "Select Stock To Remove",

            watch_df["symbol"].tolist()
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
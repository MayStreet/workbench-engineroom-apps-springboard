import datetime
from typing import List

import maystreet_data as md
import pandas as pd
import streamlit as st
from bokeh.plotting import figure


def get_price_summary_by_minute(
    product: str, feeds: List[str], day: datetime.date
) -> pd.DataFrame:
    dt = day.isoformat()
    feeds_filter = ", ".join(f"'{f}'" for f in feeds)

    query = f"""
    WITH
        price_and_time AS (
            SELECT
                f,
                product,
                DATE_TRUNC('minute', TO_TIMESTAMP(exchangetimestamp / 1000000000)) AS dp_minute,
                MIN(price) AS min_price,
                MAX(price) AS max_price,
                MIN(receipttimestamp) AS min_receipt,
                MAX(receipttimestamp) AS max_receipt
            FROM
                "prod_lake.p_mst_data_lake".mt_trade
            WHERE
                dt = '{dt}'
                AND "product" = '{product}'
                AND f IN ({feeds_filter})
            GROUP BY 1, 2, 3
        )
    SELECT
        dp_minute,
        f,
        product,
        min_price,
        max_price,
        (SELECT
            MIN(price)
        FROM
            "prod_lake.p_mst_data_lake".mt_trade
        WHERE
            dt = '{dt}'
            AND "product" = '{product}'
            AND f IN ({feeds_filter})
            AND receipttimestamp = min_receipt
        ) AS open_price,
        (SELECT
            MAX(price)
        FROM
            "prod_lake.p_mst_data_lake".mt_trade
        WHERE
            dt = '{dt}'
            AND "product" = '{product}'
            AND f IN ({feeds_filter})
            AND receipttimestamp = max_receipt
        ) close_price
    FROM
        price_and_time
    ORDER BY dp_minute
    """

    prices = pd.DataFrame(list(md.query(md.DataSource.DATA_LAKE, query)))
    if prices.empty:
        return prices

    return prices.assign(dp_minute=pd.to_datetime(prices["dp_minute"], unit="ms"))


feed_options = [
    "bats_edga",
    "bats_edga_car",
    "bats_edgx",
    "byx",
    "byx_car",
    "bzx",
    "iex_deep",
    "iex_deep_car",
    "iex_tops",
    "iex_tops_car",
    "memoir_depth",
    "miax_pearl_equities_dom",
    "total_view_bx",
    "total_view_psx",
    "utdf_binary",
    "utdf_binary_car",
]
initial_feed_selection = ["bats_edga", "bats_edgx"]

product_options = ["(None)", "AAPL", "TSLA", "IBM", "F"]

page_title = "Analytics Workbench Example Data Dashboard"

# header info
st.set_page_config(page_title=page_title, initial_sidebar_state="expanded")

st.markdown(
    """
    <style type="text/css">
        .title-img-div {
            width: 80px;
            margin: auto auto;
            text-align: center;
            display: block;
            height: 74px;
            /* you may change this to your preferred image :-) */
            background-image: url(https://maystreet.com/wp-content/uploads/2022/01/MST_MasterLogo_Horizontal_FullColor_2020-02-25@2x.png);
            background-repeat: no-repeat;
            background-position: 14px 0;
        }

        .title-caption {
            text-align: center;
            line-height: 36px;
            padding-bottom: 20px;
            font-size: 24px;
            # text-transform: uppercase;
            color: rgb(215,47,39);
        }

        h1 {
            padding-top: 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    f"""
    <div class="title-img-div"></div>
    <div class="title-caption">{page_title}</div>
    """,
    unsafe_allow_html=True,
)

selected_feeds = st.sidebar.multiselect(
    "Feeds:",
    feed_options,
    default=initial_feed_selection,
    help="The selected feeds that will be queried for this data",
)
selected_product = st.sidebar.selectbox(
    "Product:", product_options, help="Product to view"
)
selected_date = st.sidebar.date_input(
    "Date:", datetime.date(2022, 3, 15), help="Start date for product"
)

no_selected_product = selected_product == "(None)"
no_selected_feeds = len(selected_feeds) == 0

run_query = st.sidebar.button(
    "Run Query",
    key="run-query-button",
    disabled=no_selected_product or not selected_date or no_selected_feeds,
)

[t1] = st.columns(1)
t1.title("Example Market Data Dashboard")
t1.markdown(
    """
    This simple application will retrieve data from MayStreet's Data Lake in the form of minute bars and display in a variety of ways.
    <br />&nbsp;
    <br />&nbsp;
""",
    unsafe_allow_html=True,
)

with st.spinner("Running Query..."):
    # graph showing data
    if (
        run_query
        and not no_selected_feeds
        and not no_selected_product
        and selected_date
    ):
        prices = get_price_summary_by_minute(
            selected_product, selected_feeds, selected_date
        )

        if prices.empty:
            t1.text('No data available for the selected query.')
        else: 
            high, low, open, close = st.columns(4)
            high.metric("High", prices["max_price"].max())
            low.metric("Low", prices["min_price"].min())
            open.metric("Open", prices["open_price"].iat[0])
            close.metric("Close", prices["close_price"].iat[-1])

            basic_candlestick = st.expander("Basic Candlestick Graph")
            basic_candlestick.vega_lite_chart(
                prices,
                {
                    "encoding": {
                        "x": {
                            "field": "dp_minute",
                            "type": "temporal",
                            "title": "Time",
                            "axis": {"format": "%H:%M", "labelAngle": -45, "title": "Time"},
                        },
                        "y": {
                            "type": "quantitative",
                            "scale": {"zero": False},
                            "axis": {"title": "Price"},
                        },
                        "color": {
                            "condition": {
                                "test": "datum.open_price < datum.close_price",
                                "value": "#06982d",
                            },
                            "value": "#ae1325",
                        },
                    },
                    "layer": [
                        {
                            "mark": "rule",
                            "encoding": {
                                "y": {"field": "min_price"},
                                "y2": {"field": "max_price"},
                            },
                        },
                        {
                            "mark": "bar",
                            "encoding": {
                                "y": {"field": "open_price"},
                                "y2": {"field": "close_price"},
                            },
                        },
                    ],
                    "height": 400,
                },
                use_container_width=True,
            )

            enhanced_candlestick = st.expander("Enhanced Candlestick Graph")

            increasing = prices.close_price > prices.open_price
            decreasing = prices.open_price > prices.close_price
            bar_width = 60 * 1000

            candlestick_figure = figure(
                x_axis_type="datetime",
                tools="pan,wheel_zoom,box_zoom,reset,save",
                width=1000,
                title="Candlestick",
            )
            candlestick_figure.grid.grid_line_alpha = 0.3

            candlestick_figure.segment(
                prices.dp_minute,
                prices.max_price,
                prices.dp_minute,
                prices.min_price,
                color="black",
            )
            candlestick_figure.vbar(
                prices.dp_minute[increasing],
                bar_width,
                prices.open_price[increasing],
                prices.close_price[increasing],
                fill_color="#D5E1DD",
                line_color="black",
            )
            candlestick_figure.vbar(
                prices.dp_minute[decreasing],
                bar_width,
                prices.open_price[decreasing],
                prices.close_price[decreasing],
                fill_color="#F2583E",
                line_color="black",
            )

            enhanced_candlestick.bokeh_chart(candlestick_figure, use_container_width=True)

            feed_source = st.expander("Feed Source Graph")
            feed_source.vega_lite_chart(
                prices,
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {
                            "field": "f",
                            "title": "Feed",
                            "axis": {"labelAngle": -45, "title": "Feed"},
                        },
                        "y": {
                            "type": "quantitative",
                            "aggregate": "count",
                            "scale": {"zero": False},
                            "axis": {"title": "Rows per Feed"},
                        },
                    },
                    "height": 400,
                },
                use_container_width=True,
            )

            prices_table = st.expander("Raw Data Table")
            prices_table.dataframe(
                prices.rename(
                    columns={
                        "dp_minute": "Date/Time",
                        "product": "Product",
                        "f": "Feed",
                        "min_price": "Min Price",
                        "max_price": "Max Price",
                        "close_price": "Close Price",
                        "open_price": "Open Price",
                    },
                ),
                height=400,
            )

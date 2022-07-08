import streamlit as st
import pandas as pd
from PIL import Image
import datetime
from dateutil import parser
import plotly.express as px
import plotly.graph_objects as go
from bokeh.plotting import figure, show

# fix an issue where the thread Streamlit runs the app under doesn't provide us an async event loop.
# this needs to be done before we include the MayStreet Data Library or anything else that initialises the async IO

import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# now import the MayStreet Data Libraries

import maystreet_data as md

# statics

all_columns = ["product", "f", "dp_minute", "min_price", "max_price", "open_price", "close_price"]

valid_products = [
    '(None)',
    'AAPL',
    'TSLA',
    'IBM',
    'F'
]

valid_sources = [
    'bats_edga',
    'bats_edga_car',
    'bats_edgx',
    'byx',
    'byx_car',
    'bzx',
    'iex_deep',
    'iex_deep_car',
    'iex_tops',
    'iex_tops_car',
    'memoir_depth',
    'miax_pearl_equities_dom',
    'total_view_bx',
    'total_view_psx',
    'utdf_binary',
    'utdf_binary_car'
]

initial_valid_sources = [
    'bats_edga',
    'bats_edgx'
]

# maystreet data functions


def fetch_rows(product, feeds, target_date):

    target_month = str(target_date.month).rjust(2, '0')
    target_day = str(target_date.day).rjust(2, '0')

    concatenated_feeds =  ', '.join(f'\'{f}\'' for f in feeds)

    query = f"""
    WITH price_and_time AS (
    SELECT f, product, DATE_TRUNC('minute', TO_TIMESTAMP(ExchangeTimestamp / 1000000000)) as dp_minute, min(price) as min_price, max(price) as max_price, MIN(ReceiptTimestamp) min_receipt, MAX(ReceiptTimestamp) max_receipt
    FROM "prod_lake.p_mst_data_lake".mt_trade 
    WHERE "y" = '{target_date.year}' AND "m" = '{target_month}' AND "d" = '{target_day}' AND "product" = '{product}' AND f IN ({concatenated_feeds})
    GROUP BY f, DATE_TRUNC('minute', TO_TIMESTAMP(ExchangeTimestamp / 1000000000)), product
    )
    SELECT 
            f,
            product, 
            dp_minute, 
            min_price,
            (SELECT min(Price) FROM "prod_lake.p_mst_data_lake".mt_trade WHERE "y" = '{target_date.year}' and "m" = '{target_month}' and "d" = '{target_day}' and ReceiptTimestamp=min_receipt and product=price_and_time.product) open_price,
            (SELECT max(Price) FROM "prod_lake.p_mst_data_lake".mt_trade WHERE "y" = '{target_date.year}' and "m" = '{target_month}' and "d" = '{target_day}' and ReceiptTimestamp=max_receipt and product=price_and_time.product) close_price,
            max_price
    FROM price_and_time
    ORDER BY f, product, dp_minute
    """

    # print(query)

    return product, list(md.query(md.DataSource.DATA_LAKE, query))


page_title = "Analytics Workbench Example Data Dashboard"

# header info
st.set_page_config(page_title=page_title, initial_sidebar_state="expanded" )

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
    unsafe_allow_html=True
)

st.sidebar.markdown(
    f"""
        <div class="title-img-div" >
        </div>
        <div class="title-caption">
            {page_title}
       </div>

    """,
    unsafe_allow_html=True
)


mapped_products =  list(valid_products)
selected_sources = st.sidebar.multiselect('Selected Feeds:', valid_sources, default = initial_valid_sources, help = 'The selected feeds that will be queried for this data')
selected_product = st.sidebar.selectbox('Selected Product:', mapped_products, help = 'Product to view')
selected_date = st.sidebar.date_input('Selected Date:', datetime.date(2022, 3, 15), help = 'Start date for product')

no_selected_product = selected_product == '(None)'
no_selected_sources = len(selected_sources) == 0

execute_run = st.sidebar.button('Execute Query', key = "execute-button", disabled = no_selected_product or not selected_date or no_selected_sources)
# selected_time = st.sidebar.time_input('Selected Start Time:',  datetime.time(8, 45))

[t1] = st.columns((1))
t1.title("Example Market Data Dashboard")
t1.markdown(
    """
    This simple application will retrieve data from MayStreet's Market Data Repository in the form of minute bars and display in a variety of ways.
    <br />&nbsp;
    <br />&nbsp;
""",
    unsafe_allow_html=True,
)


with st.spinner('Running Query...'):

    # graph showing data
    if(execute_run and not no_selected_product and selected_date and not no_selected_sources):
        target_product, retrieved_rows = fetch_rows(selected_product, selected_sources, selected_date)
        df = pd.DataFrame(retrieved_rows, columns=all_columns)

        df["dp_time"] = pd.to_datetime(df["dp_minute"], unit='ms')
        df.sort_values(by=['dp_time'])

        df.insert(0, 'dp_time', df.pop('dp_time'))


        col1, col2, col3, col4 = st.columns(4)
        col1.metric("High", df['max_price'].max())
        col2.metric("Low",  df['min_price'].min())
        col3.metric("Open", df['open_price'][0])
        col4.metric("Close", df['close_price'][-1:])

        second_group = st.expander("Basic Candlestick Graph")
        second_group.vega_lite_chart(df, {
            "encoding": {
                "x": {
                    "field": "dp_time",
                    "type": "temporal",
                    "title": "Date",
                    "axis": {
                        "format": "%m/%d",
                        "labelAngle": -45,
                        "title": "Date"
                    }
                },
                "y": {
                    "type": "quantitative",
                    "scale": {"zero": False},
                    "axis": {"title": "Price"}
                    },
                    "color": {
                    "condition": {
                        "test": "datum.open_price < datum.close_price",
                        "value": "#06982d"
                    },
                    "value": "#ae1325"
                }
            },
            "layer": [
                {
                    "mark": "rule",
                    "encoding": {
                        "y": {"field": "min_price"},
                        "y2": {"field": "max_price"}
                    }
                },
                {
                    "mark": "bar",
                    "encoding": {
                        "y": {"field": "open_price"},
                        "y2": {"field": "close_price"}
                    }
                }
            ],
            "height": 400
        }, use_container_width=True)



        nice_thingy_group = st.expander("Enhanced Candlestick Graph")

        inc = df.close_price > df.open_price
        dec = df.open_price > df.close_price
        w = 60 * 1000

        TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

        p = figure(x_axis_type="datetime", tools=TOOLS, width=1000, title = "Candlestick")
        p.grid.grid_line_alpha=0.3

        p.segment(df.dp_time, df.max_price, df.dp_time, df.min_price, color="black")
        p.vbar(df.dp_time[inc], w, df.open_price[inc], df.close_price[inc], fill_color="#D5E1DD", line_color="black")
        p.vbar(df.dp_time[dec], w, df.open_price[dec], df.close_price[dec], fill_color="#F2583E", line_color="black")

        nice_thingy_group.bokeh_chart(p, use_container_width=True)


        third_group = st.expander("Feed Source Graph")
        third_group.vega_lite_chart(df, {
            "mark": "bar",
            "encoding": {
                "x": {
                    "field": "f",
                    "title": "Feed",
                    "axis": {
                        "labelAngle": -45,
                        "title": "Feed"
                    }
                },
                "y": {
                    "type": "quantitative",
                    "aggregate": "count",
                    "scale": {"zero": False},
                    "axis": {"title": "Volume of Trades"}
                }
            },
            "height": 400
        }, use_container_width=True)



        first_group = st.expander("Raw Data Table")

        tidied_db = df.drop(columns=['dp_minute'])
        tidied_db.rename(columns={
            'product': 'Product',
            'f': 'Feed',
            'min_price': 'Min Price',
            'max_price': 'Max Price',
            'close_price':'Close Price',
            'open_price': 'Open Price',
            'dp_time': 'Date/Time'
        }, inplace=True)
        first_group.dataframe(tidied_db, height=400)




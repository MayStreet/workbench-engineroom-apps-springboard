import pandas as pd
import streamlit as st
import time
import numpy as np

st.title('Streamlit 1.23.0 - 1.30.0 new features')

# Data editor
DATE_COLUMN = 'date/time'
DATA_URL = ('https://s3-us-west-2.amazonaws.com/'
         'streamlit-demo-data/uber-raw-data-sep14.csv.gz')

def load_data(nrows):
    data = pd.read_csv(DATA_URL, nrows=nrows)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)
    data[DATE_COLUMN] = pd.to_datetime(data[DATE_COLUMN])
    return data

data = load_data(100)

st.header('st.data_editor')
st.text('The data editor widget allows you to edit dataframes and many other data structures in a table-like UI.')
st.data_editor(data)

# Status
st.header('st.status')
st.text('Insert a status container to display output from long-running tasks.')
with st.status("Downloading data...") as status:
    st.write("Searching for data...")
    time.sleep(2)
    st.write("Found URL.")
    time.sleep(1)
    st.write("Downloading data...")
    time.sleep(1)
    status.update(label="Download complete!", state="complete", expanded=False)

st.button('Rerun')

# Scatter chart
st.header('st.scatter_chart')
st.text('Display a scatterplot chart.')
chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])
st.scatter_chart(chart_data)

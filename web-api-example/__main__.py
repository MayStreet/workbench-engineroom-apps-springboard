import datetime

from fastapi import FastAPI
import maystreet_data
import uvicorn


app = FastAPI()


@app.get("/aapl-hourly-avg/{year}/{month}/{day}")
def hourly_avg(year: int, month: int, day: int):
    dt = datetime.date(year, month, day).isoformat()

    query = f"""
    SELECT
        DATE_TRUNC('hour', TO_TIMESTAMP(ExchangeTimestamp / 1000000000)) AS hour_ts,
        AVG(price) as avg_price
    FROM
        "prod_lake"."p_mst_data_lake".mt_trade
    WHERE
        dt = '{dt}'
        AND product = 'AAPL'
        AND f = 'bats_edga'
    GROUP BY 1
    ORDER BY 1
    """

    return list(maystreet_data.query(maystreet_data.DataSource.DATA_LAKE, query))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

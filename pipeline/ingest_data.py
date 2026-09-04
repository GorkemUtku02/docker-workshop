#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import click
from sqlalchemy import create_engine
from tqdm.auto import tqdm

dtype = {
    "VendorID": "Int64",
    "passenger_count": "Int64",
    "trip_distance": "float64",
    "RatecodeID": "Int64",
    "store_and_fwd_flag": "string",
    "PULocationID": "Int64",
    "DOLocationID": "Int64",
    "payment_type": "Int64",
    "fare_amount": "float64",
    "extra": "float64",
    "mta_tax": "float64",
    "tip_amount": "float64",
    "tolls_amount": "float64",
    "improvement_surcharge": "float64",
    "total_amount": "float64",
    "congestion_surcharge": "float64",
}

parse_dates = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]



@click.command()
@click.option('--pg-user', default='root', show_default=True)
@click.option('--pg-pass', default='root', show_default=True)
@click.option('--pg-host', default='localhost', show_default=True)
@click.option('--pg-port', default=5432, show_default=True, type=int)
@click.option('--pg-db', default='ny_taxi', show_default=True)
@click.option('--target-table', default='yellow_taxi_data', show_default=True)
@click.option('--year', default=2021, show_default=True, type=int)
@click.option('--month', default=1, show_default=True, type=click.IntRange(1, 12))
@click.option('--chunksize', default=100_000, show_default=True, type=int)
def run(pg_user, pg_pass, pg_host, pg_port, pg_db, target_table, year, month, chunksize):


    prefix = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow"
    url = f"{prefix}/yellow_tripdata_{year}-{month:02d}.csv.gz"

    engine = create_engine(f'postgresql+psycopg://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')


    df_iter = pd.read_csv(
        url,
        dtype=dtype,
        parse_dates=parse_dates,
        iterator=True,
        chunksize=chunksize,
    )

    first = True
    for df_chunk in tqdm(df_iter):
        if first:
            df_chunk.head(0).to_sql(
                name=target_table,
                con=engine,
                if_exists='replace',
                index=False,
            )
            first = False

        df_chunk.to_sql(
            name=target_table,
            con=engine,
            if_exists='append',
            index=False,
        )


if __name__ == '__main__':
    run()
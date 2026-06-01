import os
from google.cloud import bigquery
import pyarrow
import pandas as pd

def upload_coordinates_dictionary(df_geo: dict) -> None:
    '''
    Uploads the updated geographic lookup dictionary.
    Using WRITE_TRUNCATE instead of WRITE_APPEND is a negligible difference in terms of costs with just ~160-180 rows by 4 columns.
    '''

    client = bigquery.Client()
    table_id = "citydna-dashboard-x.cityDNA_dataset.Coordinates_dictionary"

    schema = [
        bigquery.SchemaField("Destinations", "STRING"),
        bigquery.SchemaField("Country", "STRING"), 
        bigquery.SchemaField("Latitude", "FLOAT"),
        bigquery.SchemaField("Longitude", "FLOAT"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
    )

    job = client.load_table_from_dataframe(df_geo, table_id, job_config=job_config)
    job.result()  # Wait for job to complete

def upload_historical_bednights_table(dfm: pd.DataFrame) -> None:
    '''
    Uploads the final dataframe to BigQuery for use in the PowerBi dashboard.
    '''

    client = bigquery.Client()
    table_id = "citydna-dashboard-x.cityDNA_dataset.Monthly_data_v4_yearly_estimates"

    schema = [
        bigquery.SchemaField("Destinations", "STRING"),
        bigquery.SchemaField("Definition", "STRING"), 
        bigquery.SchemaField("Market", "STRING"),
        bigquery.SchemaField("Year", "INTEGER"),
        bigquery.SchemaField("Month", "INTEGER"),
        bigquery.SchemaField("Bed nights", "INTEGER"),
        bigquery.SchemaField("Date", "DATE"),
        bigquery.SchemaField("City category", "STRING"),
        bigquery.SchemaField("Season", "STRING"),
        bigquery.SchemaField("Country", "STRING"),
        bigquery.SchemaField("Latitude", "FLOAT64"),
        bigquery.SchemaField("Longitude", "FLOAT64"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
    )

    job = client.load_table_from_dataframe(dfm, table_id, job_config=job_config)
    job.result()  # Wait for job to complete

def append_new_data_to_bednights_table(dfm: pd.DataFrame) -> None:
    '''
    Appends new data to the existing bednights table in BigQuery.
    '''

    client = bigquery.Client()
    table_id = "citydna-dashboard-x.cityDNA_dataset.Monthly_data_temporary_table"

    schema = [
        bigquery.SchemaField("Destinations", "STRING"),
        bigquery.SchemaField("Definition", "STRING"), 
        bigquery.SchemaField("Market", "STRING"),
        bigquery.SchemaField("Year", "INTEGER"),
        bigquery.SchemaField("Month", "INTEGER"),
        bigquery.SchemaField("Bed nights", "INTEGER"),
        bigquery.SchemaField("Date", "DATE"),
        bigquery.SchemaField("City category", "STRING"),
        bigquery.SchemaField("Season", "STRING"),
        bigquery.SchemaField("Country", "STRING"),
        bigquery.SchemaField("Latitude", "FLOAT64"),
        bigquery.SchemaField("Longitude", "FLOAT64"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
    )

    job = client.load_table_from_dataframe(dfm, table_id, job_config=job_config)
    job.result()  # Wait for job to complete

    query = """
    MERGE `citydna-dashboard-x.cityDNA_dataset.Monthly_data_v4_yearly_estimates` T
    USING `citydna-dashboard-x.cityDNA_dataset.Monthly_data_temporary_table` S
    ON T.Destinations = S.Destinations
    AND T.Definition = S.Definition
    AND T.Market = S.Market
    AND T.Year = S.Year
    AND T.Month = S.Month
    WHEN MATCHED THEN
        UPDATE SET T.`Bed nights` = S.`Bed nights`
    WHEN NOT MATCHED THEN
        INSERT ROW
    """

    client.query(query).result()
    client.delete_table("citydna-dashboard-x.cityDNA_dataset.Monthly_data_temporary_table")

def upload_historical_population_table(df_pop: pd.DataFrame) -> None:
    '''
    Uploads the final dataframe to BigQuery for use in the PowerBi dashboard.
    '''

    client = bigquery.Client()
    table_id = "citydna-dashboard-x.cityDNA_dataset.Population_statistics_v3"

    schema = [
        bigquery.SchemaField("Destination", "STRING"),
        bigquery.SchemaField("Year", "INTEGER"),
        bigquery.SchemaField("Date", "DATE"),
        bigquery.SchemaField("Definition", "STRING"),
        bigquery.SchemaField("Population", "INTEGER"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",  #Replace with WRITE_APPEND to append to the table instead of replacing it.
    )

    job = client.load_table_from_dataframe(df_pop, table_id, job_config=job_config)
    job.result()  # Wait for job to complete

def append_new_data_to_population_table(df_pop: pd.DataFrame) -> None:
    '''
    Appends new data to the existing population table in BigQuery.
    '''

    client = bigquery.Client()
    table_id = "citydna-dashboard-x.cityDNA_dataset.Population_statistics_v3_temporary_table"

    schema = [
        bigquery.SchemaField("Destination", "STRING"),
        bigquery.SchemaField("Year", "INTEGER"),
        bigquery.SchemaField("Date", "DATE"),
        bigquery.SchemaField("Definition", "STRING"),
        bigquery.SchemaField("Population", "INTEGER"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
    )

    job = client.load_table_from_dataframe(df_pop, table_id, job_config=job_config)
    job.result()  # Wait for job to complete

    query = """
    MERGE `citydna-dashboard-x.cityDNA_dataset.Population_statistics_v3` T
    USING `citydna-dashboard-x.cityDNA_dataset.Population_statistics_v3_temporary_table` S
    ON T.Destination = S.Destination
    AND T.Definition = S.Definition
    AND T.Year = S.Year
    WHEN MATCHED THEN
        UPDATE SET T.`Population` = S.`Population`
    WHEN NOT MATCHED THEN
        INSERT ROW
    """

    client.query(query).result()
    client.delete_table("citydna-dashboard-x.cityDNA_dataset.Population_statistics_v3_temporary_table")
import requests as rq
import xml.etree.ElementTree as ET
import pandas as pd
from io import BytesIO
import os
from google.cloud import bigquery
import pyarrow

def build_city_dict(token: str) -> dict:
    '''
    Builds a dictionary of shorthand city names to full city names. The API returns shorthand city names, so using this to convert those to full city names is required to make it look nice in the dashboard.

    Note: This function design assumes you run it immediately after grabbing a token. Otherwise the token might have expired and this function needs to be updated to handle token errors, similar to the collect_data() function.
    '''
    url = f'https://www.tourmis.info/api.pl?c=NG&m=DK&x=1&l=en&token={token}'
    result = rq.get(url)
    xml_data = result.content
    xml_file_like = BytesIO(xml_data)
    context = ET.iterparse(xml_file_like, events=('start', 'end'))

    city_dict = {}
    for _, elem in context:
        try:
            city_dict.update({elem.find('code').text : elem.find('label').text})
        except:
            pass

    to_remove = [
        'AD', 'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'GE', 'DE', 'GR', 
        'HU', 'IS', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'ME', 'NL', 'NO', 'PL', 'PT', 'RO', 
        'RU', 'SM', 'RS', 'SK', 'SI', 'ES', 'SE', 'CH', 'TR', 'UA', 'UK',
        'BU', 'KA', 'FO', 'BEFLBRU', 'NI', 'SA', 'ST', 'TI', 'OB', 'VO',
        'WI', 'NG', 'JER'
    ]
    for key in to_remove: #Filter out countries and unwanted regions.
        city_dict.pop(key, None)
    
    return(city_dict)

def build_market_dict(token: str) -> dict:
    '''
    Builds a dictionary of shorthand market names to full market names. The API returns shorthand market names, so using this to convert those to full market names is required to make it look nice in the dashboard.

    Note: This function design assumes you run it immediately after grabbing a token. Otherwise the token might have expired and this function needs to be updated to handle token errors, similar to the collect_main_data() function.
    '''
    url = f'https://www.tourmis.info/api.pl?d=CPH&c=NG&x=1&l=en&token={token}'
    result = rq.get(url)
    xml_data = result.content
    xml_file_like = BytesIO(xml_data)
    context = ET.iterparse(xml_file_like, events=('start', 'end'))

    market_dict = {}
    for event, elem in context:
        if event == 'end' and elem.tag == 'data':
            if elem.find('code').text == 'NG': #Filters out an error in the market_dict data
                pass
            else:
                market_dict.update({elem.find('code').text : elem.find('label').text})
    return(market_dict)

def download_coordinates_dictionary() -> dict:
    '''
    Downloads a cached lookup dictionary for geographic information (country, latitude, longitude) for each known destinations.
    The lookup function for geographic information for cities currently uses a free API with a 1 second delay required, so using cached values when possible saves a lot of time.
    '''
    client = bigquery.Client()

    #Get the unique definition for each destinations
    query = """
    SELECT *
    FROM `citydna-dashboard-x.cityDNA_dataset.Coordinates_dictionary`
    """

    query_job = client.query(query)
    results = query_job.result()
    df_geo = results.to_dataframe()
    df_geo.set_index(keys='Destinations', drop=True, inplace=True)
    df_geo = df_geo.to_dict(orient='index')
    return(df_geo)

def get_population_definitions(city_dict: dict) -> dict:
    '''
    Grabs each unique combination of definition and destination from the bednights table created earlier in the pipeline.
    '''
    client = bigquery.Client()

    #Get the unique definition for each destinations
    query = """
    SELECT DISTINCT 
        Destinations,
        Definition
    FROM `citydna-dashboard-x.cityDNA_dataset.Monthly_data_v4_yearly_estimates`
    WHERE Definition LIKE 'N%'
    ORDER BY Destinations
    """

    try:
        query_job = client.query(query)
        results = query_job.result()
        df_pop = results.to_dataframe()
        
    except Exception as e:
        print(f"Error executing query: {e}")

    def convert_to_population_definitions(row):
        #Definitions are defined in a way where destinations report data for either the city area or the city AND sorrounding neighbourhoods area.
        #An "S" on the end of any definition used by a destination denotes that it's the city and sorrounding neighbourhood area, which means the only thing that's needed to differentiate between the two
        #is checking whether the last letter in a given city's definition is an "S". Based on that the function return "POP" which is the key for population within the city or "POPS" which is the key
        #for the population within the city + sorrounding neighbourhoods area.
        if row[-1:] == 'S':
            return('POPS')
        else:
            return('POP')

    df_pop['Definition'] = df_pop['Definition'].apply(convert_to_population_definitions)
    reversed_city_dict = {value: key for key, value in city_dict.items()} #The dataframe has the full names of the destinations and the shorthand names are needed to look up population values for the
    #destinations in the API. To achieve that, the city_dict is reversed and then mapped onto the dataframe's "Destinations" column.
    df_pop['Destinations'] = df_pop['Destinations'].map(reversed_city_dict)
    df_pop.set_index(keys = 'Destinations', drop = True, inplace = True)
    df_pop = df_pop.to_dict()
    df_pop = df_pop['Definition'] #Un-nest the dictionary for ease of reference.
    return(df_pop)
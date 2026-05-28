import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

def format_raw_data(dfm: pd.DataFrame, market_dict: dict, city_dict: dict) -> pd.DataFrame:
    '''
    Formats dates, sets dtypes and converts values in columns using df.map() to dictionaries.
    '''
    date_str = np.where(
        dfm['Month'] == '13',
        '31-12-' + dfm['Year'],
        '1-' + dfm['Month'] + '-' + dfm['Year']
    )

    dfm['Date'] = pd.to_datetime(date_str, dayfirst=True, format="%d-%m-%Y").date

    dfm = dfm[dfm['Market'].isin(market_dict.keys()) & dfm['Destinations'].isin(city_dict.keys())].copy()

    dfm['Market'] = dfm['Market'].map(market_dict)
    dfm['Destinations'] = dfm['Destinations'].map(city_dict)

    dfm['Month'] = dfm['Month'].astype('Int64')
    dfm['Year'] = dfm['Year'].astype('Int64')

    return(dfm)

def filter_out_invalid_sets(dfm: pd.DataFrame) -> pd.DataFrame:
    '''
    Filters out destinations with no data or breaks in the continuity of their data.
    '''
    dfy = dfm.loc[(dfm['Month'] == 13) & (~dfm['Bed nights'].isna())].copy()
    dfm = dfm.loc[(dfm['Month'] != 13)].copy()

    dfm['Bed nights'] = pd.to_numeric(dfm['Bed nights'], errors='coerce')

    #Destinations are included IF January has valid data and the data is continuous (the == x['Month'].max() check near the bottom of this chain)
    #Tourism data is often delayed, so allowing for missing values is necessary in this context, but breaks in the continuity of data is NOT allowed, because that would both make the logic for comparing
    #data across multiple years much more complex and require detailed explanations in the dashboard, which there simply isn't room for in this context. Too much complexity will kill the usage of the dashboard.
    dfm = dfm.groupby([ 
        'Destinations', 
        'Definition', 
        'Market', 
        'Year'
    ]).filter(lambda x: (not x[ #Filter out destinations that DO NOT have valid data for January
        (x['Month'] == 1) &
        (
            (~x['Bed nights'].isna()) &
            (x['Bed nights'] > 0)
        )
        ].empty
    )).loc[lambda x: ( #Remove rows with no bednights data
        (
            (~x['Bed nights'].isna()) &
            (x['Bed nights'] > 0)
        )
    )].groupby([
        'Destinations', 
        'Definition', 
        'Market', 
        'Year'
    ]).filter(lambda x: ( #Ensure continuity in the dataseries
        x['Month'].nunique() == x['Month'].max()
    )).copy()

    dfm = dfm.loc[(~pd.isna(dfm['Bed nights']))].copy()

    #Monthly data is preffered due to design parameters for the dashboard that the data is used in. Yearly data is allowed IF monthly data is not available, which is the case sometimes.
    #Some destinations do not supply their own data and data for these destinations have therefore been estimated, but estimated data is only available in the API database at a yearly level.
    complete_cities = set(dfm['Destinations'].unique()) 
    dfy = dfy.loc[(~dfy['Destinations'].isin(complete_cities))].copy()

    dfm = pd.concat([df for df in [dfm, dfy] if not df.empty]) #dfy will be empty at times, because that contains yearly estimates for cities that do not supply their own data, but if those 
    #estimates have not been released yet, then dfy won't have any data.
    dfm['Bed nights'] = dfm['Bed nights'].astype(int)
    return(dfm)

def check_for_valid_seasons(dfm: pd.DataFrame) -> pd.DataFrame:
    '''
    Assigns a season value (winter, spring, summer, fall) to a subset of the data IF that subset contains valid data for all months in that given season.
    '''
    def assign_seasons(group):
        seasons = [{12,1,2}, {3,4,5}, {6,7,8}, {9,10,11}]
        mapping_dict = {}
        for i, season in enumerate(seasons):
            if season.issubset(group['Month'].values):
                if i == 0:
                    mapping_dict.update({12 : 'Winter', 1 : 'Winter', 2 : 'Winter'})
                elif i == 1:
                    mapping_dict.update({3 : 'Spring', 4 : 'Spring', 5 : 'Spring'})
                elif i == 2:
                    mapping_dict.update({6 : 'Summer', 7 : 'Summer', 8 : 'Summer'})
                elif i == 3:
                    mapping_dict.update({9 : 'Fall', 10 : 'Fall', 11 : 'Fall'})
        group['Season'] = group['Month'].map(mapping_dict)
        return(group)

    dfm = dfm.groupby([
        'Destinations', 
        'Definition', 
        'Market', 
        'Year'
    ]).apply(assign_seasons)

    dfm.reset_index(drop=True, inplace=True)
    return(dfm)

def add_city_classification(dfm: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds city classification, which is just a label based on the aggregate number of bednights or arrivals in a given destination in a given year.
    Destinations with >=2M bednights/arrival are assigned the "Premier League City" classification.
    Destinations with <2M bednights/arrival are assigned the "Second Division City" classification.
    '''
    city_classification = dfm.loc[(
        (dfm['Month'] != 99)
    )].groupby([
        'Destinations',
        'Definition', 
        'Market', 
        'Year'
    ])['Bed nights'].sum()

    city_classification = pd.DataFrame(city_classification)
    city_classification.reset_index(inplace=True, drop=False)
    city_classification = city_classification.loc[(city_classification['Bed nights'] >= 2000000) & (city_classification['Market'] == 'Total foreign and domestic')].copy()
    city_classification['City category'] = 'Premier League City'
    city_classification.drop(columns=['Bed nights', 'Market'], inplace=True)
    city_classification = dfm.merge(city_classification, on=['Destinations', 'Definition', 'Year'], how='left')
    city_classification['City category'] = city_classification['City category'].fillna('Second Division City')
    dfm = city_classification.copy()
    return(dfm)

def aggregate_seasonal_data(dfm: pd.DataFrame) -> pd.DataFrame:
    '''
    Calculates total bednights for the full year for destinations with valid data for all four seasons.
    '''
    seasons_check = dfm.loc[(
        (~dfm['Season'].isna())
    )].groupby([
        'Destinations',
        'Definition', 
        'Market', 
        'Year'
        ]).nunique()

    seasons_check.reset_index(inplace=True, drop=False)
    seasons_check = seasons_check[['Destinations', 'Definition', 'Market', 'Year', 'Season']]
    seasons_check.rename(columns = {'Season' : 'Unique seasons'}, inplace=True)
    seasons_check = dfm.merge(seasons_check, on=['Destinations', 'Definition', 'Market', 'Year'], how='inner')
    seasons_check = seasons_check.loc[(seasons_check['Unique seasons'] == 4)].copy() #Functionally equivalent to checking if a given subset has valid data for all 12 months, given that all seasons have been validated prior.
    seasons_check.drop(columns='Unique seasons', inplace=True)

    seasons_check = seasons_check.groupby([
        'Destinations',
        'Definition', 
        'Market', 
        'Year',
        'City category'
    ])[['Bed nights']].sum()

    seasons_check.reset_index(inplace=True, drop=False)

    seasons_check['Month'] = 99 #Remember that month 13 is reserved for cities with estimated yearly data. This aggregate needs a unique label because the dashboard has to be able to differentiate between the two yearly aggregates. Explained further in the measures.md file in the repo.
    seasons_check['Date'] = pd.to_datetime(seasons_check['Year'].astype(str) + '-01-01').dt.date
    seasons_check['Season'] = 'Full year'

    seasons_check = pd.concat([dfm, seasons_check], ignore_index=True)
    seasons_check['Date'] = pd.to_datetime(seasons_check['Date']).dt.date
    dfm = seasons_check.copy()

    conditions = [dfm['Month'].astype('int64') == 13]
    choices = ['Full year']
    dfm['Season'] = np.select(conditions, choices, default=dfm['Season']) #Adds the "Full year" label to the "Season" column for subsets with month 13 aggregated yearly values while maintaining the differentiated month value (13 / 99).
    return(dfm)

def add_geographic_coordinates(dfm: pd.DataFrame, df_geo: dict) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    '''
    Adds latitude and longitude for each destination.
    '''
    geolocator = Nominatim(user_agent="city_country_lookup")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    dfm['Country'] = dfm['Destinations'].map(lambda x: df_geo.get(x, {}).get('Country'))
    dfm['Latitude'] = dfm['Destinations'].map(lambda x: df_geo.get(x, {}).get('Latitude'))
    dfm['Longitude'] = dfm['Destinations'].map(lambda x: df_geo.get(x, {}).get('Longitude'))

    cities = list(dfm['Destinations'].loc[(dfm['Country'].isna())].unique())
    print(len(cities))

    results = {}
    for city in cities:
        if city == 'Salzburg (city)': #Looking up "Salzburg (city)" gives the coordinates for the wrong location (it returns a location in the US), 
            #but the "Salzburg (city)" name has to be preserved in the data to maintain consistency across different media presenting the same data.
            city = 'Salzburg'
            location = geocode(city, language="en")
            if location:
                country = location.raw.get("display_name", "").split(", ")[-1]
                latitude = location.latitude
                longitude = location.longitude
                results.update({'Salzburg (city)' : {
                    'Country' : country,
                    'Latitude' : latitude,
                    'Longitude' : longitude
                }})
            else:
                results.update({'Salzburg (city)' : {
                    'Country' : None,
                    'Latitude' : None,
                    'Longitude' : None
                }})
        else:
            location = geocode(city, language="en")
            if location:
                country = location.raw.get("display_name", "").split(", ")[-1]
                latitude = location.latitude
                longitude = location.longitude
                results.update({city : {
                    'Country' : country,
                    'Latitude' : latitude,
                    'Longitude' : longitude
                }})
            else:
                results.update({city : {
                    'Country' : None,
                    'Latitude' : None,
                    'Longitude' : None
                }})

    df_geo.update(results)

    df_geo = pd.DataFrame(df_geo).T
    df_geo.reset_index(inplace=True, drop=False)
    df_geo.rename(columns={'index' : 'Destinations'}, inplace=True)

    dfm['Country'] = dfm['Destinations'].map(lambda x: results.get(x, {}).get('Country')).fillna(dfm['Country'])
    dfm['Latitude'] = dfm['Destinations'].map(lambda x: results.get(x, {}).get('Latitude')).fillna(dfm['Latitude'])
    dfm['Longitude'] = dfm['Destinations'].map(lambda x: results.get(x, {}).get('Longitude')).fillna(dfm['Longitude'])
    dfm['Latitude'] = dfm['Latitude'].astype('float64')
    dfm['Longitude'] = dfm['Longitude'].astype('float64')
    return(dfm, df_geo, bool(cities))
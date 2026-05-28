from authentication import prepare_log_in_info, get_auth_token
from build_lookup_dicts import build_city_dict, build_market_dict, download_coordinates_dictionary, get_population_definitions
from upload_data import upload_coordinates_dictionary, upload_historical_bednights_table, append_new_data_to_bednights_table, upload_historical_population_table, append_new_data_to_population_table
from download_main_datasets import collect_main_data, get_population_data
from format_data_and_calculate_metrics import format_raw_data, filter_out_invalid_sets, check_for_valid_seasons, add_city_classification, aggregate_seasonal_data, add_geographic_coordinates

if __name__ == "__main__": #Only run functions IF the script is run directly, not if it's imported.
    print('Running all scripts.')
    #This entire pipeline is designed to be run in one go. Intermediate dictionaries and dataframes are only stored in memory and will be lost if the pipeline is interrupted.
    #If necessary, cache the dataframes at the marked points in the pipeline to preserve intermediate tables.
    username, password = prepare_log_in_info()
    token = get_auth_token(username, password)
    city_dict = build_city_dict(token)
    market_dict = build_market_dict(token)
    print('Collecting main data.')
    dfm = collect_main_data(city_dict, token, username, password) #Cache dfm after this step if you need a backup for iteration or testing purposes
    print('Main data collection done.')
    dfm = format_raw_data(dfm, market_dict, city_dict)
    dfm = filter_out_invalid_sets(dfm)
    dfm = check_for_valid_seasons(dfm)
    dfm = add_city_classification(dfm)
    dfm = aggregate_seasonal_data(dfm)
    df_geo = download_coordinates_dictionary()
    dfm, df_geo, has_new_cities = add_geographic_coordinates(dfm, df_geo)

    #If no new destination geographic data has been downloaded, there's no point re-uploading the lookup dictionary 
    #for geographic information. has_new_cities is a bool that checks if the list of destinations with newly pulled geographic information is longer than 0 or not.
    if has_new_cities:
        upload_coordinates_dictionary(df_geo)
    
    #ONLY run this function IF you're planning to create a completely new instance of the table with a full historical data pull OTHERWISE run the 
    #append_new_data_to_bednights_table() function to append new data to the existing table.
    #upload_historical_bednights_table(dfm)
    
    append_new_data_to_bednights_table(dfm)
    print('New bednights data uploaded.')
    pop_dict = get_population_definitions(city_dict)
    df_pop = get_population_data(username, password, token, pop_dict, city_dict) #Cache df_pop after this step if you need a backup for iteration or testing purposes
    
    #ONLY run this function IF you're planning to create a completely new instance of the table with a full historical data pull OTHERWISE run the 
    #append_new_data_to_population_table() function to append new data to the existing table.
    #upload_historical_population_table(df_pop)
    append_new_data_to_population_table(df_pop)
    print('New population data uploaded.')
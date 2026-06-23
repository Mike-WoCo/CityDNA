import requests as rq
import xml.etree.ElementTree as ET
import pandas as pd
from io import BytesIO
from authentication import prepare_log_in_info, get_auth_token
import time
from datetime import datetime

def collect_main_data(city_dict: dict, token: str, username: str, password: str) -> pd.DataFrame:
    '''
    This is the main data collection loop. 
    Use historical_year_set if historical data (2017 and onwards) needs to be recollected for whatever reason.
    Define a new variable for specific years, if, for instance, a destination goes back and updates XYZ specific years. In that case replace the city loop with just that city as well, otherwise this will pull A LOT of unnecessary
    rows and take much longer than necessary.
    Use year_set to just grab the most recent data which is what is most likely to have been adjusted since the last data pull. This heavily limits the amount of data requested from the API and, as a result of API thresholds,
    quite heavily limits the time it takes to pull that data.
    '''
    definition_set = ['N:A'] #The database work with different types of definitions for bednights (N) and arrivals (A). 
    #'N:A' just grabs the definition that each destinations has specified as their preferred definitions, which is both what's most likely to contain data and what's used in other applications of the data.

    current_year = datetime.now().year
    last_year = datetime.now().year - 1
    previous_year = datetime.now().year -2
    #historical_year_set = [i for i in range(2017, datetime.now().year + 1)]
    year_set = [previous_year, last_year, current_year] # USE THIS TO ONLY PULL DATA THAT HAS REALISTICALLY BEEN UPDATED SINCE THE LAST PULL

    collected_data_monthly = {
        'Destinations' : [],
        'Definition' : [],
        'Market' : [],
        'Year' : [],
        'Month' : [],
        'Bed nights' : []
    }

    break_all = False #Used in the retry logic. If 3 attempts to get data from the API fails for a specific combination of parameters, data collection is aborted. 
    #Has never been an issue, but stability issues with the API did cause it to drop connection every now and then at one point, so that's why this is here.
    for city in city_dict.keys():
            
        if break_all:
            break

        for year in year_set:
            if break_all:
                break

            for definition in definition_set:
                if break_all:
                    break

                for attempt in range(3):
                    try:
                        url = f'https://www.tourmis.info/api.pl?d={city}&c={definition}&m=*ECM&y={year}&token={token}'
                        result = rq.get(url)#session.get(url)

                        #Check if the token has expired and request a new token if that's the case
                        if any(token in result.content.decode('ISO-8859-1') for token in ['Token invalid', 'Token missing']) == True:
                            token = get_auth_token(username, password)       

                            url = f'https://www.tourmis.info/api.pl?d={city}&c={definition}&m=*ECM&y={year}&token={token}'
                            result = rq.get(url)

                        xml_data = result.content
                        xml_file_like = BytesIO(xml_data)
                        context = ET.iterparse(xml_file_like, events=('start', 'end'))

                        for event, elem in context:
                            if event == 'end' and elem.tag == 'data':
                                destination = elem.find('destination').text
                                market = elem.find('market').text
                                year_variable = elem.find('year').text
                                total_value = elem.find('value').text
                                definition = elem.find('content').text

                                #Grab yearly data values
                                collected_data_monthly['Destinations'].append(destination)
                                collected_data_monthly['Definition'].append(definition)
                                collected_data_monthly['Market'].append(market)
                                collected_data_monthly['Year'].append(year_variable)
                                collected_data_monthly['Month'].append('13') #The dashboard is primarily scoped for monthly data but allows yearly values if the time period is set to Jan.-Dec. Measure logic handles this.
                                collected_data_monthly['Bed nights'].append(total_value)

                                for value in elem.findall('value'): #Grab monthly data values
                                    month = value.get('month')
                                    if month:

                                        collected_data_monthly['Destinations'].append(destination)
                                        collected_data_monthly['Definition'].append(definition)
                                        collected_data_monthly['Market'].append(market)
                                        collected_data_monthly['Year'].append(year_variable)
                                        collected_data_monthly['Month'].append(month)
                                        collected_data_monthly['Bed nights'].append(value.text)

                        time.sleep(1.2) #Based on testing and API thresholds for the number of allowed requests per minute. Non-negotiable.
                        elem.clear()
                        break

                    except ConnectionError as e: #The API used to have connection issues that would result in random drops of the connection. Leaving this here just in case, but it doesn't seem to trigger much anymore. Seems the API stability has been drastically improved.

                        if attempt < 2:
                            print(f"Connection failed: {e}")
                            print("Waiting 5 minutes before trying again...")
                            #This cooldown might not be necessary anymore. It's a long cooldown because the API was VERY temperamental a while ago. It doesn't really seem to drop connections anymore,
                            #but it did it a lot at one point and needed some time to recover. Leaving this for now, since the exception doesn't seem to trigger anymore, but if it starts happening again,
                            #it'd be prudent to do some testing for how long of a timeout the API needs to recover. Last time I tested what cooldown duration would give me reproducible, successful data
                            #collection runs was mid-august 2025.
                            time.sleep(300)

                        else:
                            print('Connection failed 3 times. Aborting.')
                            break_all = True
                            break

                if break_all:
                    break

    dfm = pd.DataFrame(collected_data_monthly)
    return(dfm)

def get_population_data(username: str, password: str, token: str, pop_dict: dict, city_dict: dict) -> pd.DataFrame:
    '''
    Pulls the population data for each destination from the API and convert destinations names back to full names.
    '''
    current_year = datetime.now().year
    last_year = datetime.now().year - 1
    #historical_year_set = [i for i in range(2017, datetime.now().year + 1)]
    year_set = [last_year, current_year]

    population_data = {
        'Destination' : [],
        'Year' : [],
        'Date' : [],
        'Definition' : [],
        'Population' : []
    }

    break_all = False
    for city in pop_dict.keys():
        if break_all:
            break
            
        for year in year_set:
            break_range_attempts = False
            if break_all:
                break

            for attempt in range(3):
                if break_range_attempts == True:
                    break
                else:
                    try:
                        if break_all:
                            break
            
                        url = f'https://www.tourmis.info/api.pl?d={city}&c={pop_dict[city]}&y={year}&token={token}'
                        result = rq.get(url)
                    
                        #Check if the token has expired and request a new token if that's the case
                        if any(token in result.content.decode('ISO-8859-1') for token in ['Token invalid', 'Token missing']) == True:
                            token = get_auth_token(username, password)        
                            
                            url = f'https://www.tourmis.info/api.pl?d={city}&c={pop_dict[city]}&y={year}&token={token}'
                            result = rq.get(url)
                    
                        xml_data = result.content
                        
                        root = ET.fromstring(xml_data)
                        
                        for data in root.findall(".//alldata/data"):
                            value = data.find("value").text #Population value
                        
                            population_data['Destination'].append(city)
                            population_data['Year'].append(year)
                            population_data['Date'].append(pd.to_datetime(str('1-1-'+str(year)), dayfirst = True).date())
                            population_data['Definition'].append('Bed nights - preferred definition')
                            population_data['Population'].append(int(value))

                            population_data['Destination'].append(city)
                            population_data['Year'].append(year)
                            population_data['Date'].append(pd.to_datetime(str('1-1-'+str(year)), dayfirst = True).date())
                            population_data['Definition'].append('Arrivals - preferred definition')
                            population_data['Population'].append(int(value))
            
                        time.sleep(1) #Necessary due to API thresholds.
                        break_range_attempts = True
            
                    except ConnectionError as e:
                        if attempt < 2:
                            print(f"Connection failed: {e}")
                            print("Waiting 30 seconds before trying again...")
                            time.sleep(30)

                        else:
                            print('Connection failed 3 times. Aborting.')
                            break_all = True
                            break
                            
                    except Exception as e:
                        break_range_attempts = True
                        
    df_pop = pd.DataFrame(population_data)
    df_pop['Destination'] = df_pop['Destination'].map(city_dict) #Convert destination names back to full names from shorthand names.
    return(df_pop)
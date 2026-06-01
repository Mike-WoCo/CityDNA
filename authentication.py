import requests as rq
import json
from google.cloud import secretmanager
import json

def prepare_log_in_info() -> tuple[str, str]:
    """
    Loads login credentials from a local JSON config file.
    Switch to environmental variables if moving to a cloud VM or docker.
    """
    client = secretmanager.SecretManagerServiceClient()

    project_id = "citydna-dashboard-x"
    secret_id = "TourMIS"
    parent = f"projects/{project_id}"

    response = client.access_secret_version(
        request={"name": f"projects/{project_id}/secrets/{secret_id}/versions/latest"}
    )

    payload = response.payload.data.decode("UTF-8")
    payload = json.loads(payload)

    username = payload['username']
    password = payload['password']
    return(username, password)

def get_auth_token(username: str, password: str) -> str:
    '''
    Get an auth token. Note: This is how the API is designed. It expects the username and password as url parameters.
    '''
    url = f'https://www.tourmis.info/api.pl?id={username}&pw={password}'
    result = rq.get(url)
    token = result.content.decode('ISO-8859-1').split('<token>')[1].split('</token>')[0]
    return(token)
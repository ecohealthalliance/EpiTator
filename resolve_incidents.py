import requests
import json

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--eidr_url", default='https://eidr-connect.eha.io'
    )
    args = parser.parse_args()

    for annotator_name in ['count_annotator', 'infection_annotator']:
        incidents_for_disease = []
        formatted_incidents = []
        with open("incidents_from_" + annotator_name + ".json") as f:
            formatted_incidents = json.load(f)

        for incident in formatted_incidents:
            if 'cases' in incident and incident.get('resolvedDisease', {}).get('id') == 'https://www.wikidata.org/wiki/Q16654806':
                incidents_for_disease.append(incident)

        response = requests.post(args.eidr_url + '/api/resolve-incidents', json={
            'incidents': incidents_for_disease,
            'constrainingIncidents': [
                #{
                #    'type': 'caseCount',
                #    'cases': 10,
                #    'constraining': True,
                #    'dateRange': {
                #        'start': datetime.datetime(2014, 11, 1).strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                #        'end': datetime.datetime(2014, 12, 1).strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                #        "cumulative": False
                #    },
                #    "resolvedDisease": {
                #        "label": "Middle East respiratory syndrome",
                #        "type": "disease",
                #        "id": "https://www.wikidata.org/wiki/Q16654806"
                #    },
                #    'locations': [
                #        {
                #            "name": "Kingdom of Saudi Arabia",
                #            "countryName": "Kingdom of Saudi Arabia",
                #            "featureCode": "PCLI",
                #            "admin1Code": "00",
                #            "population": 25731776,
                #            "asciiname": "Kingdom of Saudi Arabia",
                #            "latitude": 25.0,
                #            "admin3Code": "",
                #            "admin2Code": "",
                #            "admin4Code": "",
                #            "countryCode": "SA",
                #            "namesUsed": "Saudi;Saudi Arabia",
                #            "nameCount": 171,
                #            "id": "102358",
                #            "longitude": 45.0
                #        }
                #    ]
                #}
            ]
        })
        if response.status_code != 200:
            print("Error message:")
            print(response.content)
            response.raise_for_status()
        resonpose_json = response.json()

        with open("resolved_incidents_from_" + annotator_name + ".json", "w") as f:
            json.dump(resonpose_json, f, indent=4)

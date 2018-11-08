from epitator.annodoc import AnnoDoc
from epitator.infection_annotator import InfectionAnnotator
from epitator.incident_annotator import IncidentAnnotator
from epitator.count_annotator import CountAnnotator
import pandas
import pymongo
import requests
import jsondiff
import json
import datetime


def format_incident_spans(incident_spans):
    formatted_incidents = []
    for span in incident_spans:
        incident_type = span.metadata["type"]
        incident_value = span.metadata["value"]
        formatted_incident = {}
        if "case" in incident_type.lower():
            formatted_incident["cases"] = incident_value
        elif "death" in incident_type.lower():
            formatted_incident["deaths"] = incident_value
        else:
            continue
        formatted_incident["dateRange"] = {
            "start": span.metadata["dateRange"][0].strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
            "end": span.metadata["dateRange"][1].strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
            "cumulative": "cumulative" in incident_type
        }
        formatted_incident["locations"] = span.metadata["locations"]
        if "resolvedDisease" in span.metadata:
            formatted_incident["resolvedDisease"] = span.metadata["resolvedDisease"]
        formatted_incidents.append(formatted_incident)
    return formatted_incidents


def pretty_print_dict(d):
    print("{")
    for key, value in d.items():
        print("\t" + key + ":")
        print("\t" + str(value)[:100])
    print("}")


def pretty_print_diff(a, b):
    diff_data = jsondiff.diff(a, b, syntax='symmetric')
    differing_items = 0
    if isinstance(diff_data, dict):
        for k, v in diff_data.items():
            if str(k) == "$insert":
                print("\nInserted:")
                differing_items += len(v)
                for idx, value in v:
                    pretty_print_dict(value)
            elif str(k) == "$delete":
                print("\nRemoved:")
                differing_items += len(v)
                for idx, value in v:
                    pretty_print_dict(value)
            elif str(k) == "$update":
                print("\nChanged:")
                differing_items += len(v)
                for idx, value in v:
                    pretty_print_dict(a[idx])
                    print(value)
            else:
                differing_items += 1
                print("\nChanged:")
                pretty_print_dict(a[k])
                print(v)
    else:
        print("Array diff")
        differing_items += len(diff_data[0])
    print("Differing elements:", differing_items)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mongo_url", default='localhost'
    )
    parser.add_argument(
        "--db_name", default='promed'
    )
    parser.add_argument(
        "--eidr_url", default='https://eidr-connect.eha.io'
    )
    args = parser.parse_args()
    db = pymongo.MongoClient(args.mongo_url)[args.db_name]
    formatted_incidents_by_annotator = dict(
        count_annotator = [],
        infection_annotator = []
    )
    posts = list(db.posts.find({
        "subject.diseaseLabels": "MERS",
        "feedId": "1",
        "$and": [
            {
                "promedDate": { "$gt": datetime.datetime(2013,1,1) }
            },
            {
                "promedDate": { "$lt": datetime.datetime(2015,1,1) }
            }
        ]
    }))
    print("Posts:", len(posts))
    for post in posts:
        print(post['subject']['raw'])
        print("http://www.promedmail.org/post/" + post['promedId'])
        doc = AnnoDoc(post["content"], date=post["promedDate"])
        case_counts = doc.require_tiers("counts", via=CountAnnotator)
        incident_spans_from_count_annotator = doc.require_tiers("incidents", via=IncidentAnnotator)
        infection_counts = doc.require_tiers('infections', via=InfectionAnnotator)
        attribute_remappings = {
            'infection': 'case'
        }
        for span in infection_counts:
            span.metadata['attributes'] = [
                attribute_remappings.get(attribute, attribute)
                for attribute in span.metadata['attributes']]
        doc.add_tier(IncidentAnnotator(), case_counts=infection_counts)
        incident_spans_from_infection_annotator = doc.tiers['incidents']
        print("Number of counts:", len(case_counts), ",", len(infection_counts))
        new_formatted_incidents_from_count_annotator = format_incident_spans(incident_spans_from_count_annotator)
        new_formatted_incidents_from_infection_annotator = format_incident_spans(incident_spans_from_infection_annotator)
        print("Number of incidents:", len(new_formatted_incidents_from_count_annotator), ",", len(new_formatted_incidents_from_infection_annotator))
        # Print base counts for each incident
        # for span, group in infection_counts.group_spans_by_containing_span(incident_spans_from_infection_annotator, allow_partial_containment=True):
        #     print(span)
        #     for incident in group:
        #         if span in incident.base_spans:
        #             pretty_print_dict(format_incident_spans([incident])[0])
        # pretty_print_diff(new_formatted_incidents_from_count_annotator, new_formatted_incidents_from_infection_annotator)
        for incident_span in incident_spans_from_infection_annotator:
            metadata = incident_span.metadata
            if metadata['type'] != "caseCount": continue
            if not metadata.get('duration'): continue
            if metadata['value'] / metadata['duration'] < 25: continue
            if metadata.get('resolvedDisease', {}).get('id') != 'https://www.wikidata.org/wiki/Q16654806': continue
            if metadata.get('locations', [{}])[0].get('name') != "Kingdom of Saudi Arabia": continue
            print("Outlier Detected")
        formatted_incidents_by_annotator['count_annotator'] += new_formatted_incidents_from_count_annotator
        formatted_incidents_by_annotator['infection_annotator'] += new_formatted_incidents_from_infection_annotator
    for annotator_name, formatted_incidents in formatted_incidents_by_annotator.items():
        with open("incidents_from_" + annotator_name + ".json", "w") as f:
            json.dump(formatted_incidents, f, indent=4)
        incidents_for_disease = []
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

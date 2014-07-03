#!/usr/bin/env python
"""Score """

import glob

import sys
sys.path.append('/Users/russ/eha/projects/grits-api/')
sys.path.append('/Users/russ/eha/projects/geonote/')
sys.path.append('/Users/russ/eha/projects/geonote/annotator')

import sklearn

from diagnosis.LocationExtractor import *
from corpora.iterate_resources import *
from geonames_api import get_wikipedia_title_or_fallback
from annotator.annotator import *
from annotator.geoname_human_tag_annotator import GeonameHumanTagAnnotator
from annotator.geoname_annotator import GeonameAnnotator


def score_LocationExtraction():

	location_extractor = LocationExtractor()
	gold_geotag_annotator = GeonameHumanTagAnnotator()
	geoname_annotator = GeonameAnnotator()

	gold_directory = '/Users/russ/eha/projects/geonote/annotated_data/'
	gold_files = glob.glob(gold_directory + '*.md')

	all_gold_locations = []
	all_le_locations = []
	all_ga_locations = []

	le_tps = 0 # locations tagged and gold
	le_fps = 0 # locations tagged and not gold
	le_tns = 0 # locations not tagged and not gold
	le_fns = 0 # locationed not tagged and gold

	ga_tps = 0 # locations tagged and gold
	ga_fps = 0 # locations tagged and not gold
	ga_tns = 0 # locations not tagged and not gold
	ga_fns = 0 # locationed not tagged and gold

	i = 1
	for gold_file in gold_files:

		processed = process_resource_file(gold_file)
		le_res = location_extractor.transform_one(processed['content'])

		print processed['content']

		doc = AnnoDoc(unicode(processed['content'], 'utf8', 'ignore'))
		print "Annotating gold..."
		doc.add_tier(gold_geotag_annotator)
		print "Annotating geonames..."
		doc.add_tier(geoname_annotator)

		gold_locations = [span.label
		                  for span in doc.tiers['gold_geonames'].spans]
		all_gold_locations += gold_locations
		

		ga_locations = [span.label
		                for span in doc.tiers['geonames'].spans]
		all_ga_locations += ga_locations

		

		le_locations = [location['name']
						for cluster in le_res
		 				for location in cluster['locations']]
		all_le_locations += le_locations
		
		print 'gold_locations:', gold_locations
		print 'le_locations:', le_locations
		print 'ga_locations:', ga_locations

		le_tp_locations = set(gold_locations).intersection(set(le_locations))
		le_fp_locations = set(le_locations).difference(set(gold_locations))
		le_fn_locations = set(gold_locations).difference(set(le_locations))

		le_tps += len(le_tp_locations)
		le_fps += len(le_fp_locations)
		le_fns += len(le_fn_locations)

		ga_tp_locations = set(gold_locations).intersection(set(ga_locations))
		ga_fp_locations = set(ga_locations).difference(set(gold_locations))
		ga_fn_locations = set(gold_locations).difference(set(ga_locations))

		ga_tps += len(ga_tp_locations)
		ga_fps += len(ga_fp_locations)
		ga_fns += len(ga_fn_locations)

		print 'le_tp_locations:', le_tp_locations
		print 'le_fp_locations:', le_fp_locations
		print 'le_fn_locations:', le_fn_locations
		print 'ga_tp_locations:', ga_tp_locations
		print 'ga_fp_locations:', ga_fp_locations
		print 'ga_fn_locations:', ga_fn_locations
		
		print
		print
		print

	print 'le_TPs:', le_tps
	print 'le_FPs:', le_fps
	print 'le_FNs:', le_fns
	print 'ga_TPs:', ga_tps
	print 'ga_FPs:', ga_fps
	print 'ga_FNs:', ga_fns




if __name__ == '__main__':
	score_LocationExtraction()
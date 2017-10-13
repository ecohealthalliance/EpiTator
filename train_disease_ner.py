#!/usr/bin/env python
# coding: utf8
"""
This script trains a new SpaCy NER model that recognizes disease names.
It is designed to connect to our ProMED-mail mongo database to download text to be used as training data.
Since this database is private, external users will probably need to find another source of training data.
The training data is not human annotated. Instead, the this script will use the EpiTator resolved disease annotator
to annotate disease names by matching them to a known set of names.
The resulting model's precision will inevitably be worse than the resolved disease annotator's,
however it may be able to identify some previously unseen disease names that would not be
possible to catch with a purely dictionary based approach.
An --output_directory parameter can be supplied to indicate where the model should be saved to.
This script will also create some evaluation data in the same manner as the training data and print out
statistics on the number of true/false positives/negatives.

Results from the current parameters:

    tps: 171
    fns: 11
    fps: 6
    Potential false positive: Avian paramyxovirus
    Potential false positive: Dumfries
    Potential false positive: yellow alert
    Potential false positive: yellow alert
    Potential false positive: bird's
    Potential false positive: African horse

To use the new disease name NER model with EpiTator:

>>> import spacy
>>> from epitator.spacy_annotator import SpacyAnnotator
>>> spacy_nlp = spacy.load('en', path=output_directory) # use the same output_directory this script was invoked with.
>>> spacy_nlp.entity.add_label('DISEASE')
>>> doc.add_tiers(SpacyAnnotator(spacy_nlp))
>>> doc.tiers["spacy.nes"].with_label('DISEASE')
"""
from __future__ import print_function
from pathlib import Path
import random
import spacy
from spacy.gold import GoldParse
import pymongo
import argparse
from epitator.annotator import AnnoDoc, AnnoTier, AnnoSpan
from epitator.resolved_keyword_annotator import ResolvedKeywordAnnotator
from epitator.spacy_annotator import SpacyAnnotator
import datetime


NUM_TRAIN_POSTS = 450
NUM_TEST_POSTS = 50


# Based on the train_ner function in the
# Spacy example here: https://github.com/explosion/spaCy/blob/master/examples/training/train_new_entity_type.py
def train_ner(nlp, train_data, output_dir):
    # Add new words to vocab
    for raw_text, _ in train_data:
        doc = nlp.make_doc(raw_text)
        for word in doc:
            _ = nlp.vocab[word.orth]
    random.seed(0)
    # You may need to change the learning rate. It's generally difficult to
    # guess what rate you should set, especially when you have limited data.
    nlp.entity.model.learn_rate = 0.01
    for itn in range(200):
        random.shuffle(train_data)
        loss = 0.
        for raw_text, entity_offsets in train_data:
            doc = nlp.make_doc(raw_text)
            gold = GoldParse(doc, entities=entity_offsets)
            nlp.tagger(doc)
            # As of 1.9, spaCy's parser now lets you supply a dropout probability
            # This might help the model generalize better from only a few
            # examples.
            loss += nlp.entity.update(doc, gold, drop=0.5)
        if loss == 0:
            break
    # This step averages the model's weights. This may or may not be good for
    # your situation --- it's empirical.
    nlp.end_training()
    if output_dir:
        if not output_dir.exists():
            output_dir.mkdir()
        nlp.save_to_directory(output_dir)
    return nlp

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mongo_url", default='localhost'
    )
    parser.add_argument(
        "--db_name", default='promed'
    )
    parser.add_argument(
        "--output_directory"
    )
    args = parser.parse_args()

    db = pymongo.MongoClient(args.mongo_url)[args.db_name]

    output_directory = None
    if args.output_directory is not None:
        output_directory = Path(args.output_directory)

    annotator = ResolvedKeywordAnnotator()
    spacy_annotator = SpacyAnnotator()
    base_model_name = "en_core_web_sm"
    nlp = spacy.load(base_model_name)
    training_data = []

    query = {
        "promedDate": { "$gt": datetime.datetime(2010,1,1)},
        "articles": { "$not": {"$size": 0}}}
    for post in db.posts.find(query, {'articles': 1}).limit(NUM_TRAIN_POSTS):
        for art in post.get("articles", []):
            if "content" in art:
                spacy_doc = nlp(art['content'])
                for sent in spacy_doc.sents:
                    doc = AnnoDoc(sent.text)
                    try:
                        doc.add_tier(annotator)
                        doc.add_tier(spacy_annotator)
                    except ValueError as e:
                        print("Exception occured during annotation of article:")
                        print(art)
                        print("Skipping post")
                        print("promedId:", post["promedId"])
                        break
                    dis_kw_annos = AnnoTier([AnnoSpan(span.start, span.end, doc, 'DISEASE')
                                             for span in doc.tiers['resolved_keywords'].spans
                                             if span.resolutions[0]['entity']['type'] == 'disease'])
                    spacy_annos = doc.tiers['spacy.nes']
                    dis_kw_annos.without_overlaps(spacy_annos)
                    annotations = spacy_annos.without_overlaps(dis_kw_annos) + dis_kw_annos
                    training_data.append((doc.text, [(span.start, span.end, span.label)
                                                     for span in annotations.spans],))
    print("Training data ready.")
    nlp.entity.add_label('DISEASE')
    nlp = train_ner(nlp, training_data, output_directory)
    print("Training complete")
    # Test that the entity is recognized against resolved disease annotations
    tps = 0
    fps = 0
    fns = 0
    for post in db.posts.find(query).skip(NUM_TRAIN_POSTS).limit(NUM_TEST_POSTS):
        for art in post.get("articles", []):
            if "content" in art:
                doc = AnnoDoc(art['content'])
                try:
                    doc.add_tier(annotator)
                    doc.add_tier(SpacyAnnotator(nlp))
                except ValueError as e:
                    print("Exception occured during annotation of article:")
                    print(art)
                    print("Skipping post")
                    print("promedId:", post["promedId"])
                    break
                spacy_doc = nlp(art['content'])
                dis_kw_annos = AnnoTier([AnnoSpan(span.start, span.end, doc, 'DISEASE')
                                         for span in doc.tiers['resolved_keywords'].spans
                                         if span.resolutions[0]['entity']['type'] == 'disease'])
                grouped_spans = dis_kw_annos.group_spans_by_containing_span(
                    doc.tiers['spacy.nes'].with_label('DISEASE'),
                    allow_partial_containment=True)
                for dis_kw_span, spacy_ne_spans in grouped_spans:
                    if len(spacy_ne_spans) == 0:
                        #print("Missed:", dis_kw_span.text)
                        fns += 1
                    else:
                        tps += 1

                grouped_spans = doc.tiers['spacy.nes'].with_label('DISEASE').group_spans_by_containing_span(
                    dis_kw_annos,
                    allow_partial_containment=True)
                for spacy_ne_span, dis_kw_spans in grouped_spans:
                    if len(dis_kw_spans) == 0:
                        print("Potential false positive:", spacy_ne_span.text)
                        fps += 1

    print("tps:", tps)
    print("fns:", fns)
    print("fps:", fps)


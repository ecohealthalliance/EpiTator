# Annie the annotator

Infrastructure to store linguistic annotations.

# GeonameAnnotator

The geoname annotator requires the geonames.org dataset to be downloaded and
imported into a mongo database. Run `import_geonames.sh` to the do the import.
Here are some [instructions](http://docs.mongodb.org/manual/tutorial/install-mongodb-on-linux/)
for installing Mongo.

# JVM-NLP

The jvm_nl_annotator relies on a server from this project:

https://github.com/ecohealthalliance/jvm-nlp

Why aren't we using a Swagger-generated client? It doesn't handle Maps very well.

https://github.com/wordnik/swagger-spec/issues/38

# TODO

* docs
* update and re-enable tests
* requirements.txt
* separate EHA-internal annotators from general annotators
* make token annotator raise errors if unexpected characters need to be consumed

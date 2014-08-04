# Annie the annotator

Infrastructure to store linguistic annotations.

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

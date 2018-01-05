from __future__ import print_function
import sys
import doctest
if __name__ == "__main__":
    raise_on_error = True
    try:
        import epitator.annotier
        doctest.testmod(epitator.annotier, raise_on_error=raise_on_error)
        import epitator.annospan
        doctest.testmod(epitator.annospan, raise_on_error=raise_on_error)
        import epitator.annodoc
        doctest.testmod(epitator.annodoc, raise_on_error=raise_on_error)
    except doctest.UnexpectedException as e:
        print("Failed example:")
        print(e.example.lineno, ":", e.example.source)
        print(e.exc_info)
        sys.exit(1)
    except doctest.DocTestFailure as e:
        print("Failed example:")
        print(e.example.lineno, ":", e.example.source)
        print("Expected:", e.example.want)
        print("Got:", e.got)
        sys.exit(1)

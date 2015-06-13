
GIT_VERSION:=$(shell git describe --tags --dirty=M)

all: sdist
	echo "__VERSION__='$(GIT_VERSION)'" > swingtix/bookkeeper/__init__.py

version: 
	echo "__VERSION__='$(GIT_VERSION)'" > swingtix/bookkeeper/__init__.py

test: version
	python -Wall ./manage.py test swingtix.bookkeeper

.coverage: test
	coverage run --source=swingtix ./manage.py test swingtix.bookkeeper

coverage.xml: .coverage
	coverage xml -o coverage.xml

sdist: version
	python setup.py sdist
    

clean:
	rm -f .coverage coverage.xml
	rm -Rf *.egg-info htmlcov build dist

.PHONY: all version


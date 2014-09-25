
GIT_VERSION:=$(shell git describe --tags --dirty=M)

all: sdist
	echo "__VERSION__='$(GIT_VERSION)'" > swingtix/bookkeeper/__init__.py

version: 
	echo "__VERSION__='$(GIT_VERSION)'" > swingtix/bookkeeper/__init__.py

test: test_latest

all_tests: test_latest test_previous test_lts

test_latest: version env.dj_latest
	PATH=env.dj_latest/bin:${PATH}   python -Wall ./manage.py test swingtix.bookkeeper

test_previous: version env.dj_previous
	PATH=env.dj_previous/bin:${PATH} python -Wall ./manage.py test swingtix.bookkeeper

test_lts: version env.dj_lts
	PATH=env.dj_lts/bin:${PATH}      python -Wall ./manage.py test bookkeeper

.coverage: test env.dj_latest
	PATH=env.dj_latest/bin:${PATH} coverage run --source=swingtix ./manage.py test swingtix.bookkeeper

coverage.xml: .coverage env.dj_latest
	PATH=env.dj_latest/bin:${PATH} coverage xml -o coverage.xml

sdist: version
	python setup.py sdist
    

clean:
	rm -f .coverage coverage.xml
	rm -Rf *.egg-info htmlcov build dist
	rm -Rf env.dj_latest
	rm -Rf env.dj_previous
	rm -Rf env.dj_lts

env.dj_latest:
	virtualenv --no-site-packages $@
	PATH=$@/bin:${PATH} pip install -r tests/requirements_latest.txt

env.dj_previous:
	virtualenv --no-site-packages $@
	PATH=$@/bin:${PATH} pip install -r tests/requirements_previous.txt

env.dj_lts:
	virtualenv --no-site-packages $@
	PATH=$@/bin:${PATH} pip install -r tests/requirements_lts.txt

.PHONY: all version


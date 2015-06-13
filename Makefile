
GIT_VERSION:=$(shell git describe --tags --dirty=M)

all: sdist
	echo "__VERSION__='$(GIT_VERSION)'" > swingtix/bookkeeper/__init__.py

version: 
	echo "__VERSION__='$(GIT_VERSION)'" > swingtix/bookkeeper/__init__.py

test: test_latest

all_tests: test_latest test_previous test_lts

test_latest: version .env.dj_latest
	PATH=.env.dj_latest/bin:${PATH}   python -Wall ./manage.py test swingtix.bookkeeper

test_previous: version .env.dj_previous
	PATH=.env.dj_previous/bin:${PATH} python -Wall ./manage.py test swingtix.bookkeeper

test_lts: version .env.dj_lts
	PATH=.env.dj_lts/bin:${PATH}      python -Wall ./manage.py test swingtix.bookkeeper

.coverage: test .env.dj_latest
	PATH=.env.dj_latest/bin:${PATH} coverage run --source=swingtix ./manage.py test swingtix.bookkeeper

#jenkins, etc.
unit_coverage.xml: .coverage .env.dj_latest
	PATH=.env.dj_latest/bin:${PATH} coverage xml -o $@

#Go/html
unit_coverage_html: .coverage .env.dj_latest
	PATH=.env.dj_latest/bin:${PATH} coverage html -d $@

lint:
	pylint swingtix/bookkeeper

#human
coverage: .coverage
	PATH=.env.dj_latest/bin:${PATH} coverage report

sdist: version
	python setup.py sdist
    
#everything except python environments
clean:
	rm -Rf .coverage unit_coverage.xml unit_coverage_html
	rm -Rf *.egg-info htmlcov build dist

fullclean: clean
	rm -Rf .env.dj_latest
	rm -Rf .env.dj_previous
	rm -Rf .env.dj_lts

.env.dj_%: tests/requirements_%.txt
	virtualenv --no-site-packages $@
	PATH=$@/bin:${PATH} pip install -r $<


.PHONY: all version coverage clean fullclean


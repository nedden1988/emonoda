all :
	true

regen : regen-fetchers

regen-fetchers :
	python -c '\
			import json, rtlib.fetchers; \
			print(json.dumps({ \
					item.plugin() : { \
							"version" : item.version(), \
							"path" : item.__module__.replace(".", "/") + ".py", \
						} \
					for item in rtlib.fetchers.FETCHERS_MAP.values() \
				}, sort_keys=True, indent="    ")) \
		' > fetchers.json

pylint :
	pylint --rcfile=pylint.ini \
		rtlib \
		*.py \
		--output-format=colorized 2>&1 | less -SR

clean :
	find . -type f -name '*.pyc' -exec rm '{}' \;
	rm -rf pkg-root.arch pkg src build rtfetch.egg-info


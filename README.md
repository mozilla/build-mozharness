# Mozharness
This repository is a downstream read-only copy of:
http://hg.mozilla.org/build/mozharness/

To submit a patch, please create a Mozharness bug under:
https://bugzilla.mozilla.org/enter_bug.cgi?product=Release%20Engineering&component=Mozharness

General information about Mozharness:
* https://developer.mozilla.org/en-US/docs/Mozharness_FAQ
* https://wiki.mozilla.org/ReleaseEngineering/Mozharness
* http://moz-releng-mozharness.readthedocs.org/en/latest/mozharness.mozilla.html
* http://moz-releng-docs.readthedocs.org/en/latest/software.html#mozharness

To run mozharness unit tests:
```
pip install tox
tox
```

Please note if you fork this repository and wish to run the tests in travis,
you will need to enable your github fork in both travis and coveralls. In both
cases you can log in with your github account, you do not need to set up a new
one. To enable:
* https://travis-ci.org/profile
* https://coveralls.io/repos/new

Happy contributing! =)

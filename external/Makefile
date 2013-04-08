CWD = $(shell pwd)
PROJECT_ROOT = $(CWD)/..
EXTERNAL_ROOT = $(CWD)
VIRTENV = $(EXTERNAL_ROOT)/virtenv
PIP = $(VIRTENV)/bin/pip
DESTDIR = $(EXTERNAL_ROOT)/ephemvpn-extras


all: install-deps package zip

${VIRTENV}/bin/activate:
	virtualenv --no-site-packages $(VIRTENV)

install-deps: ${VIRTENV}/bin/activate
	$(PIP) install -e ephemvpn/

package:
	mkdir -p $(DESTDIR)/libs && \
	cp -r virtenv/lib/python2.7/site-packages/* $(DESTDIR)/libs/ && \
	rm -rf $(DESTDIR)/libs/pip* && \
	rm -rf $(DESTDIR)/libs/pycrypto* && \
	rm -rf $(DESTDIR)/libs/Crypto* && \
	rm -rf $(DESTDIR)/libs/ephemvpn.egg-link && \
	cp -r ephemvpn/ephemvpn $(DESTDIR)/libs/ && \
	cp ephemvpn_android.py $(DESTDIR)

zip:
	cd $(DESTDIR) && \
	zip ../ephemvpn_bundle.zip  -r .


distclean:
	rm -rf $(DESTDIR) $(VIRTENV) ephemvpn_bundle.zip

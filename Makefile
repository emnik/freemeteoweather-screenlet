SYSTEM_SCREENLETS_DIR = $(DESTDIR)/usr/share/screenlets
XDG_DESKTOP_FILES_DIR = $(DESTDIR)/usr/share/applications/screenlets

install:
	mkdir -p $(SYSTEM_SCREENLETS_DIR)
	cp -r screenlet/* $(SYSTEM_SCREENLETS_DIR)
	mkdir -p $(XDG_DESKTOP_FILES_DIR)
	cp -r xdg-desktop/* $(XDG_DESKTOP_FILES_DIR)
	for file in $$(ls -1 po/); do mkdir -p $(DESTDIR)/usr/share/locale/$${file%.po}/LC_MESSAGES; msgfmt -v -o $(DESTDIR)/usr/share/locale/$${file%.po}/LC_MESSAGES/freemeteoweather-screenlet.mo po/$$file; done
import gettext
from io import BytesIO
import logging
import os
import re
import time

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

import chameleon

from webob.static import DirectoryApp

log = logging.getLogger(__name__)

NAME_RE = r"[a-zA-Z][-a-zA-Z0-9_]*"

_interp_regex = re.compile(r'(?<!\$)(\$(?:({n})|{{({n})}}))'.format(n=NAME_RE))


def get_languages_from_locale(locale):
    """The languages this locale supports.

    From least to most specific.
    """
    languages = []
    if locale:
        if '_' in locale:
            languages.append(locale.split('_')[0])
        languages.append(locale)
    return tuple(languages)


# TODO allow for static localized files.
class LocaleApp(DirectoryApp):

    _initialized = False
    locales = {}
    templatedir = localedir = tempdir = use_fuzzy = _kw = None
    known_locales = {'en_US': get_languages_from_locale('en_US')}

    @classmethod
    def initialize(cls, templatedir, localedir, tempdir,
                   use_fuzzy=False, **kw):
        if not cls._initialized:
            cls.templatedir = os.path.abspath(templatedir)
            cls.localedir = os.path.abspath(localedir)
            cls._tempdir = os.path.abspath(tempdir)
            cls.use_fuzzy = use_fuzzy
            cls._kw = kw
            cls._initialized = True
            for entry in os.scandir(cls.localedir):
                if entry.is_dir():
                    cls.known_locales[entry.name] = \
                        get_languages_from_locale(entry.name)

    @classmethod
    def get_app(cls, locale):
        locale = locale or ''
        locale = locale.replace('-', '_')
        log.debug('Getting locale for %s', locale)
        if locale not in cls.locales:
            log.debug('Can\'t find locale %s in dict', locale)
            cls.locales[locale] = cls(locale)
        else:
            log.debug('Loading %s from dict', locale)
        return cls.locales[locale]

    def __init__(self, locale):
        if not self._initialized:
            raise RuntimeError('Must Initialize LocaleApp before '
                               'creating an intance.')
        self.locale = locale
        self.outdir = os.path.join(self._tempdir, self.locale)
        self._mtime = {}
        self._pofiles = {}
        self.languages = get_languages_from_locale(self.locale)
        if self.locale:
            os.mkdir(self.outdir, mode=0o700)
            self.templatedir = os.path.join(self.templatedir, '_locale')
        super().__init__(self.templatedir, **self._kw)

    def is_dirty(self, path):
        current_mtime = self.get_real_mtime(path)
        mtime = self._mtime.get(path, 0)
        log.debug('Current mtime %s, original mtime %s.', current_mtime,
                  mtime)
        if current_mtime > mtime:
            self._mtime[path] = current_mtime
            return True
        return False

    def get_real_mtime(self, path):
        mtime = os.path.getmtime(path)
        log.debug('File "%s" mtime: %s', path, mtime)
        for pofile in self.get_pofiles(path):
            mtime = max(mtime, os.path.getmtime(pofile))
        return mtime

    def bust_cache(self, bust_time=None):
        if bust_time is None:
            bust_time = time.time()
        utime = (bust_time, bust_time)
        log.debug('Busting cache, bust time: %s', bust_time)
        for path in self._mtime:
            if os.path.getmtime(path) < bust_time:
                os.utime(path, utime)

    def make_fileapp(self, path):
        log.debug('Getting path: %s for locale %s', path, self.locale)
        if self.is_dirty(path):
            log.debug('File is dirty, reloading translation.')
            self.reload_translations(path)
        return super().make_fileapp(self.get_outpath(path))

    def get_pofiles(self, path):
        """Get pofiles for this path.

        We get the file in order of least to most specific.
        """
        if not self.locale:
            return []
        if path not in self._pofiles:
            log.debug('Finding .po files for path %s and locale %s',
                      path, self.locale)
            pofiles = []
            domain = os.path.splitext(self._get_relpath(path))[0]
            log.debug('Template %s has domain %s', path, domain)
            for lang in self.languages:
                pofile = os.path.join(self.localedir, lang, 'LC_MESSAGES',
                                      '{}.po'.format(domain))
                if os.path.exists(pofile):
                    pofiles.append(pofile)
            self._pofiles[path] = pofiles
        return self._pofiles[path]

    def _get_relpath(self, path):
        return os.path.relpath(path, self.templatedir)

    def get_outpath(self, path):
        return os.path.join(self.outdir, self._get_relpath(path))

    def reload_translations(self, path):
        translations = gettext.NullTranslations()
        for pofile in self.get_pofiles(path):
            # Mo file is in memory.
            with BytesIO() as mofile:
                # Generate mofile.
                write_mo(mofile, read_po(pofile), use_fuzzy=self.use_fuzzy)
                # Return to beginning of mofile.
                mofile.seek(0)
                tl = gettext.GNUTranslations(mofile)
            tl.add_falback(translations)
            translations = tl

        def translate(msgid, mapping=None, default=None, **kw):
            translation = translations.gettext(msgid)
            if translation == msgid:
                translation = default
            if '$' in translation and mapping:

                def replace(match):
                    whole, param1, param2 = match.groups()
                    return mapping.get(param1 or param2, whole)
                translation = _interp_regex.sub(replace, translation)
            return translation

        with open(self.get_outpath(path), 'w') as outpath:
                template = chameleon.PageTemplateFile(path,
                                                      translate=translate)
                outpath.write(template.render(
                    locale=self.locale,
                    known_locales=self.known_locales
                ))

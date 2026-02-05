import gettext
import sys


def print_message(locale):
    # Set up message catalog access
    t = gettext.translation('%s' % locale, 'locale', fallback=True)
    _ = t.gettext

    s = _('Hello World!')
    print(s)


print_message(sys.argv[1])

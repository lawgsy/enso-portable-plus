"""Translate using Google's unofficial translation API."""

import urllib2
from urllib import urlencode
import re

re_language_detect = re.compile(r'.*"(.*)".*$')
re_translation = re.compile(r'"([^"]*)"')


hdr = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36')
}

supporte_languages = [
    "af", "ach", "ak", "am", "ar", "az", "be", "bem", "bg", "bh", "bn",
    "br", "bs", "ca", "chr", "ckb", "co", "crs", "cs", "cy", "da", "de", "ee",
    "el", "en", "eo", "es", "es-419", "et", "eu", "fa", "fi", "fo", "fr", "fy",
    "ga", "gaa", "gd", "gl", "gn", "gu", "ha", "haw", "hi", "hr", "ht", "hu",
    "hy", "ia", "id", "ig", "is", "it", "iw", "ja", "jw", "ka", "kg", "kk",
    "km", "kn", "ko", "kri", "ku", "ky", "la", "lg", "ln", "lo", "loz", "lt",
    "lua", "lv", "mfe", "mg", "mi", "mk", "ml", "mn", "mo", "mr", "ms", "mt",
    "ne", "nl", "nn", "no", "nso", "ny", "nyn", "oc", "om", "or", "pa", "pcm",
    "pl", "ps", "pt-BR", "pt-PT", "qu", "rm", "rn", "ro", "ru", "rw", "sd",
    "sh", "si", "sk", "sl", "sn", "so", "sq", "sr", "sr-ME", "st", "su", "sv",
    "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "tt",
    "tum", "tw", "ug", "uk", "ur", "uz", "vi", "wo", "xh", "yi", "yo", "zh-CN",
    "zh-TW", "zu"
]


def remove_prefix(text, prefix):
    """Remove prefix from start of text, if present and return result."""
    return text[text.startswith(prefix) and len(prefix):]


def detect_language(inputlist):
    """Detect the language given the input."""
    query = urlencode({'text': ' '.join(inputlist)})
    url = ('http://translate.googleapis.com/translate_a/single'
           '?client=gtx&sl=auto&dt=t&q=%s' % query)

    request = urllib2.Request(url, headers=hdr)
    response = urllib2.urlopen(request).read()

    return re_language_detect.findall(response)[0]


def trans(sl, tl, inputlist):
    """Translate given source to target language."""
    query = urlencode({'text': ' '.join(inputlist)})
    url = ('http://translate.googleapis.com/translate_a/single'
           '?client=gtx&sl=%s&tl=%s&dt=t&q=%s' % (sl, tl, query))

    request = urllib2.Request(url, headers=hdr)
    response = urllib2.urlopen(request).read()

    translation = re_translation.findall(response)[0]
    return translation


def cmd_translate(ensoapi, source_target_text=None):
    """
    Translate 'text' from 'source' to 'target' using Google (eg. en nl hello).

    <b>Supported languages:</b><br />
    See https://sites.google.com/site/tomihasa/google-language-codes<br />
    NOTE: Unicode not currently supported (i.e. Chinese characters, etc.)
    """
    if not source_target_text:
        source_target_text = ensoapi.get_selection().get("text", "")
    source_target_text.strip().strip("\0")

    if not source_target_text:
        ensoapi.display_message("No text to translate.")
        return

    source_target_text = source_target_text.encode("utf-8")

    inputlist = source_target_text.split(' ')
    sl = inputlist.pop(0)
    if sl not in supporte_languages:
        inputlist = [sl]+inputlist

        sl = detect_language(inputlist)
        tl = 'en' if sl != 'en' else 'nl'

        translation = trans(sl, tl, inputlist)
        translation = unicode(translation, "utf-8")
        translation = translation.replace("\\n", "")
        translation = translation.replace("\\r", "")
        translation = remove_prefix(translation, "Text = ")
        translation = remove_prefix(translation, "text =")

        ensoapi.display_message(translation, "Translation (%s->%s)" % (sl, tl))
    else:
        tl = inputlist.pop(0)

        if sl == tl:
            ensoapi.display_message("No translation",
                                    "The languages are the same")
            return

        translation = trans(sl, tl, inputlist)
        translation = unicode(translation, "utf-8")
        translation = translation.replace("\\n", "")
        translation = translation.replace("\\r", "")
        translation = remove_prefix(translation, "Text = ")
        translation = remove_prefix(translation, "text =")
        ensoapi.display_message(translation, "Translation (%s->%s)" % (sl, tl))

"use strict";

function loadIndex() {
    window.onunload = function() {};
    var locale = get_locale();
    let url = window.location;
    url = url.origin + "/" + locale + url.pathname + url.search + url.hash;
    console.log("assigning new url");
    window.location.assign(url);
};

function get_locale() {
    // List of locales of the browser in prefered order.
    var locales = window.navigator.languages;
    if (storageAvailable(localStorage)) {
        // If localStorage exists try and get locale from there and
        // add it as most prefered locale.
        var storage = localStorage;
        if (storage.getItem("locale")) {
            locales.unshift(storage.getItem("locale"));
        };
    };
    // Loop throug all locales.
    locale_loop:
    for (var locale of locales) {
        locale = locale.replace('-', '_')
        // If locale is in any of the languages supported return locale.
        for (let known_locale of Object.keys(known_locales)) {
            if (known_locales[known_locale].indexOf(locale) > -1) {
                break locale_loop;
            }
        }
        locale = null;
    }
    // A not supported locale, set default.
    if (locale == null) {
        locale = "en"
    }
    return locale;
}

var known_locales;

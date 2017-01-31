"use strict";

function loadIndex() {
    window.onunload = function() {};
    var locale = get_locale();
    let url = window.location;
    url = url.origin + "/" + locale + url.pathname + url.search + url.hash;
    console.log("Assigning new url", url);
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
            console.log("Found locale in localstorage, prepending it to array of locales.")
            locales.unshift(storage.getItem("locale"));
        };
    };
    console.log("Locales in preferred order", locales)
    // Loop throug all locales.
    for (var locale of locales) {
        let language = locale.split(/[-_]/)
        if (language.length > 1) {
            language = language[0].toLowerCase() + '-' + language[1].toUpperCase();
        } else {
            language = language[0]
        }
        // If locale is in any of the languages supported return locale.
        for (let known_locale of Object.keys(known_locales)) {
            if (known_locales[known_locale].indexOf(language) > -1) {
                console.log('Will use locale', locale);
                return locale;
            }
        }
    }
    // A not supported locale, return default.
    console.log("Locale unknown defaulting to en");
    return "en"
}

var known_locales;

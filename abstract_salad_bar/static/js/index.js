function loadIndex() {
    var known_locales = ["en-US", "nl"]
    var locale = window.navigator.language;
    if (storageAvailable(localStorage)) {
        var storage = localStorage;
        if (storage.getItem("locale")) {
            locale = storage.getItem("locale");
        };
        storage.setItem("locale", locale);
    };
    if (known_locales.indexOf(locale) == -1) {
        locale = known_locales[0];
    };
    let url = window.location
    url = url.origin + "/" + locale + url.pathname + url.search + url.hash;
    window.location.replace(url);
};

window.onload = loadIndex;

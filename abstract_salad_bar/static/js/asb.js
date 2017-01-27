"use strict";

function postSalad(event) {
    // Create a salad and post it to the server.
    var data = $(this).serializeObject();
    event.preventDefault();
    console.log(data);
    $.ajax({
        url: $(this).attr("action"),
        method: "POST",
        data: JSON.stringify(data),
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        success: loadSalad,
        error: showSaladLoadFail(null)
    });
};

function getId(ApiUrl) {
    // Get the id from an Document in the api url.
    let parser = document.createElement("a");
    parser.href = ApiUrl;
    var pathname = parser.pathname;
    if (pathname.lastIndexOf("/") == (pathname.length - 1)) {
        pathname.pop();
    };
    return pathname.substr(pathname.lastIndexOf("/") + 1);
};

function showSalad(data) {
    // Load a salad from the data.
    var startDate = moment.tz(data["startDate"], timezone);
    resetSalad();
    $("#main").hide();
    let salad = $("#salad");
    salad.data(data);
    salad.find("#saladLocation").append(data["location"]);
    salad.find("#saladStartDate").
        append(startDate.calendar());
    salad.find("#saladStartTime").
        append(startDate.format("LT"));
    salad.find("#createIngredient").submit(postIngredient(data["ingredients"]["@id"]));
    getIngredients(data);
    salad.show();
};

function postIngredient(url) {
    return function(event) {
        event.preventDefault();
        var data = $(this).serializeObject();
        // We should only call the ajax if both values are filled.
        // Empty the form.
        this.reset();
        $.ajax({
            url: url,
            method: "POST",
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success: showIngredient,
        });
    };
};

function getIngredients(salad) {
    var url = salad["ingredients"]["@id"];
    $.ajax({
        url: url,
        dataType: "json",
        success: showIngredients,
        data: {full: true},
    });
};

function showIngredients(data) {
    for (let ingredient of data["itemListElement"]) {
        showIngredient(ingredient);
    };
};

function showIngredient(data) {
    var row = $("<tr>");
    row.append($("<td>").text(data["itemOffered"]["name"]));
    row.append($("<td>").text(data["seller"]["name"]));
    $("#ingredients tbody").append(row);
};

function loadApp() {
    // Actions to run on page load.
    var currentState = history.state;
    window.onpopstate = showPage;
    timezone = moment.tz.guess();
    // timezone = "Europe/Amsterdam";
    moment.tz.setDefault(timezone);
    setMomentLocaleCalendars();
    locale = document.documentElement.lang;
    saveEmptySalad();
    if (currentState) {
        showSalad(currentState)
    } else {
        loadHash();
    };
}

function showPage(event) {
    if (event.state) {
        showSalad(event.state)
    } else {
        showMain();
    };
};

function saveEmptySalad() {
    $(document).data("emptySalad", $("#salad").clone(true));
};

function resetSalad() {
    $(document).data("emptySalad").clone(true).replaceAll("#salad");
};

function loadHash() {
    // Load a salad from the url hash.
    var hash = window.location.hash;
    if (hash) {
        hash = hash.slice(1);
        url = $("#createSalad").attr("action") + "/" + hash
        getSalad(url);
    } else {
        showMain();
    };
}

function getSalad(data) {
    var url;
    if (data.hasOwnProperty("@id")) {
        url = data["@id"]
    } else {
        url = data
    };
    var id = getId(url);
    $.ajax({
        url: url,
        dataType: "json",
        success: loadSalad,
        error: showSaladLoadFail(id),
    });
};

function loadSalad(data) {
    var id = getId(data["@id"]);
    history.pushState(data, data["location"], "#" + id);
    showSalad(data);
};

function showSaladLoadFail(id) {
    var message;
    if (id) {
        message = "Failed to load salad with id: [ " + id + " ].";
    } else {
        message = "Could not create salad.";
    }
    return function(jqXHR, textStatus, errorThrown) {
        alert(message);
        showMain();
    };
}

function showMain() {
    var main = $("#main");
    $("#salad").hide();
    resetSalad();
    resetCreateSaladForm();
    main.show();
}

function setStartDate(date) {
    $("input[name=when]").attr("value", date.calendar());
    $("input[name=time]").attr("value", date.format("LT"));
    $("input[name=startDate]").attr("value", date.format());
}

function resetCreateSaladForm() {
    $("#createSalad").submit(postSalad);
    $("#createSalad").trigger("reset");
    var date = moment().tz(timezone).
        day(7 + 4).
        hours(12).minutes(30).
        startOf('minute'); // Next thursday at 12.30 locale time.
    setStartDate(date);
};

function getStartDate() {
    // Get the start date from the when and time input.
    var date;
    var whenInput = $("input[name=when]").attr("value");
    var timeInput = $("input[name=time]").attr("value");
    if (whenInput) {
        date = moment(whenInput, "dddd");
        if (date.isValid()) {
            date.add(7, "days")
        } else {
            date = moment(whenInput, ["YYYY-M-D", "L", "LL"])
        }
        date.hour(12).minute(30); // Set default time to 12.30.
    };
    if (timeInput) {
        let time = moment(timeInput, ["HH:mm", "h:mm a"])
        if (date) {
            date.hour(time.hour()).minute(time.minute());
        } else {
            date = time;
        }
    };
    if (date != null & date.isValid()) {
        // Set timezone.
        $("input[name=startDate]").attr("value", date.format());
    };
};

function loadMain() {
    history.pushState(null, document.title, window.location.pathname);
    showMain();
};

// Global variables, values are filled in the loadApp function.
var locale;
var timezone;
window.onload = loadApp;

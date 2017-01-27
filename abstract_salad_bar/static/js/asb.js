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
    salad.find(".saladStartDate").
        text(startDate.calendar());
    salad.find(".saladStartTime").
        text(startDate.format("LT"));
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

function resetCreateSaladForm() {
    $("#createSalad .help-block").hide();
    $("#createSalad").trigger("reset");
    $("#createSalad").submit(postSalad);
    $("input[name=when]").change(setStartDate)
    $("input[name=time]").change(setStartDate)
    var date = moment().tz(timezone).
        day(4).
        hours(12).minutes(30).
        startOf('minute'); // Thursday at 12.30 locale time.
    if (date < moment()) {
        date.add(7, "day"); // Make sure it is the next Thursday and not the last.
    }
    $("input[name=when]").attr("placeholder", date.calendar());
    $("input[name=time]").attr("placeholder", date.format("LT"));
    $("input[name=startDate]").attr("value", date.format());
};

function getStartDate() {
    // Get the start date from the when and time input.
    var date;
    var fromDay = false;
    var whenInput = $("input[name=when]").val();
    var timeInput = $("input[name=time]").val();
    if (whenInput) {
        // Check for weekday. Does not work if text is put infront of weekday.
        // works: "Thursday", "thurs"
        // does not work: "next Thursday"
        date = moment(whenInput, "dddd");
        if (date.isValid()) {
            fromDay = true;
        } else {
            date = moment(whenInput, ["YYYY-M-D", "L", "LL"])
        }
        if (!date.isValid()) {
            // Try localized strings for "today" or "tomorrow", "next week".
            whenInput = whenInput.trim().toLowerCase();
            // TODO localize this part.
            if (whenInput == "today") {
                date = moment();
            } else if (whenInput == "tomorrow") {
                date = moment();
                date.add(1, "day");
            } else if (whenInput == "next week") {
                date = moment();
                date.add(7, "day");
            }
        }
        date.hour(12).minute(30); // Set default time to 12.30.
    };
    if (timeInput) {
        let time = moment(timeInput, ["HH:mm", "h:mm a"])
        if (date) {
            date.hour(time.hour()).minute(time.minute());
        } else {
            fromDay = true;
            date = time;
        }
    };
    if (fromDay) {
        // If the date was not set, or the weekday string format was used
        // make sure that this date is in the future.
        moment.min(date, moment()).add(7, "days");
    };
    if (date == null) {
        date = moment($("input[name=startDate]").attr("value"));
    }
    if (date.isValid()) {
        return date
    };
};

function setStartDate(event) {
    var date = getStartDate();
    var input = $(event.target);
    let input.sibings(".help-block").hide()
    console.log(input);
    if (!date) {
        let errorBlock = input.siblings(".help-block .error");
        let dateSpan = helpBlock.find("#inputStartDateError");
        let timeSpan = helpBlock.find("#inputStartTimeError");
        let andSpan = helpBlock.find("#andError");
        if (input.attr("name") == "when") {
            dateSpan.show();
        } else {
            timeSpan.show();
        }
        if (dateSpan.is(":visible") & timeSpan.is(":visible")) {
            andSpan.show();
        } else {
            andSpan.hide();
        };
    } else if (date < moment()) {
        // Set class to onError, show warning message
    } else {
        // Set class to onSuccess Show success message update startDate input.
        input.siblings(".help-block .error").children("span").hide();
        $("input[name=startDate]").val(date);
    }
};

function loadMain() {
    history.pushState(null, document.title, window.location.pathname);
    showMain();
};

// Global variables, values are filled in the loadApp function.
var locale;
var timezone;
window.onload = loadApp;

"use strict";

function postSalad(event) {
    // Create a salad and post it to the server.
    event.preventDefault();
    var data = $(this).serializeObject();
    if (!moment(data['startDate'], moment.ISO_8601, true).isValid()) {
        return;
    }
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
    printStartDate(startDate, salad);
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
    locale = document.documentElement.lang;
    moment.locale(locale);
    timezone = moment.tz.guess();
    // timezone = "Europe/Amsterdam";
    moment.tz.setDefault(timezone);
    setMomentLocaleCalendars();
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
    $("input[name=at]").change(setStartDate)
    var date = moment().tz(timezone).
        day(4).
        hours(12).minutes(30).
        startOf('minute'); // Thursday at 12.30 locale time.
    if (date < moment()) {
        date.add(7, "day"); // Make sure it is the next Thursday and not the last.
    }
    $("input[name=when]").attr("placeholder", date.calendar());
    $("input[name=at]").attr("placeholder", date.format("LT"));
    $("input[name=startDate]").data("date", date);
    setStartDate();
};

function getStartDate() {
    // Get the start date from the when and time input.
    var date;
    var invalid = [];
    var now = false;
    var fromDay = false;
    var whenInput = $("input[name=when]").val().trim().toLowerCase();
    var timeInput = $("input[name=at]").val().trim().toLowerCase();
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
            let options = $("input[name=when]").data();
            if (whenInput == options["today"]) {
                date = moment();
            } else if (whenInput == options["tomorrow"]) {
                date = moment();
                date.add(1, "day");
            } else if (whenInput == options["nextWeek"]) {
                date = moment();
                date.add(7, "day");
            } else if (whenInput == options["now"]) {
                date = moment();
                now = true;
            } else {
                invalid.push("date");
            }
        }
        if (!now) {
            date.hour(12).minute(30); // Set default time to 12.30.
        };
    };
    if (timeInput) {
        let time = moment(timeInput, ["HH:mm", "h:mm a"])
        if (!time.isValid()) {
            let options = $("input[name=at]").data();
            if (timeInput == options["same"]) {
                time = moment();
            } else {
                invalid.push("time");
            }
        }
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
        date = $("input[name=startDate]").data("date");
    }
    return [date, invalid];
};

function setStartDate(event) {
    var [date, invalid] = getStartDate();
    if (event == null) {
        var parentDiv = $("#createSalad input[name=when]").parent();
    } else {
        var parentDiv = $(event.target).parent();
    }
    parentDiv.find(".help-block").hide()
    if (invalid.length) {
        var helpBlock = parentDiv.find(".help-block.error");
        let timeError = invalid.indexOf("time") > -1;
        let dateError = invalid.indexOf("date") > -1;
        parentDiv.find("input[name=when]").toggleClass("error", dateError)
        parentDiv.find("input[name=at]").toggleClass("error", timeError)
        helpBlock.find("#inputStartDateError").toggle(dateError);
        helpBlock.find("#inputStartTimeError").toggle(timeError);
        helpBlock.find("#andError").toggle(invalid.length > 1);
        helpBlock.show();
    } else {
        if (date < moment()) {
            var helpBlock = parentDiv.find(".help-block.warning");
        } else {
            var helpBlock = parentDiv.find(".help-block.success");
        }
        parentDiv.find("input").removeClass("error");
        printStartDate(date, helpBlock);
        helpBlock.show();
    }
    $("input[name=startDate]").val(date.format());
};

function printStartDate(date, block) {
    if (block == null) {
        block = $(window);
    }
    block.find(".saladStartDate").text(date.calendar());
    block.find(".saladStartTime").text(date.format("LT"));
}

function loadMain() {
    history.pushState(null, document.title, window.location.pathname);
    showMain();
};

// Global variables, values are filled in the loadApp function.
var locale;
var timezone;
window.onload = loadApp;

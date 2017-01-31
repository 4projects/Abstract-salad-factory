"use strict";

function postSalad(event) {
    // Create a salad and post it to the server.
    event.preventDefault();
    var data = $(this).serializeObject();
    $.ajax({
        url: $(this).attr("action"),
        method: "POST",
        data: JSON.stringify(data),
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        success: loadSalad,
        error: SaladLoadFail(null)
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
    var id = getId(data["@id"]);
    history.replaceState(data, data["location"], "#" + id);
    resetSalad();
    hideElement($("#create"));
    let salad = $("#salad");
    salad.data(data);
    salad.find("#saladLocation").append(data["location"]);
    let url = "/#" + id;
    salad.find("#saladUrl a").text(window.location.origin + url).attr("href", url);
    printStartDate(startDate, salad);
    salad.find("#createIngredient").submit(postIngredient(data["ingredients"]["@id"]));
    getIngredients(data);
    showElement(salad);
    salad.find("input[name=name]")[0].focus();
};

function postIngredient(url) {
    return function(event) {
        event.preventDefault();
        var data = $(this).serializeObject();
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
    row.append($("<td>"));
    $("#ingredients tbody").append(row);
    // Focus on input.
    $("#salad input[name=name]")[0].focus();
};

function loadApp() {
    // Actions to run on page load.
    var currentState = history.state;
    window.onpopstate = showPage;
    locale = document.documentElement.lang;
    // TODO set the current locale in the local storage.
    moment.locale(locale);
    timezone = moment.tz.guess();
    // timezone = "Europe/Amsterdam";
    moment.tz.setDefault(timezone);
    setMomentLocaleCalendars();
    extendDatalists();
    saveEmptySalad();
    setNav();
    if (currentState) {
        getSalad(currentState)
    } else {
        loadHash();
    };
}

function setNav() {
    $("#toCreate").click(loadCreate);
}

function extendDatalists() {
    var datesList = $("#datesList");
    for (let weekday of moment.weekdays()) {
        datesList.append("<option>" + weekday + "</option>");
    }
}

function showPage(event) {
    if (event.state) {
        getSalad(event.state)
    } else {
        showCreate();
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
    var url;
    if (hash) {
        hash = hash.slice(1);
        url = $("#createSalad").attr("action") + "/" + hash
        getSalad(url);
    } else {
        showCreate();
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
        success: showSalad,
        error: SaladLoadFail(id),
    });
};

function loadSalad(data) {
    var url = data["@id"]
    var id = getId(url);
    history.pushState(data, null, "#" + id);
    showSalad(data);
};

function SaladLoadFail(id) {
    var message;
    if (id) {
        message = "Failed to load salad with id: [ " + id + " ].";
    } else {
        message = "Could not create salad.";
    }
    return function(jqXHR, textStatus, errorThrown) {
        alert(message);
        loadCreate();
    };
}

function showCreate() {
    var createDiv = $("#create");
    history.replaceState(null, document.title, window.location.pathname);
    hideElement($("#salad"));
    resetSalad();
    resetCreateSaladForm();
    showElement(createDiv);;
    // Focus on input field after createDiv is shown.
    createDiv.find("input[name=when]")[0].focus();
}

function resetCreateSaladForm() {
    var form = $("#createSalad");
    hideElement(form.find(".help-block"));
    form[0].reset();
    form.submit(postSalad);
    var whenInput = form.find("input[name=when]");
    var atInput = form.find("input[name=at]");
    whenInput.on("input", setStartDate)
    atInput.on("input", setStartDate)
    var date = moment().tz(timezone).
        day(4).
        hours(12).minutes(30).
        startOf("minute"); // Thursday at 12.30 locale time.
    if (date < moment()) {
        date.add(7, "day"); // Make sure it is the next Thursday and not the last.
    }
    whenInput.attr("placeholder", date.calendar());
    atInput.attr("placeholder", date.format("LT"));
    form.find("input[name=startDate]").data("date", date);
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
            let options = $("input[name=when]").siblings("datalist");
            if (whenInput == options.children("#today").text().trim().toLowerCase()) {
                date = moment();
            } else if (whenInput == options.children("#tomorrow").text().trim().toLowerCase()) {
                date = moment();
                date.add(1, "day");
            } else if (whenInput == options.children("#nextWeek").text().trim().toLowerCase()) {
                date = moment();
                date.add(7, "day");
            } else if (whenInput == options.children("#now").text().trim().toLowerCase()) {
                date = moment();
                now = true;
            } else {
                invalid.push("when");
            }
        }
        if (!now) {
            date.hour(12).minute(30); // Set default time to 12.30.
        };
    };
    if (timeInput) {
        let time = moment(timeInput, ["HH:mm", "h:mm a"])
        if (!time.isValid()) {
            let options = $("input[name=at]").siblings("datalist");
            if (timeInput ==  options.children("#same").text().trim().toLowerCase()) {
                time = moment();
            } else {
                invalid.push("at");
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
        var parentDiv = $("#createSalad input[name=when]").parents("#startDateInput").first();
    } else {
        var parentDiv = $(event.target).parents("#startDateInput").first();
    }
    // Hide all help blocks.
    console.log(parentDiv);
    hideElement(parentDiv.find(".help-block"));
    for (let error of ["at", "when"]) {
        let input = parentDiv.find("input[name=" + error + "]");
        if (invalid.indexOf(error) > -1) {
            input[0].setCustomValidity(input.attr("errormessage"));
        } else {
            input[0].setCustomValidity("");
        }
    }
    if (!invalid.length) {
        if (date < moment()) {
            var helpBlock = parentDiv.find("#startDatePast");
        } else {
            var helpBlock = parentDiv.find("#startDateCorrect");
        }
    } else {
        var helpBlock = parentDiv.find("#startDateInvalid");
    }
    printStartDate(date, helpBlock);
    showElement(helpBlock);
    $("input[name=startDate]").val(date.format());
};

function printStartDate(date, block) {
    if (block == null) {
        block = $(window);
    }
    block.find(".saladStartDate").text(date.calendar());
    block.find(".saladStartTime").text(date.format("LT"));
}

function loadCreate() {
    history.pushState(null, document.title, window.location.pathname);
    showCreate();
};

// Global variables, values are filled in the loadApp function.
var locale;
var timezone;

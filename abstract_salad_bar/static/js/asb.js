function postSalad(event) {
    // Create a salad and post it to the server.
    event.preventDefault();
    var data = $(this).serializeObject();
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
    var parser = document.createElement("a");
    parser.href = ApiUrl;
    var pathname = parser.pathname;
    if (pathname.lastIndexOf("/") == (pathname.length - 1)) {
        pathname.pop();
    };
    return pathname.substr(pathname.lastIndexOf("/") + 1);
};

function showSalad(data) {
    // Load a salad from the data.
    resetSalad();
    $("#main").hide();
    var salad = $("#salad");
    salad.data(data);
    salad.find("#saladLocation").append(data["location"]);
    var startDate = moment.tz(data["startDate"], timezone);
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

function loadPage() {
    // Actions to run on page load.
    saveEmptySalad();
    var currentState = history.state;
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
    id = getId(url);
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
    $("#salad").hide();
    resetSalad();
    $("#createSalad").submit(postSalad);
    var main = $("#main");
    main.trigger("reset");
    main.show();
}

function setStartDate() {
    startDateInput = $("input[name=startDate]");
    var date = startDateInput.data("date");
    if (date == null) {
        var date = moment().tz(timezone).
            day(7 + 4).
            hours(12).minutes(30).
            startOf('minute'); // Next thursday at 12.30 locale time.
        startDateInput.data("date", date);
    };
    $("input[name=when]").attr("value", date.calendar());
    $("input[name=time]").attr("value", date.format("LT"));
    $("input[name=startDate]").attr("value", date.format());
}

funcion getstartDate() {
}

function loadMain() {
    history.pushState(null, document.title, window.location.pathname);
    showMain();
};

window.onload = loadPage;
window.onpopstate = showPage;
const timezone = moment.tz.guess();
// const timezone = "Europe/Amsterdam";
moment.tz.setDefault(timezone);
const locale = document.documentElement.lang;
setMomentLocaleCalendars();

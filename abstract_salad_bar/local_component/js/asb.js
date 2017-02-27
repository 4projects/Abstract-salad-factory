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
    $("#toCreate").closest("li").removeClass("uk-active");
    history.replaceState(data, data["location"], "#" + id);
    resetSalad();
    hideElement($("#create"));
    hideElement($("#createHelp"));
    showElement($("#saladHelp"));
    let salad = $("#salad");
    salad.data(data);
    salad.find("#saladLocation").append(data["location"]);
    let url = "/#" + id;
    let saladUrl = salad.find("#saladUrl");
    saladUrl.find("a").text(window.location.origin + url).attr("href", url);
    printStartDate(startDate, salad);
    salad.find("#createIngredient").submit(postIngredient(data["ingredients"]["@id"]));
    getIngredients(data);
    showElement(salad);
    salad.find("input[name=name]")[0].focus();
    showFirstTimeHelp();
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
            success: addIngredient,
        });
    };
};

function addIngredient(data) {
    // TODO Save ingredient to local storage, so we know it is ours.
    showIngredient(data)
}

function getIngredients(salad) {
    var url = salad["ingredients"]["@id"];
    $.ajax({
        url: url,
        dataType: "json",
        success: showIngredients,
        data: {full: true},
    });
};

function websocketIngredients(data) {
    // 1 connect to websocket
    var url = data["websocket"]["@value"]
    // 2 Already subscribed to path.
    var ws = new WebSocket(url);
    // add ingredient on message
    ws.addEventListener("message",
        function (event) {
            parseWebsocketIngredientMessage(event.data)
        });
}

function parseWebsocketIngredientMessage(data) {
    data = JSON.parse(data)
    console.log("Message from server", data);
    console.log(data["function"])
    if (data["function"] == "message" && data["type"] == "CREATE") {
        showIngredient(data["data"])
    }
}

function showIngredients(data) {
    websocketIngredients(data);
    for (let ingredient of data["itemListElement"]) {
        showIngredient(ingredient);
    };
};

function showIngredient(data) {
    // Add ingredient to list of ingredients.
    var table = $("#ingredients tbody")
    var id = getId(data["@id"])
    // Only add ingredienten if it is not in the list yet.
    if (table.children("#" + id).length == 0) {
        var row = $("<tr>").attr("id", id);
        row.append($("<td>").addClass("uk-text-truncate").text(data["itemOffered"]["name"]));
        row.append($("<td>").addClass("uk-text-truncate").text(data["seller"]["name"]));
        row.append($("<td>"));
        table.append(row);
    }
    // Focus on input.
    $("#salad input[name=name]")[0].focus();
};

function loadApp() {
    // Actions to run on page load.
    var currentState = history.state;
    window.onpopstate = showPage;
    locale = document.documentElement.lang;
    // Save the locale for next reload.
    if (storageAvailable("localStorage")) {
        window.localStorage.setItem("locale", locale);
    }
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
    loadVegetables();
}

function setNav() {
    $("#toCreate").click(navAttachClick(loadCreate, resetCreateSaladForm));
    $("#changeLanguage ul a").click(navAttachClick(loadLanguage));
    $("#toggleBackground").click(toggleBackground);
}

function toggleBackground() {
    $("#toggleBackground #backgroundOff").toggle();
    console.log("Toggling background");
    $("#fallingVegetables").toggle();
}

function loadLanguage(event) {
    var url = event.target.href
    window.location.assign(url + window.location.hash);
}

function navAttachClick(inactiveFunc, activeFunc) {
    // Don't execute the click function if navigation is active.
    return function(event) {
        event.preventDefault();
        if (!$(event.target).closest(".uk-active").length) {
            console.log("Inactive function will be called for event", inactiveFunc, event);
            return inactiveFunc(event);
        } else if (activeFunc != null) {
            console.log("Active function will be called for event", activeFunc, event);
            return activeFunc(event);
        }
        console.log("No function will be called for event", event)
    }
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
    $("#toCreate").closest("li").addClass("uk-active");
    hideElement($("#saladHelp"));
    showElement($("#createHelp"));
    hideElement($("#salad"));
    resetSalad();
    resetCreateSaladForm();
    showElement(createDiv);;
    // Focus on input field after createDiv is shown.
    createDiv.find("input[name=when]")[0].focus();
    showFirstTimeHelp();
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

function showFirstTimeHelp() {
    if (storageAvailable("localStorage")) {
        var storage = window.localStorage;
        if (!storage.getItem("notFirstTime")) {
            storage.setItem("notFirstTime", true);
            $("#toHelp").click();
        }
    }
}

var vegetables = ["lettuce", "olive", "walnut", "tomato", "cucumber", "carrote", "radish"]

function loadVegetables() {
    // var vegetablesDiv = $("#vegetables");
    var deferreds = [];
    for (let vegetable of vegetables) {
        // Create a new deferred which will be resolved when the ajax call is complete (success or fail).
        let deferred = $.Deferred();
        deferreds.push(deferred);
        // 
        $.ajax({
            url: "/images/vegetables/" + vegetable + ".svg",
            complete: function(jqXHR, textStatus) {
                // Add the jqXHR and text status tot the deferred object.
                deferred.resolve(jqXHR, textStatus, vegetable)
            },
        })
    }
    $.when.apply(null, deferreds).done(function() {
        var vegetablesDiv = $("#vegetables");
        var serializer = new XMLSerializer();
        var defs = $("#globalDefs");
        // var diameter = 0;
        // let draw = SVG("vegetables").attr("id", "logoNew");;
        for (let result of arguments) {
            // Skip result that did not load succesfully.
            if (result[1] != "success") {
                continue
            }
            let svgDoc = result[0].responseXML;
            let svgData = $(serializer.serializeToString(svgDoc.documentElement)).attr("id", result[2]).addClass("vegetable");
            // Move gradients out of svg into a seperate (none hidden) div.
            defs.append(svgData.find("defs").children());
            // Put svg data in hidden div
            vegetablesDiv.append(svgData);
        }
        animateVegetables(1);
        // Add vegetables every 10 seconds.
        // vegetableTimer = setInterval(animateVegetables, 10000);
    })
}


function animateVegetables(counter) {
    var fallingVegetablesDiv = $("#fallingVegetables");
    if (counter < 8) {
        setTimeout(animateVegetables, counter * 5000, counter + 1);
    };
    console.log("number of vegetable copies falling:", counter);
    $("#vegetables > svg").each(function() {
        // Clone vegetables
        let vegetable = $(this).clone().attr("id", null).removeClass("vegetable");
        vegetable.addClass("fallingVegetable");
        readyVegetable(vegetable);
        fallingVegetablesDiv.append(vegetable);
        // add animationend event listener
        // vegetable.on("animationend", function(event) {
        //     console.log(event);
        //     readyVegetable($(event.target));
        // });
    });
}

function readyVegetable(vegetable) {
    // vegetable.css("Animation-play-state", "paused");
    // vegetable.removeClass("fallingVegetable");
    // set random position
    vegetable.css("animation-name", "falling" + Math.floor(Math.random() * 6));
    vegetable.css("left", Math.floor(-10 + Math.random() * 110) + "%");
    // vegetable.css("transform", "rotate(" + Math.random() + "turn)")
    // set speed randomish
    vegetable.css("animation-duration", (5 + Math.random() * 10) + "s");
    // vegetable.css("Animation-play-state", "running");
    // void vegetable[0].offsetWidth;
}

function createLogo() {
    // let draw = SVG($(svgData).attr("id", result[2])[0]);
    // let svg = SVG.adopt(svgData.children("g")[0]);
    // console.log(svg.transform());
    // // svg.transform({x: 0, y: 0});
    // console.log(svg.transform());
    // // svg.rotate(45);
    // console.log(svg.transform());
    // console.log(svgData);
    // let maxSide = Math.max.apply(null, svgData.attr("viewBox").split(/\s+/).map(Number));
    // console.log(maxSide);
    // draw.add(svg);
    // if (maxSide > diameter) {
    //     diameter = maxSide;
    // }
    // // if (result[2] == "lettuce") {
    // //     draw.attr("viewBox", svgData.attr("viewBox"));
    // // }
    // // draw.use(svg);
    // console.log(diameter);
    // diameter = Math.sqrt(2 * diameter**2);
    // console.log(diameter);
    // draw.viewbox(0, 0, diameter, diameter);
    // // console.log(draw);
}

// Global variables, values are filled in the loadApp function.
var locale;
var timezone;

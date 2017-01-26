function submitSalad(event) {
    // Create a salad and post it to the server.
    event.preventDefault();
    var data = $(this).serializeObject();
    $.ajax({
        url: $(this).attr("action"),
        method: "POST",
        data: JSON.stringify(data),
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        success: showSalad,
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
    var id = getId(data["@id"]);
    window.location.hash = "#" + id;
    console.log(data);
    $("#main").hide();
    var salad = $("#salad");
    salad.data(data);
    salad.find("#saladLocation").append(data["location"]);
    salad.find("#saladDate").append(data["startDate"]);
    salad.find("#createIngredient").submit(submitIngredient(data["ingredients"]["@id"]));
    loadIngredients(data);
    salad.show();
};

function submitIngredient(url) {
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

function loadIngredients(salad) {
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
    console.log(data);
    var row = $("<tr>");
    row.append($("<td>").text(data["itemOffered"]["name"]));
    row.append($("<td>").text(data["seller"]["name"]));
    $("#ingredients tbody").append(row);
};

function loadPage() {
    // Actions to run on page load.
    saveEmptySalad();
    $("#createSalad").submit(submitSalad);
    loadHash();
}

function saveEmptySalad() {
    $(document).data("emptySalad", $("#salad").clone(true));
};

function resetSalad() {
    $(document).data("emptySalad").replaceAll("#salad");
};

function loadHash() {
    // Load a salad from the url hash.
    var hash = window.location.hash;
    if (hash) {
        hash = hash.slice(1);
        $.ajax({
            url: $("#createSalad").attr("action") + "/" + hash,
            dataType: "json",
            success: showSalad,
            error: showSaladLoadFail(hash),
        })
    }
}

function showSaladLoadFail(id) {
    var message;
    if (id) {
        message = "Failed to load salad with id: [ " + id + " ].";
    } else {
        message = "Could not create salad.";
    }
    return function(jqXHR, textStatus, errorThrown) {
        alert(message);
    };
}

window.onload = loadPage;

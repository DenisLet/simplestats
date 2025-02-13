
function setupAutocomplete(inputId, suggestionsId, searchUrl) {
    const input = document.getElementById(inputId);
    const suggestions = document.getElementById(suggestionsId);

    async function handleInput() {
        const query = input.value.trim();
        if (query.length < 3) {
            suggestions.innerHTML = "";
            return;
        }

        const response = await fetch(`${searchUrl}?q=${query}`);
        const data = await response.json();

        suggestions.innerHTML = "";
        if (data.teams.length) {
            data.teams.forEach(team => {
                const item = document.createElement("div");
                item.className = "suggestion-item";
                item.textContent = team;
                item.onclick = () => {
                    input.value = team;
                    suggestions.innerHTML = "";
                };
                suggestions.appendChild(item);
            });
        }
    }

    function handleClickOutside(e) {
        if (!suggestions.contains(e.target) && e.target !== input) {
            suggestions.innerHTML = "";
        }
    }

    input.addEventListener("input", handleInput);
    document.addEventListener("click", handleClickOutside);

    return () => {
        input.removeEventListener("input", handleInput);
        document.removeEventListener("click", handleClickOutside);
        suggestions.innerHTML = "";
    };
}


let disableAutocompleteTeam1;
let disableAutocompleteTeam2;

function initAutocomplete() {

    const currentPage = window.location.pathname;


    let searchUrl = "/search_teams";
    if (currentPage.includes("hockey")) {
        searchUrl = "/search_hockey_teams";
    }
    if (currentPage.includes("handball")) {
        searchUrl = "/search_handball_teams";
    }

    if (currentPage.includes("basketball")) {
        searchUrl = "/search_basketball_teams";
    }


    const autocompleteToggle = document.getElementById("autocomplete-toggle");
    if (autocompleteToggle.checked) {
        disableAutocompleteTeam1 = setupAutocomplete("team1", "team1-suggestions", searchUrl);
        disableAutocompleteTeam2 = setupAutocomplete("team2", "team2-suggestions", searchUrl);
    }
}


const autocompleteToggle = document.getElementById("autocomplete-toggle");

autocompleteToggle.addEventListener("change", (e) => {
    const currentPage = window.location.pathname;
    let searchUrl = "/search_teams";
    if (currentPage.includes("hockey")) {
        searchUrl = "/search_hockey_teams";
    }
    if (currentPage.includes("handball")) {
        searchUrl = "/search_handball_teams";
    }
    if (currentPage.includes("basketball")) {
        searchUrl = "/search_basketball_teams";
    }

    if (e.target.checked) {

        disableAutocompleteTeam1 = setupAutocomplete("team1", "team1-suggestions", searchUrl);
        disableAutocompleteTeam2 = setupAutocomplete("team2", "team2-suggestions", searchUrl);
    } else {

        if (disableAutocompleteTeam1) disableAutocompleteTeam1();
        if (disableAutocompleteTeam2) disableAutocompleteTeam2();
    }
});


document.addEventListener("DOMContentLoaded", initAutocomplete);

// Функция автозаполнения
function setupAutocomplete(inputId, suggestionsId, searchUrl) {
    const input = document.getElementById(inputId);
    const suggestions = document.getElementById(suggestionsId);

    async function handleInput() {
        const query = input.value.trim();
        if (query.length < 3) {
            suggestions.innerHTML = ""; // Очистка списка предложений
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
                    suggestions.innerHTML = ""; // Очистка списка после выбора
                };
                suggestions.appendChild(item);
            });
        }
    }

    function handleClickOutside(e) {
        if (!suggestions.contains(e.target) && e.target !== input) {
            suggestions.innerHTML = ""; // Очистка при клике вне списка
        }
    }

    input.addEventListener("input", handleInput);
    document.addEventListener("click", handleClickOutside);

    return () => {
        input.removeEventListener("input", handleInput);
        document.removeEventListener("click", handleClickOutside);
        suggestions.innerHTML = ""; // Очистка предложений при отключении
    };
}

// Инициализация автозаполнения
let disableAutocompleteTeam1;
let disableAutocompleteTeam2;

function initAutocomplete() {
    // Инициализация автозаполнения только если чекбокс выбран
    const autocompleteToggle = document.getElementById("autocomplete-toggle");
    if (autocompleteToggle.checked) {
        disableAutocompleteTeam1 = setupAutocomplete("team1", "team1-suggestions", "/search_teams");
        disableAutocompleteTeam2 = setupAutocomplete("team2", "team2-suggestions", "/search_teams");
    }
}

// Управление автозаполнением через чекбокс
const autocompleteToggle = document.getElementById("autocomplete-toggle");

autocompleteToggle.addEventListener("change", (e) => {
    if (e.target.checked) {
        // Включаем автозаполнение
        disableAutocompleteTeam1 = setupAutocomplete("team1", "team1-suggestions", "/search_teams");
        disableAutocompleteTeam2 = setupAutocomplete("team2", "team2-suggestions", "/search_teams");
    } else {
        // Отключаем автозаполнение
        if (disableAutocompleteTeam1) disableAutocompleteTeam1();
        if (disableAutocompleteTeam2) disableAutocompleteTeam2();
    }
});

// Инициализация автозаполнения при загрузке страницы в зависимости от состояния чекбокса
document.addEventListener("DOMContentLoaded", initAutocomplete);

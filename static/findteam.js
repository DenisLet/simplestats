function setupAutocomplete(inputId, suggestionsId, searchUrl) {
    const input = document.getElementById(inputId);
    const suggestions = document.getElementById(suggestionsId);

    input.addEventListener("input", async () => {
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
    });

    document.addEventListener("click", (e) => {
        if (!suggestions.contains(e.target) && e.target !== input) {
            suggestions.innerHTML = ""; // Очистка при клике вне списка
        }
    });
}

// Настройка автодополнения
setupAutocomplete("team1", "team1-suggestions", "/search_teams");
setupAutocomplete("team2", "team2-suggestions", "/search_teams");
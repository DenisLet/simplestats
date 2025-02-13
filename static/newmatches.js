let currentSport = 'football';
let previousFirstMatches = {
    football: null,
    basketball: null
};

function checkForNewMatch(newMatches) {
    if (newMatches.length === 0) return;

    const firstMatch = newMatches[0];


    if (!previousFirstMatches[currentSport]) {
        previousFirstMatches[currentSport] = firstMatch;
        return;
    }


    if (
        previousFirstMatches[currentSport][0] !== firstMatch[0] ||
        previousFirstMatches[currentSport][1] !== firstMatch[1] ||
        previousFirstMatches[currentSport][2] !== firstMatch[2] ||
        previousFirstMatches[currentSport][3] !== firstMatch[3] ||
        previousFirstMatches[currentSport][4] !== firstMatch[4]
    ) {
        playSound();
    }


    previousFirstMatches[currentSport] = firstMatch;
}


function playSound() {
    const audio = new Audio('/static/zvon.ogg');
    audio.play().catch(error => console.error('Ошибка при воспроизведении звука:', error));
}

function fetchMatches() {
    fetch('/api/new_matches')
        .then(response => response.json())
        .then(data => {
            const matches = data[currentSport + '_matches'];

            console.log('Полученные матчи:', matches);

            checkForNewMatch(matches);
            updateTable(matches);
        })
        .catch(error => console.error('Ошибка загрузки данных:', error));
}

function switchSport(sport) {
    currentSport = sport;
    fetchMatches();
}

function updateTable(matches) {
    const tableBody = document.getElementById('matches-table-body');
    tableBody.innerHTML = '';

    const currentTime = new Date().getTime();

    matches.forEach((match) => {
        const matchFoundTime = new Date(match[4] + ' UTC').getTime();
        const timeDifference = (currentTime - matchFoundTime) / 1000 / 60;

        let rowClass = '';
        if (timeDifference < 20) {
            rowClass = 'recent-match';
        }

        const row = document.createElement('tr');
        if (rowClass) {
            row.classList.add(rowClass);
        }

        row.innerHTML = `
            <td>${match[0]}</td>
            <td>${match[1]}</td>
            <td>${match[2]}</td>
            <td>${match[3]}</td>
            <td>${match[4]}</td>
        `;
        tableBody.appendChild(row);
    });
}

window.onload = function () {
    fetchMatches();
    setInterval(fetchMatches, 15000);
};

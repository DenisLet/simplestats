function calculateMinMaxScoresWithTotal(tableId) {
    let rows = document.querySelectorAll(`#${tableId} tbody tr`);
    let homeScores = [];
    let awayScores = [];
    let totalScores = [];

    rows.forEach(row => {
        let halfTimeScores = row.querySelectorAll('td:nth-child(5)');
        if (halfTimeScores.length > 0) {
            let [home, away] = halfTimeScores[0].textContent.split(' - ').map(Number);
            homeScores.push(home);
            awayScores.push(away);
            totalScores.push(home + away);
        }
    });

    let minHome = Math.min(...homeScores);
    let maxHome = Math.max(...homeScores);
    let minAway = Math.min(...awayScores);
    let maxAway = Math.max(...awayScores);
    let minTotal = Math.min(...totalScores);
    let maxTotal = Math.max(...totalScores);

    return {
        home: { min: minHome, max: maxHome },
        away: { min: minAway, max: maxAway },
        total: { min: minTotal, max: maxTotal }
    };
}

function updateMinMaxDisplay(teamId, stats) {
    document.getElementById(`${teamId}-min`).textContent = `Min: ${stats.min}`;
    document.getElementById(`${teamId}-max`).textContent = `Max: ${stats.max}`;
}

function updateTotalMinMaxDisplayForTeam(teamId, totalStats) {
    document.getElementById(`total-min-${teamId}`).textContent = `Min: ${totalStats.min}`;
    document.getElementById(`total-max-${teamId}`).textContent = `Max: ${totalStats.max}`;
}

// Example usage for team1 and team2
let team1Stats = calculateMinMaxScoresWithTotal('matches-team1');
let team2Stats = calculateMinMaxScoresWithTotal('matches-team2');

updateMinMaxDisplay('team1', team1Stats.home);
updateMinMaxDisplay('team2', team2Stats.away);
updateTotalMinMaxDisplayForTeam('team1', team1Stats.total); // Update for team1
updateTotalMinMaxDisplayForTeam('team2', team2Stats.total); // Update for team2